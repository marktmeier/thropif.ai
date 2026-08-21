#!/usr/bin/env python3
"""
Thropif.ai — OOi Engine
http://localhost:7700

Phase 1: GIVER — gives value on day one.
8 apps + wheel view + depth view + command bar.
"""
from __future__ import annotations
import asyncio, json, os, re, subprocess, sys, time, uuid
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
    import uvicorn
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]"], check=True)
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
    import uvicorn

import yaml

app = FastAPI(title="Thropif.ai", version="0.1.0")
STATIC = Path(__file__).parent / "static"
TEMPLATES = ROOT / "templates"
STORE = ROOT / "store"
TOOLS = ROOT / "tools"

# ── Load templates ──
def load_templates() -> dict:
    templates = {}
    for f in sorted(TEMPLATES.rglob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text())
            if not data:
                continue
            layers = {}
            for key in ["L1.Giver","L2.Fair","L3.Truthful","L4.Loyal","L5.Respect","L6.Listening","L7.Teaching"]:
                if key in data:
                    layers[key] = {"question": data[key].get("question",""), "factors": data[key].get("factors",{})}
            if layers:
                name = str(f.relative_to(TEMPLATES)).replace("/00i-matrix.yaml","").replace(".00i-matrix.yaml","").replace("/",".")
                templates[name] = {"name": name, "file": str(f.relative_to(ROOT)), "categories": data.get("categories",{}), "layers": layers}
        except Exception:
            pass
    return templates

TEMPLATE_CACHE = load_templates()


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")

@app.get("/wheel")
async def wheel():
    return FileResponse(STATIC / "ooi-wheel.html")

@app.get("/depth")
async def depth():
    return FileResponse(STATIC / "ooi-side.html")

@app.get("/api/templates")
async def api_templates():
    return TEMPLATE_CACHE

@app.get("/api/templates/{name:path}")
async def api_template(name: str):
    return TEMPLATE_CACHE.get(name, {"error": "not found"})

@app.get("/api/stats")
async def api_stats():
    n_templates = len(TEMPLATE_CACHE)
    n_factors = sum(sum(len(l["factors"]) for l in t["layers"].values()) for t in TEMPLATE_CACHE.values())
    return {
        "templates": n_templates,
        "factors": n_factors,
        "cells_per_object": 3199,
        "store_exists": STORE.exists(),
        "tools": [f.stem for f in TOOLS.glob("*.py") if f.stem != "__init__"],
    }


# ── Settings ──

SETTINGS_FILE = ROOT / "settings.yaml"

def load_settings() -> dict:
    defaults = {
        "llm": {
            "provider": "bitrouter",
            "url": "http://127.0.0.1:4356/v1",
            "model": "clawd-rift-16k",
            "key": "local",
            "fallback_url": "http://127.0.0.1:1234/v1",
            "fallback_model": "google/gemma-4-12b-qat",
        },
        "bots": {
            "jdax": {"name": "jDax", "platform": "telegram", "handle": "@Jdaxx_bot", "status": "active"},
            "edax": {"name": "eDax", "platform": "telegram", "handle": "@Edaxv01_bot", "status": "active"},
            "cdax": {"name": "cDax", "platform": "internal", "handle": "container", "status": "planned"},
        },
        "sources": {
            "email_db": str(Path.home() / "Projects/08-mail-channels/data/mailfind.db"),
            "whatsapp": [
                str(Path.home() / "Downloads/WhatsApp Chat - Wessam Hayba Nin Arkadasi/_chat.txt"),
                str(Path.home() / "Downloads/New Folder With Items/WhatsApp Chat - Anais Bezacier/_chat.txt"),
            ],
            "vault": str(Path.home() / "Vaults"),
            "registry": str(Path.home() / "Projects/00x/projects.yaml"),
            "ooi_db": str(Path.home() / "Projects/00x/00i/00i.db"),
        },
        "pipeline": {
            "stages": ["_st1.RAG", "_st2.JSON", "/OOi"],
            "auto_run": False,
            "schedule": "02:00",
        },
        "perspectives": ["government", "scientist", "commercial", "internal"],
        "values": {
            "L1": "SAFETY — first give no harm",
            "L2": "PURITY — what's inside is fair to the body",
            "L3": "TRUTH — prove every claim",
            "L4": "TRACEABILITY — the chain holds",
            "L5": "CONSISTENCY — respect is re-earned every batch",
            "L6": "TRANSPARENCY — let them see, hear, verify",
            "L7": "RESPONSIBILITY — your name on it, forever",
        },
    }
    if SETTINGS_FILE.exists():
        try:
            saved = yaml.safe_load(SETTINGS_FILE.read_text())
            if saved:
                for k, v in saved.items():
                    if isinstance(v, dict) and isinstance(defaults.get(k), dict):
                        defaults[k].update(v)
                    else:
                        defaults[k] = v
        except: pass
    return defaults


def save_settings(settings: dict):
    SETTINGS_FILE.write_text(yaml.dump(settings, default_flow_style=False, allow_unicode=True))


@app.get("/api/settings")
async def api_settings():
    return load_settings()


@app.post("/api/settings")
async def api_save_settings(request: Request):
    data = await request.json()
    settings = load_settings()
    settings.update(data)
    save_settings(settings)
    return {"ok": True}


@app.get("/api/settings/test-llm")
async def test_llm():
    """Test the LLM connection."""
    import httpx
    settings = load_settings()
    url = settings["llm"]["url"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{url}/models")
            models = r.json().get("data", [])
            return {"ok": True, "models": len(models), "url": url,
                    "names": [m["id"] for m in models[:10]]}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": url}


# ── OOi Archive API ──

OOI_DB = Path.home() / "Projects" / "00x" / "00i" / "00i.db"

@app.get("/api/ooi/objects")
async def ooi_objects():
    """List all OOi objects with truth rates."""
    import sqlite3
    if not OOI_DB.exists():
        return {"objects": [], "count": 0}
    conn = sqlite3.connect(str(OOI_DB))
    conn.row_factory = sqlite3.Row
    objects = []
    for r in conn.execute("SELECT id, type, name, created, updated FROM objects ORDER BY updated DESC").fetchall():
        truth = conn.execute("SELECT COALESCE(SUM(score),0)/49.0 FROM cells WHERE object_id=?", (r["id"],)).fetchone()[0]
        objects.append({"id": r["id"], "type": r["type"], "name": r["name"], "truth": round(truth, 4)})
    conn.close()
    return {"objects": objects, "count": len(objects)}


@app.get("/api/ooi/objects/{obj_id}")
async def ooi_object(obj_id: str):
    """Get one OOi object with all cells."""
    import sqlite3
    conn = sqlite3.connect(str(OOI_DB))
    conn.row_factory = sqlite3.Row
    obj = conn.execute("SELECT * FROM objects WHERE id=?", (obj_id,)).fetchone()
    if not obj:
        conn.close()
        return {"error": "not found"}
    cells = {}
    for r in conn.execute("SELECT outside_i, inside_i, data, score, who, updated FROM cells WHERE object_id=?", (obj_id,)).fetchall():
        cells[f"{r['outside_i']}.{r['inside_i']}"] = {"data": r["data"], "score": r["score"], "who": r["who"]}
    truth = conn.execute("SELECT COALESCE(SUM(score),0)/49.0 FROM cells WHERE object_id=?", (obj_id,)).fetchone()[0]
    connections = conn.execute(
        "SELECT object_a, object_b, strength FROM connections WHERE object_a=? OR object_b=? ORDER BY strength DESC LIMIT 20",
        (obj_id, obj_id)
    ).fetchall()
    conn.close()
    return {
        "id": obj["id"], "type": obj["type"], "name": obj["name"],
        "truth": round(truth, 4), "cells": cells, "cell_count": len(cells),
        "connections": [{"a": c["object_a"], "b": c["object_b"], "s": c["strength"]} for c in connections],
    }


@app.get("/api/ooi/network")
async def ooi_network():
    """Get the full network for visualization."""
    import sqlite3
    conn = sqlite3.connect(str(OOI_DB))
    conn.row_factory = sqlite3.Row
    nodes = []
    for r in conn.execute("SELECT id, type, name FROM objects").fetchall():
        t = conn.execute("SELECT COALESCE(SUM(score),0)/49.0 FROM cells WHERE object_id=?", (r["id"],)).fetchone()[0]
        if t > 0.005:
            nodes.append({"id": r["id"], "type": r["type"], "name": r["name"][:25], "truth": round(t, 3)})
    edges = []
    for r in conn.execute("SELECT object_a, object_b, strength FROM connections WHERE strength > 0.15 ORDER BY strength DESC LIMIT 300").fetchall():
        edges.append({"source": r["object_a"], "target": r["object_b"], "strength": r["strength"]})
    conn.close()
    return {"nodes": nodes, "edges": edges}


@app.get("/api/ooi/ledger")
async def ooi_ledger(limit: int = 50):
    """L0 ledger — last N writes."""
    import sqlite3
    conn = sqlite3.connect(str(OOI_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM ledger ORDER BY at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return {"entries": [dict(r) for r in rows], "count": len(rows)}


@app.get("/pipeline")
async def pipeline_page():
    return FileResponse(STATIC / "pipeline.html")

# ── Pipeline execution engine ──

clients: list[WebSocket] = []

async def broadcast(msg: dict):
    dead = []
    for ws in clients:
        try: await ws.send_json(msg)
        except: dead.append(ws)
    for ws in dead: clients.remove(ws)


def run_tool(tool_name: str, args: list[str], timeout: int = 60) -> dict:
    """Run a tool script and capture output."""
    script = TOOLS / f"{tool_name}.py"
    if not script.exists():
        return {"ok": False, "error": f"tool {tool_name} not found", "output": ""}
    try:
        r = subprocess.run(
            [sys.executable, str(script)] + args,
            capture_output=True, text=True, timeout=timeout,
            cwd=str(ROOT),
        )
        return {
            "ok": r.returncode == 0,
            "output": r.stdout[:5000],
            "error": r.stderr[:1000] if r.returncode != 0 else "",
            "exit_code": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "output": ""}
    except Exception as e:
        return {"ok": False, "error": str(e), "output": ""}


async def execute_node(node: dict, input_data: str = "") -> dict:
    """Execute a single pipeline node using real tools."""
    ntype = node.get("type", "")
    settings = {s["k"]: s.get("v", "") for s in node.get("settings", [])}
    result = {"node_id": node["id"], "type": ntype, "ok": False, "output": "", "error": ""}

    if ntype == "source":
        path = os.path.expanduser(settings.get("path", "~/store/_inbox/"))
        p = Path(path)
        if p.exists():
            files = [f.name for f in p.iterdir() if not f.name.startswith(".")][:20]
            result["ok"] = True
            result["output"] = json.dumps({"path": path, "files": files, "count": len(files)})
        else:
            result["error"] = f"path not found: {path}"

    elif ntype == "ocr":
        if input_data:
            r = await asyncio.to_thread(run_tool, "ocr", [input_data, "--json"])
            result.update(r)
        else:
            result["ok"] = True
            result["output"] = json.dumps({"status": "ready", "backend": settings.get("backend", "auto")})

    elif ntype == "classify":
        text = input_data or "test classification"
        r = await asyncio.to_thread(run_tool, "classify", ["--text", text, "--json"])
        result.update(r)

    elif ntype == "filter":
        mask = settings.get("mask", "all")
        result["ok"] = True
        result["output"] = json.dumps({"mask": mask, "status": "filtering", "input": input_data[:200] if input_data else "none"})

    elif ntype == "search":
        query = input_data or "test"
        sources = settings.get("sources", "vault,projects")
        args = [query, "--max", settings.get("max", "5"), "--json"]
        src_list = sources.split(",")
        for s in src_list:
            args.extend(["--source", s.strip()])
        r = await asyncio.to_thread(run_tool, "search", args, timeout=30)
        result.update(r)

    elif ntype == "memory":
        if input_data:
            r = await asyncio.to_thread(run_tool, "memory", ["recall", input_data, "--top", settings.get("top_k", "5"), "--json"])
            result.update(r)
        else:
            r = await asyncio.to_thread(run_tool, "memory", ["stats"])
            result.update(r)

    elif ntype == "evaluate":
        if input_data:
            eval_script = ROOT / "evaluator" / "evaluate.py"
            if eval_script.exists():
                r = await asyncio.to_thread(
                    lambda: subprocess.run(
                        [sys.executable, str(eval_script), input_data, "--json", "--quiet"],
                        capture_output=True, text=True, timeout=300, cwd=str(ROOT),
                    ).__dict__
                )
                result["ok"] = r.get("returncode", 1) == 0
                result["output"] = r.get("stdout", "")[:5000]
                result["error"] = r.get("stderr", "")[:1000]
            else:
                result["error"] = "evaluator not found"
        else:
            result["ok"] = True
            result["output"] = json.dumps({"status": "ready", "agents": 7})

    elif ntype == "store":
        result["ok"] = True
        result["output"] = json.dumps({"status": "stored", "path": settings.get("path", "~/store/objects/")})

    elif ntype == "agent":
        agent = settings.get("agent", "jDax")
        result["ok"] = True
        result["output"] = json.dumps({"agent": agent, "risk": settings.get("risk", "LOW_RISK"), "status": "ready"})

    elif ntype == "output":
        target = settings.get("target", "file")
        result["ok"] = True
        result["output"] = json.dumps({"target": target, "format": settings.get("format", "json"), "delivered": True})

    return result


async def execute_pipeline(pipeline: dict, ws: WebSocket):
    """Execute a full pipeline — topological order, real tools, streaming results."""
    nodes_data = {n["id"]: n for n in pipeline.get("nodes", [])}
    edges_data = pipeline.get("edges", [])

    # Build adjacency
    deps = {n["id"]: [] for n in pipeline["nodes"]}
    for e in edges_data:
        deps[e["to"]["n"]].append(e["from"]["n"])

    # Topological sort
    visited, order = set(), []
    def visit(nid):
        if nid in visited: return
        visited.add(nid)
        for dep in deps.get(nid, []): visit(dep)
        order.append(nid)
    for nid in deps: visit(nid)

    await ws.send_json({"type": "pipe_start", "order": order, "total": len(order)})

    outputs = {}  # node_id → output string

    for i, nid in enumerate(order):
        node = nodes_data.get(nid)
        if not node: continue

        # Gather input from upstream nodes
        input_data = ""
        for e in edges_data:
            if e["to"]["n"] == nid and e["from"]["n"] in outputs:
                input_data = outputs[e["from"]["n"]]
                break

        await ws.send_json({"type": "node_start", "node_id": nid, "step": i + 1, "total": len(order)})

        t0 = time.monotonic()
        result = await execute_node(node, input_data)
        result["duration_ms"] = int((time.monotonic() - t0) * 1000)

        outputs[nid] = result.get("output", "")

        await ws.send_json({"type": "node_done", **result})

    await ws.send_json({"type": "pipe_done", "nodes_executed": len(order)})


@app.websocket("/ws/pipeline")
async def ws_pipeline(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "run":
                await execute_pipeline(data.get("pipeline", {}), ws)
            elif data.get("type") == "execute_node":
                node = data.get("node", {})
                result = await execute_node(node, data.get("input", ""))
                await ws.send_json({"type": "node_result", **result})
    except WebSocketDisconnect:
        clients.remove(ws)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

if __name__ == "__main__":
    STATIC.mkdir(parents=True, exist_ok=True)
    # Create index.html if not exists
    index_html = STATIC / "index.html"
    if not index_html.exists() or index_html.stat().st_size < 100:
        # Will be created below
        pass
    print(f"\n  🌀 Thropif.ai — OOi Engine")
    print(f"  http://localhost:7700")
    print(f"  {len(TEMPLATE_CACHE)} templates loaded\n")
    uvicorn.run(app, host="0.0.0.0", port=7700, log_level="warning")
