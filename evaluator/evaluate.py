#!/usr/bin/env python3
"""
evaluate.py — 7-agent Person evaluator for the OOi Person 7×7 matrix.

Runs 7 specialized agents against a person, one per OOi layer:

  L1 Scout     — what do they GIVE to the network
  L2 Auditor   — do they deal FAIRLY
  L3 Verifier  — is what they say REAL (claims vs. evidence)
  L4 Watcher   — do they PREFER the network (loyalty over time)
  L5 Council   — is their respect EARNED (peer-measured)
  L6 Listener  — do they HEAR before they speak
  L7 Elder     — do they make others BETTER (teaching / legacy)

Each agent reads the 7 factors defined for its layer in
templates/person/00i-matrix.yaml, gathers evidence with tools/search.py and
tools/memory.py, calls an LLM through BitRouter, and scores each factor
0.0-1.0 with a one-sentence reasoning grounded in that evidence.

Execution order:
  Phase 1 — L1 (Scout) runs alone; establishes the baseline "what do they give".
  Phase 2 — L2-L6 run in parallel, at most 2 concurrent (semaphore-gated),
            each given a summary of L1's findings as context.
  Phase 3 — L7 (Elder) runs last; it needs the summarized output of all
            six other agents to judge teaching/legacy.

truth.rate = (factors scored > 0.0 across all 7 layers) / 49

Usage:
  python3 evaluator/evaluate.py "Mark Meier"
  python3 evaluator/evaluate.py "Mark Meier" --model qwen3.5:2b
  python3 evaluator/evaluate.py "Mark Meier" --layer-model L7=qwen-max
  python3 evaluator/evaluate.py "Mark Meier" --benchmark
  python3 evaluator/evaluate.py "Mark Meier" --json
"""
import argparse
import json
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
EVALUATOR_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "tools"
SEARCH_PY = TOOLS_DIR / "search.py"
MEMORY_PY = TOOLS_DIR / "memory.py"
MATRIX_PATH = BASE_DIR / "templates" / "person" / "00i-matrix.yaml"
RESULTS_DIR = EVALUATOR_DIR / "results"

# ── LLM ───────────────────────────────────────────────────────────────────
BITROUTER_URL = "http://127.0.0.1:4356/v1/chat/completions"
DEFAULT_MODEL = "clawd-rift-16k"
DEFAULT_BENCHMARK_MODELS = ["clawd-rift-16k", "qwen3.5:2b", "qwen/qwen3.6-flash"]

# ── Agents ────────────────────────────────────────────────────────────────
LAYER_IDS = ["L1", "L2", "L3", "L4", "L5", "L6", "L7"]
AGENT_NAMES = {
    "L1": "Scout",
    "L2": "Auditor",
    "L3": "Verifier",
    "L4": "Watcher",
    "L5": "Council",
    "L6": "Listener",
    "L7": "Elder",
}
PHASE1_LAYERS = ["L1"]
PHASE2_LAYERS = ["L2", "L3", "L4", "L5", "L6"]
PHASE3_LAYERS = ["L7"]


# ── Matrix ────────────────────────────────────────────────────────────────
def load_matrix() -> dict:
    """Load the 7x7 person matrix, keyed by layer id (L1..L7)."""
    if not MATRIX_PATH.exists():
        raise FileNotFoundError(f"Matrix definition not found: {MATRIX_PATH}")
    raw = yaml.safe_load(MATRIX_PATH.read_text())
    matrix = {}
    for key, body in raw.items():
        layer_id = key.split(".", 1)[0]
        matrix[layer_id] = {
            "key": key,
            "name": key.split(".", 1)[1] if "." in key else key,
            "question": (body or {}).get("question", ""),
            "factors": (body or {}).get("factors", {}) or {},
        }
    missing = [lid for lid in LAYER_IDS if lid not in matrix]
    if missing:
        raise ValueError(f"Matrix is missing layers: {missing}")
    return matrix


# ── Evidence tools (subprocess) ──────────────────────────────────────────
def _run_tool(cmd: list[str], timeout: int = 30) -> tuple[str | None, str | None]:
    """Run a tool subprocess. Returns (stdout, error). Never raises."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, f"{cmd[1] if len(cmd) > 1 else cmd[0]}: {e}"
    # search.py exits 1 on an empty non-json result set; both tools exit 1
    # when their backing store is empty/missing. Treat stdout as authoritative.
    if not proc.stdout.strip():
        stderr_lines = [ln for ln in proc.stderr.strip().splitlines() if ln.strip()]
        err = (stderr_lines[-1][:300] if stderr_lines else f"exit {proc.returncode}, no output")
        return None, err
    return proc.stdout, None


def search_evidence(query: str, max_results: int = 5) -> tuple[list[dict], str | None]:
    """Query the unified estate search tool."""
    stdout, err = _run_tool(
        [sys.executable, str(SEARCH_PY), query, "--json", "--max", str(max_results)],
        timeout=150,
    )
    if stdout is None:
        return [], err
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return [], "search.py: unparseable output"
    return data.get("results", []), None


def memory_evidence(query: str, top: int = 5) -> tuple[list[dict], str | None]:
    """Query semantic memory recall."""
    stdout, err = _run_tool(
        [sys.executable, str(MEMORY_PY), "recall", query, "--top", str(top), "--json"],
        timeout=60,
    )
    if stdout is None:
        return [], err
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return [], "memory.py: unparseable output"
    return data.get("results", []), None


def format_evidence(search_results: list[dict], memory_results: list[dict]) -> str:
    lines = []
    if search_results:
        lines.append("From estate search:")
        for r in search_results:
            src = r.get("source", "?")
            name = r.get("name", r.get("id", "?"))
            path = r.get("path", "")
            snippet = (r.get("snippet") or "").strip().replace("\n", " ")[:200]
            loc = f" ({path})" if path else ""
            lines.append(f"  - [{src}] {name}{loc}: {snippet}")
    if memory_results:
        lines.append("From semantic memory:")
        for r in memory_results:
            title = r.get("title", r.get("path", "?"))
            sim = r.get("similarity", 0.0)
            content = (r.get("content") or "").strip().replace("\n", " ")[:200]
            lines.append(f"  - [{sim:.2f}] {title}: {content}")
    return "\n".join(lines)


# ── LLM call ──────────────────────────────────────────────────────────────
def call_llm(prompt: str, model: str, max_tokens: int = 900, temperature: float = 0.2,
             timeout: int = 120) -> str:
    """Call BitRouter's OpenAI-compatible chat endpoint via urllib (no deps)."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")
    req = urllib.request.Request(
        BITROUTER_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer unused"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"BitRouter HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"BitRouter unreachable at {BITROUTER_URL}: {e.reason}") from e
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError(f"empty response from {model}: {json.dumps(body)[:300]}")
    return choices[0]["message"]["content"] or ""


def strip_think(text: str) -> str:
    """Strip <think>...</think> reasoning blocks some models emit."""
    return re.sub(r"<think>[\s\S]*?</think>", "", text).strip()


def extract_factor_scores(text: str, factors: dict) -> dict:
    """Parse the model's JSON array of {factor, score, reasoning} into a dict."""
    result = {name: {"score": 0.0, "reasoning": "not scored"} for name in factors}
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        for name in result:
            result[name]["reasoning"] = "no JSON array found in model response"
        return result
    try:
        items = json.loads(match.group())
    except json.JSONDecodeError:
        for name in result:
            result[name]["reasoning"] = "JSON parse error in model response"
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("factor")
        if name not in result:
            continue
        try:
            score = float(item.get("score", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        score = max(0.0, min(1.0, score))
        reasoning = str(item.get("reasoning", "")).strip() or "no reasoning given"
        result[name] = {"score": round(score, 2), "reasoning": reasoning}
    return result


# ── Prompting ────────────────────────────────────────────────────────────
def build_prompt(person: str, agent_name: str, layer_id: str, layer_name: str, question: str,
                  factors: dict, evidence_text: str, context_summary: str | None) -> str:
    factor_lines = "\n".join(f"- {name}: {desc}" for name, desc in factors.items())
    ctx = f"\n\nFindings from prior-layer agents (for context only):\n{context_summary}\n" if context_summary else ""
    return f"""You are {agent_name}, the {layer_id} ({layer_name}) evaluator in the OOi Person 7×7 matrix.

Central question for this layer: "{question}"

Evaluate {person} against these 7 factors. For each factor, assign a score from
0.0 (no evidence / entirely absent) to 1.0 (fully verified, strong evidence),
based ONLY on the evidence provided below. If there is no evidence for a
factor, score it 0.0 and say so — never invent evidence.

Factors:
{factor_lines}
{ctx}
Evidence gathered from the estate (search + memory):
{evidence_text or "(no evidence found)"}

Reply with ONLY a JSON array of exactly 7 objects, one per factor, in this
exact form and nothing else:
[{{"factor": "<factor_name>", "score": 0.0, "reasoning": "<one sentence, cite evidence or state none found>"}}]"""


# ── Agent ────────────────────────────────────────────────────────────────
def run_agent(layer_id: str, person: str, matrix: dict, model: str,
              context_summary: str | None = None, search_max: int = 5,
              quiet: bool = True) -> dict:
    layer = matrix[layer_id]
    agent_name = AGENT_NAMES[layer_id]
    factors = layer["factors"]

    if not quiet:
        print(f"  [{layer_id}:{agent_name}] gathering evidence...", file=sys.stderr)

    query = f"{person} {layer['question']}"
    search_results, search_err = search_evidence(query, max_results=search_max)
    memory_results, memory_err = memory_evidence(f"{person} {layer['name']} {layer['question']}", top=search_max)
    evidence_text = format_evidence(search_results, memory_results)

    prompt = build_prompt(person, agent_name, layer_id, layer["name"], layer["question"],
                           factors, evidence_text, context_summary)

    if not quiet:
        print(f"  [{layer_id}:{agent_name}] calling {model}...", file=sys.stderr)

    llm_error = None
    try:
        raw = call_llm(prompt, model)
        parsed = extract_factor_scores(strip_think(raw), factors)
    except Exception as e:  # noqa: BLE001 — agent must degrade, never crash the run
        llm_error = str(e)
        parsed = {name: {"score": 0.0, "reasoning": f"LLM error: {llm_error}"} for name in factors}

    result = {
        "layer": layer_id,
        "agent": agent_name,
        "name": layer["name"],
        "question": layer["question"],
        "model": model,
        "evidence_count": len(search_results) + len(memory_results),
        "factors": parsed,
    }
    warnings = [w for w in (search_err, memory_err) if w]
    if warnings:
        result["evidence_warnings"] = warnings
    if llm_error:
        result["llm_error"] = llm_error

    if not quiet:
        avg = sum(d["score"] for d in parsed.values()) / len(parsed) if parsed else 0.0
        print(f"  [{layer_id}:{agent_name}] avg score {avg:.2f}", file=sys.stderr)

    return result


def _agent_failure_result(layer_id: str, matrix: dict, model: str, error: str) -> dict:
    layer = matrix[layer_id]
    return {
        "layer": layer_id,
        "agent": AGENT_NAMES[layer_id],
        "name": layer["name"],
        "question": layer["question"],
        "model": model,
        "evidence_count": 0,
        "factors": {name: {"score": 0.0, "reasoning": f"agent error: {error}"} for name in layer["factors"]},
        "agent_error": error,
    }


def summarize_context(results: dict) -> str:
    """Compact per-layer summary fed forward to later-phase agents."""
    lines = []
    for lid in LAYER_IDS:
        r = results.get(lid)
        if not r:
            continue
        scores = [d["score"] for d in r["factors"].values()]
        avg = sum(scores) / len(scores) if scores else 0.0
        detail = ", ".join(f"{f}={d['score']:.1f}" for f, d in r["factors"].items())
        lines.append(f"- {lid} {r['agent']} ({r['name']}): avg={avg:.2f} [{detail}]")
    return "\n".join(lines)


# ── Orchestration ─────────────────────────────────────────────────────────
def run_phase_parallel(layer_ids: list[str], person: str, matrix: dict, model_for,
                        context_summary: str, max_concurrent: int, search_max: int,
                        quiet: bool) -> dict:
    """Run a batch of agents concurrently, gated to max_concurrent via a semaphore."""
    sem = threading.Semaphore(max_concurrent)
    lock = threading.Lock()
    out: dict = {}

    def worker(lid: str):
        with sem:
            try:
                r = run_agent(lid, person, matrix, model_for(lid), context_summary,
                              search_max=search_max, quiet=quiet)
            except Exception as e:  # noqa: BLE001 — one agent's crash must not sink the phase
                r = _agent_failure_result(lid, matrix, model_for(lid), str(e))
            with lock:
                out[lid] = r

    threads = [threading.Thread(target=worker, args=(lid,), name=f"agent-{lid}") for lid in layer_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return out


def run_evaluation(person: str, model: str = DEFAULT_MODEL, layer_models: dict | None = None,
                    max_concurrent: int = 2, search_max: int = 5, quiet: bool = False) -> tuple[dict, float]:
    matrix = load_matrix()
    layer_models = layer_models or {}

    def model_for(lid: str) -> str:
        return layer_models.get(lid, model)

    started = time.time()
    results: dict = {}

    if not quiet:
        print(f"\n=== Evaluating '{person}' ({model}) ===", file=sys.stderr)
        print("Phase 1: L1 Scout (solo)", file=sys.stderr)
    results["L1"] = run_agent("L1", person, matrix, model_for("L1"), search_max=search_max, quiet=quiet)

    if not quiet:
        names = ", ".join(AGENT_NAMES[l] for l in PHASE2_LAYERS)
        print(f"Phase 2: L2-L6 ({names}) — max {max_concurrent} concurrent", file=sys.stderr)
    context1 = summarize_context(results)
    results.update(run_phase_parallel(PHASE2_LAYERS, person, matrix, model_for, context1,
                                       max_concurrent, search_max, quiet))

    if not quiet:
        print("Phase 3: L7 Elder (needs all others)", file=sys.stderr)
    context2 = summarize_context(results)
    results["L7"] = run_agent("L7", person, matrix, model_for("L7"), context2,
                               search_max=search_max, quiet=quiet)

    elapsed = round(time.time() - started, 1)
    if not quiet:
        print(f"Done in {elapsed}s", file=sys.stderr)

    return results, elapsed


def compute_truth(results: dict) -> dict:
    """truth.rate = total factors scored > 0.0 across all layers / 49."""
    filled = 0
    total_score = 0.0
    total = 0
    for r in results.values():
        for d in r["factors"].values():
            total += 1
            total_score += d["score"]
            if d["score"] > 0.0:
                filled += 1
    return {
        "rate": round(filled / 49, 4),
        "filled": filled,
        "total": 49,
        "avg_score": round(total_score / total, 4) if total else 0.0,
    }


# ── Persistence ───────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip()).strip("_").lower()
    return slug or "unknown"


def save_results(person: str, results: dict, model: str, truth: dict, elapsed: float,
                  extra_tag: str | None = None) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"_{extra_tag}" if extra_tag else ""
    path = RESULTS_DIR / f"{slugify(person)}_{ts}{tag}.yaml"
    doc = {
        "person": person,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "elapsed_seconds": elapsed,
        "truth": truth,
        "layers": {lid: results[lid] for lid in LAYER_IDS if lid in results},
    }
    with open(path, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True, width=100)
    return path


# ── CLI ───────────────────────────────────────────────────────────────────
def parse_layer_models(pairs: list[str]) -> dict:
    out = {}
    for p in pairs:
        if "=" not in p:
            raise SystemExit(f"--layer-model expects LAYER=MODEL, got: {p!r}")
        lid, m = p.split("=", 1)
        lid = lid.strip().upper()
        if lid not in AGENT_NAMES:
            raise SystemExit(f"--layer-model: unknown layer {lid!r} (expected one of {LAYER_IDS})")
        out[lid] = m.strip()
    return out


def print_summary(person: str, results: dict, truth: dict, elapsed: float, model: str) -> None:
    print(f"\n{person} — truth.rate {truth['rate']:.2%} "
          f"({truth['filled']}/{truth['total']} factors filled) — {elapsed}s — {model}")
    for lid in LAYER_IDS:
        r = results.get(lid)
        if not r:
            continue
        scores = [d["score"] for d in r["factors"].values()]
        avg = sum(scores) / len(scores) if scores else 0.0
        flag = " ⚠" if r.get("llm_error") or r.get("agent_error") else ""
        print(f"  {lid} {r['agent']:<9} {r['name']:<10} avg={avg:.2f}{flag}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="evaluate.py",
        description="7-agent OOi Person 7x7 evaluator — scores a person across L1-L7 "
                     "layers using estate evidence (search + memory) and LLM agents via BitRouter.",
    )
    parser.add_argument("person", help="Person name to evaluate, e.g. 'Mark Meier'")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                         help=f"LLM model for all agents (default: {DEFAULT_MODEL})")
    parser.add_argument("--layer-model", action="append", default=[], metavar="LAYER=MODEL",
                         help="Override the model for one layer, e.g. --layer-model L7=qwen-max. Repeatable.")
    parser.add_argument("--benchmark", action="store_true",
                         help="Run the full evaluation once per model in --benchmark-models "
                              "and compare truth.rate across them")
    parser.add_argument("--benchmark-models", nargs=3, metavar=("MODEL1", "MODEL2", "MODEL3"),
                         default=DEFAULT_BENCHMARK_MODELS,
                         help=f"Models to compare in --benchmark mode (default: {DEFAULT_BENCHMARK_MODELS})")
    parser.add_argument("--max-concurrent", type=int, default=2,
                         help="Max concurrent agents in Phase 2 (default: 2)")
    parser.add_argument("--search-max", type=int, default=5,
                         help="Max evidence results per source, per agent (default: 5)")
    parser.add_argument("--json", action="store_true",
                         help="Print the full result as JSON to stdout (results are always also saved as YAML)")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output on stderr")
    args = parser.parse_args()

    try:
        layer_models = parse_layer_models(args.layer_model)

        if args.benchmark:
            summary = []
            all_results = {}
            for m in args.benchmark_models:
                results, elapsed = run_evaluation(args.person, model=m, max_concurrent=args.max_concurrent,
                                                    search_max=args.search_max, quiet=args.quiet)
                truth = compute_truth(results)
                path = save_results(args.person, results, m, truth, elapsed, extra_tag=slugify(m))
                all_results[m] = results
                summary.append({
                    "model": m, "truth_rate": truth["rate"], "filled": truth["filled"],
                    "avg_score": truth["avg_score"], "elapsed_seconds": elapsed, "path": str(path),
                })
                if not args.quiet:
                    print_summary(args.person, results, truth, elapsed, m)

            summary.sort(key=lambda x: x["truth_rate"], reverse=True)

            if args.json:
                print(json.dumps({"person": args.person, "benchmark": summary}, indent=2))
            else:
                print(f"\n=== Benchmark comparison for '{args.person}' ===")
                print(f"{'model':<28} {'truth.rate':>10} {'filled':>8} {'avg_score':>10} {'time(s)':>8}")
                for row in summary:
                    print(f"{row['model']:<28} {row['truth_rate']:>10.2%} {row['filled']:>8} "
                          f"{row['avg_score']:>10.3f} {row['elapsed_seconds']:>8.1f}")
            return

        results, elapsed = run_evaluation(args.person, model=args.model, layer_models=layer_models,
                                           max_concurrent=args.max_concurrent, search_max=args.search_max,
                                           quiet=args.quiet)
        truth = compute_truth(results)
        path = save_results(args.person, results, args.model, truth, elapsed)

        if args.json:
            print(json.dumps({
                "person": args.person, "model": args.model, "elapsed_seconds": elapsed,
                "truth": truth, "layers": results, "saved_to": str(path),
            }, indent=2))
        else:
            print_summary(args.person, results, truth, elapsed, args.model)
            print(f"\nSaved: {path}")
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:  # noqa: BLE001 — top-level CLI error boundary
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
