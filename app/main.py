#!/usr/bin/env python3
"""
Thropif.ai — OOi Engine
http://localhost:7700

Phase 1: GIVER — gives value on day one.
8 apps + wheel view + depth view + command bar.
"""
from __future__ import annotations
import json, os, sys, time
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
