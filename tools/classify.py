#!/usr/bin/env python3
"""
classify.py — Classify any input into OOi L1–L7 layers.

The Thropif.ai intake algorithm. Takes text (or a file) and returns:
  - Which OOi layer (L1–L7) it belongs to
  - Confidence score
  - Suggested storage path
  - Cloud policy

Two modes:
  1. Rules-based (fast, no LLM, keyword + pattern matching)
  2. LLM-assisted (slow, uses local model for ambiguous cases)

Usage:
  echo "BP Derma shipped 41 boxes to Kuwait" | python3 tools/classify.py
  python3 tools/classify.py --file document.md
  python3 tools/classify.py --text "Revenue Q2: €42k" --json
  python3 tools/classify.py --file scan.txt --llm   # use LLM for hard cases
"""
import sys, json, re, argparse
from pathlib import Path

# ── OOi Layer Definitions ────────────────────────────────────────────────────
LAYERS = {
    "L1": {
        "name": "Identity",
        "cloud": "CLOUD_OK",
        "owner": "Claude",
        "desc": "Public identity: name, purpose, tech, team, status",
        "keywords": ["name", "purpose", "about", "overview", "introduction",
                     "readme", "description", "mission", "what is", "who is"],
        "patterns": [r"(?i)^(about|overview|introduction|readme)", r"(?i)project.*(name|purpose)"],
    },
    "L2": {
        "name": "Structure",
        "cloud": "CLOUD_AUTH",
        "owner": "Claude",
        "desc": "Internal structure: folder tree, deps, git stats",
        "keywords": ["structure", "folder", "directory", "dependency", "import",
                     "package", "tree", "architecture", "module", "component"],
        "patterns": [r"(?i)(folder|directory|file).*(tree|structure)", r"(?i)package\.json", r"(?i)import\s+\{"],
    },
    "L3": {
        "name": "Rules",
        "cloud": "LOCAL_PREF",
        "owner": "Owner",
        "desc": "Locked constraints: regulatory, contracts, legal",
        "keywords": ["regulation", "compliance", "contract", "legal", "eu 1223",
                     "inci", "gmp", "iso", "cpsr", "sds", "msds", "restricted",
                     "banned", "limit", "maximum", "threshold", "law", "rule"],
        "patterns": [r"(?i)eu\s*1223", r"(?i)(regulation|directive)\s*(ec|eu)", r"(?i)(contract|agreement|terms)"],
    },
    "L4": {
        "name": "Metrics",
        "cloud": "LOCAL_PREF",
        "owner": "Claude",
        "desc": "Measurements: size, counts, timestamps, KPIs",
        "keywords": ["count", "size", "total", "metric", "kpi", "revenue",
                     "units", "quantity", "boxes", "shipped", "stock", "inventory",
                     "price", "cost", "margin", "percentage", "growth"],
        "patterns": [r"\d+\s*(units|boxes|kg|ml|EUR|USD|\$|€|%)", r"(?i)(revenue|profit|cost|margin).*\d"],
    },
    "L5": {
        "name": "Validation",
        "cloud": "LOCAL_ONLY",
        "owner": "Claude",
        "desc": "Quality signals: risks, health checks, test results",
        "keywords": ["test", "fail", "pass", "error", "warning", "risk",
                     "health", "status", "deploy", "build", "ci", "bug",
                     "issue", "fix", "broken", "down", "incident"],
        "patterns": [r"(?i)(test|build|deploy).*(fail|pass|error)", r"(?i)(bug|issue|incident)\s*#?\d+"],
    },
    "L6": {
        "name": "Worth",
        "cloud": "LOCAL_ONLY",
        "owner": "Claude",
        "desc": "Strategic value: 7×7 pillar cells, priority, roadmap",
        "keywords": ["strategy", "priority", "roadmap", "vision", "pillar",
                     "decision", "plan", "future", "goal", "objective",
                     "competitive", "market", "opportunity", "invest"],
        "patterns": [r"(?i)(strateg|roadmap|vision|priorit)", r"(?i)(decision|plan)\s*(d\d+|#\d+)"],
    },
    "L7": {
        "name": "Private",
        "cloud": "NEVER_CLOUD",
        "owner": "Owner",
        "desc": "Founder-only: personal notes, secrets, passwords",
        "keywords": ["password", "secret", "key", "token", "credential",
                     "private", "personal", "confidential", "salary",
                     "bank", "account", "ssn", "passport"],
        "patterns": [r"(?i)(password|secret|api.?key|token)\s*[:=]", r"sk-[a-zA-Z0-9]{20,}"],
    },
}

# ── Domain Detection ─────────────────────────────────────────────────────────
DOMAINS = {
    "core": ["meier festivals", "symbion8", "channel-ai", "ndax", "mail channels"],
    "ai-rag": ["_search", "mirag", "rag", "embedding", "qdrant", "vector"],
    "cosmetics": ["bp derma", "inci", "ingredient", "cosmetic", "skincare",
                  "formul", "cpsr", "gmp", "batch", "sku"],
    "marketing": ["nmtw", "rossmann", "hub", "campaign", "seo", "brand",
                  "social media", "instagram", "tiktok"],
    "finance-erp": ["invoice", "accounting", "erp", "revenue", "payment",
                    "coldcase", "settlement"],
    "mesh-devops": ["deploy", "docker", "pm2", "launchd", "tailscale",
                    "broker", "mesh", "skynet"],
    "operations": ["auth", "ciam", "sso", "jwt", "login", "user management"],
}


def score_layer(text: str) -> list[dict]:
    """Score text against all 7 layers. Returns sorted by confidence."""
    text_lower = text.lower()
    scores = []

    for layer_id, layer in LAYERS.items():
        score = 0.0

        # Keyword hits
        kw_hits = sum(1 for kw in layer["keywords"] if kw in text_lower)
        score += min(kw_hits * 0.15, 0.6)  # cap at 0.6 from keywords

        # Pattern hits (stronger signal)
        pat_hits = sum(1 for pat in layer["patterns"] if re.search(pat, text))
        score += min(pat_hits * 0.25, 0.5)

        # Length bonus for L7 (short secrets score higher)
        if layer_id == "L7" and len(text) < 200 and score > 0:
            score += 0.15

        scores.append({
            "layer": layer_id,
            "name": layer["name"],
            "cloud": layer["cloud"],
            "confidence": round(min(score, 1.0), 2),
            "kw_hits": kw_hits,
            "pat_hits": pat_hits,
        })

    scores.sort(key=lambda x: x["confidence"], reverse=True)
    return scores


def detect_domain(text: str) -> str | None:
    """Detect which estate domain the text relates to."""
    text_lower = text.lower()
    hits = {}
    for domain, keywords in DOMAINS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            hits[domain] = count
    if hits:
        return max(hits, key=hits.get)
    return None


def classify_llm(text: str) -> dict:
    """Use local LLM for ambiguous classification."""
    from openai import OpenAI
    client = OpenAI(base_url="http://127.0.0.1:4356/v1", api_key="unused")

    prompt = f"""Classify this text into exactly ONE OOi layer (L1-L7):

L1 = Identity (public info: name, purpose, what it is)
L2 = Structure (internal: folder tree, deps, architecture)
L3 = Rules (regulatory, contracts, legal constraints)
L4 = Metrics (numbers: counts, revenue, KPIs, inventory)
L5 = Validation (quality: test results, bugs, health, deploy status)
L6 = Worth (strategy: priorities, roadmap, decisions, market)
L7 = Private (secrets: passwords, tokens, personal/confidential)

Text: {text[:1000]}

Reply with ONLY a JSON object: {{"layer": "L?", "reason": "one sentence"}}"""

    try:
        resp = client.chat.completions.create(
            model="qwen3.5-27b-16k",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        # Extract JSON from response
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        return {"layer": "unknown", "reason": f"LLM error: {e}"}
    return {"layer": "unknown", "reason": "no response"}


def classify(text: str, use_llm: bool = False) -> dict:
    """Full classification pipeline."""
    scores = score_layer(text)
    top = scores[0]
    second = scores[1] if len(scores) > 1 else None

    # If ambiguous (top two close), optionally use LLM
    ambiguous = second and (top["confidence"] - second["confidence"]) < 0.1
    llm_result = None

    if use_llm and (ambiguous or top["confidence"] < 0.2):
        llm_result = classify_llm(text)

    domain = detect_domain(text)
    layer_id = llm_result["layer"] if llm_result and llm_result["layer"] != "unknown" else top["layer"]
    layer = LAYERS.get(layer_id, LAYERS["L1"])

    return {
        "layer": layer_id,
        "name": layer["name"],
        "cloud_policy": layer["cloud"],
        "confidence": top["confidence"],
        "domain": domain,
        "ambiguous": ambiguous,
        "llm_override": llm_result,
        "top_3": scores[:3],
        "store_path": f"~/.ooi/{layer_id}/",
    }


def main():
    parser = argparse.ArgumentParser(description="Classify input into OOi L1–L7 layers")
    parser.add_argument("--file", help="Read from file")
    parser.add_argument("--text", help="Classify this text")
    parser.add_argument("--llm", action="store_true", help="Use LLM for ambiguous cases")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.file:
        text = Path(args.file).expanduser().read_text()
    elif args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("Usage: echo 'text' | python3 tools/classify.py", file=sys.stderr)
        sys.exit(1)

    result = classify(text.strip(), use_llm=args.llm)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        c = result["confidence"]
        icon = "🟢" if c >= 0.4 else "🟡" if c >= 0.2 else "🔴"
        print(f"{icon} {result['layer']} — {result['name']} (confidence: {c})")
        print(f"   Cloud: {result['cloud_policy']}")
        if result["domain"]:
            print(f"   Domain: {result['domain']}")
        if result["ambiguous"]:
            print(f"   ⚠️  Ambiguous — close to {result['top_3'][1]['layer']} ({result['top_3'][1]['name']})")
        if result["llm_override"]:
            print(f"   🤖 LLM: {result['llm_override']['layer']} — {result['llm_override'].get('reason', '')}")
        print(f"   Store: {result['store_path']}")


if __name__ == "__main__":
    main()
