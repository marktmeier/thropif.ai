#!/usr/bin/env python3
"""
search.py — Unified search across the Meier estate.

Searches multiple sources in parallel and returns merged results:
  1. Vault (~/Vaults/) — Obsidian markdown notes
  2. Projects (~/Projects/) — code and docs
  3. CRM (~/crm/crm.db) — contacts and emails
  4. eDax feed (~/clawd/memory/edax-feed/) — harvested content
  5. OOi store (~/.ooi/) — classified objects

Usage:
  python3 tools/search.py "Ahmed order"
  python3 tools/search.py "EU 1223 regulation" --source vault
  python3 tools/search.py "ingredient" --max 20 --json
"""
import sys, json, re, argparse, sqlite3, os
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

HOME = Path.home()
VAULT = HOME / "Vaults"
PROJECTS = HOME / "Projects"
CRM_DB = HOME / "crm" / "crm.db"
EDAX_FEED = HOME / "clawd" / "memory" / "edax-feed"
OOI_STORE = HOME / ".ooi"
DATACENTER = HOME / "Cloud-Drive" / "04-Data-Center"


def search_files(root: Path, query: str, extensions: list[str], max_results: int = 10) -> list[dict]:
    """Search markdown/text files by content match."""
    query_lower = query.lower()
    terms = query_lower.split()
    results = []

    if not root.exists():
        return []

    for ext in extensions:
        for f in root.rglob(f"*{ext}"):
            if ".git" in f.parts or "node_modules" in f.parts or ".next" in f.parts:
                continue
            try:
                content = f.read_text(errors="ignore")
                content_lower = content.lower()

                # All terms must appear
                if not all(t in content_lower for t in terms):
                    continue

                # Score by term frequency
                score = sum(content_lower.count(t) for t in terms)

                # Title match bonus
                name_lower = f.stem.lower()
                if any(t in name_lower for t in terms):
                    score += 10

                # Snippet: find first match context
                idx = content_lower.find(terms[0])
                start = max(0, idx - 60)
                end = min(len(content), idx + 140)
                snippet = content[start:end].replace("\n", " ").strip()

                results.append({
                    "source": str(root.name),
                    "path": str(f.relative_to(HOME)),
                    "name": f.stem,
                    "score": score,
                    "snippet": snippet,
                    "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d"),
                })
            except (OSError, UnicodeDecodeError):
                continue

            if len(results) >= max_results * 3:  # collect more, sort later
                break

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


def search_vault(query: str, max_results: int = 10) -> list[dict]:
    """Search Obsidian vault notes."""
    return search_files(VAULT, query, [".md"], max_results)


def search_projects(query: str, max_results: int = 10) -> list[dict]:
    """Search project docs and code."""
    return search_files(PROJECTS, query, [".md", ".txt", ".yaml", ".yml"], max_results)


def search_edax(query: str, max_results: int = 10) -> list[dict]:
    """Search eDax feed entries."""
    return search_files(EDAX_FEED, query, [".md"], max_results)


def search_crm(query: str, max_results: int = 10) -> list[dict]:
    """Search CRM database (contacts + emails)."""
    if not CRM_DB.exists():
        return []

    results = []
    try:
        conn = sqlite3.connect(f"file:{CRM_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row

        # Search contacts
        for row in conn.execute(
            "SELECT name, email, org, sample_subjects FROM contacts WHERE "
            "name LIKE ? OR email LIKE ? OR org LIKE ? OR sample_subjects LIKE ? LIMIT ?",
            (f"%{query}%",) * 4 + (max_results,)
        ):
            results.append({
                "source": "crm",
                "type": "contact",
                "name": row["name"] or "",
                "email": row["email"] or "",
                "company": row["org"] or "",
                "snippet": (row["sample_subjects"] or "")[:140],
                "score": 5,
            })

        conn.close()
    except Exception:
        pass

    return results


def search_ooi(query: str, max_results: int = 10) -> list[dict]:
    """Search OOi layer store."""
    if not OOI_STORE.exists():
        return []

    query_lower = query.lower()
    results = []
    for layer_dir in OOI_STORE.iterdir():
        if not layer_dir.is_dir() or not layer_dir.name.startswith("L"):
            continue
        for f in layer_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                payload = data.get("payload", {})
                searchable = json.dumps(payload).lower()
                if query_lower in searchable:
                    results.append({
                        "source": "ooi",
                        "layer": data.get("layer", layer_dir.name),
                        "id": data.get("id", f.stem),
                        "name": payload.get("name", f.stem),
                        "snippet": payload.get("summary", payload.get("purpose", ""))[:140],
                        "score": 3,
                    })
            except (json.JSONDecodeError, OSError):
                continue

    return results[:max_results]


def search_all(query: str, sources: list[str] | None = None, max_results: int = 10) -> list[dict]:
    """Search all sources in parallel."""
    all_sources = {
        "vault": lambda: search_vault(query, max_results),
        "projects": lambda: search_projects(query, max_results),
        "edax": lambda: search_edax(query, max_results),
        "crm": lambda: search_crm(query, max_results),
        "ooi": lambda: search_ooi(query, max_results),
    }

    if sources:
        all_sources = {k: v for k, v in all_sources.items() if k in sources}

    results = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fn): name for name, fn in all_sources.items()}
        for future in as_completed(futures):
            try:
                results.extend(future.result())
            except Exception:
                pass

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:max_results]


def main():
    parser = argparse.ArgumentParser(description="Unified search across Meier estate")
    parser.add_argument("query", nargs="+", help="Search terms")
    parser.add_argument("--source", choices=["vault", "projects", "edax", "crm", "ooi"],
                        action="append", help="Limit to specific source(s)")
    parser.add_argument("--max", type=int, default=10, help="Max results")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    query = " ".join(args.query)
    results = search_all(query, args.source, args.max)

    if args.json:
        print(json.dumps({"query": query, "count": len(results), "results": results}, indent=2))
    else:
        if not results:
            print(f"No results for '{query}'")
            sys.exit(1)

        print(f"🔍 {len(results)} results for '{query}'\n")
        for i, r in enumerate(results, 1):
            src = r.get("source", "?")
            name = r.get("name", r.get("id", "?"))
            path = r.get("path", "")
            snippet = r.get("snippet", "")[:100]
            layer = r.get("layer", "")

            header = f"  {i}. [{src}{'/' + layer if layer else ''}] {name}"
            if path:
                header += f"  (~/{path})"
            print(header)
            if snippet:
                print(f"     {snippet}")
            print()


if __name__ == "__main__":
    main()
