#!/usr/bin/env python3
"""
memory.py — Agent memory interface: read, embed, recall.

Combines vault reading, embedding, and semantic recall into one tool.
Uses Ollama nomic-embed-text for embeddings, SQLite for the vector store.

Modes:
  ingest  — Read files into the memory DB with embeddings
  recall  — Semantic search (find similar content by meaning)
  read    — Read a vault note or file by path/title
  stats   — Show memory DB statistics

Usage:
  python3 tools/memory.py ingest ~/Vaults/MasterMind/
  python3 tools/memory.py recall "What is Mark's background?"
  python3 tools/memory.py read "VAULT-INDEX"
  python3 tools/memory.py stats
  python3 tools/memory.py recall "EU regulation cosmetics" --top 5 --json
"""
import sys, json, argparse, struct, sqlite3, hashlib
from pathlib import Path
from datetime import datetime

HOME = Path.home()
VAULT = HOME / "Vaults"
MEMORY_DB = HOME / "Projects" / "00x" / "tools" / ".memory.db"
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 500  # chars per chunk


def get_embedding(text: str) -> list[float]:
    """Get embedding vector from Ollama."""
    import urllib.request
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embed",
        data=json.dumps({"model": EMBED_MODEL, "input": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["embeddings"][0]


def vec_to_bytes(vec: list[float]) -> bytes:
    """Pack float vector to bytes for SQLite storage."""
    return struct.pack(f"{len(vec)}f", *vec)


def bytes_to_vec(b: bytes) -> list[float]:
    """Unpack bytes to float vector."""
    n = len(b) // 4
    return list(struct.unpack(f"{n}f", b))


def cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize the memory database."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            path TEXT,
            title TEXT,
            chunk_idx INTEGER,
            content TEXT,
            embedding BLOB,
            source TEXT,
            ingested_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_path ON chunks(path)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON chunks(source)")
    conn.commit()
    return conn


def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Split text into chunks, preserving paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) > size and current:
            chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para if current else para

    if current.strip():
        chunks.append(current.strip())

    return chunks or [text[:size]]


def ingest_file(conn: sqlite3.Connection, path: Path, source: str = "vault"):
    """Ingest a single file into the memory DB."""
    try:
        content = path.read_text(errors="ignore")
    except OSError:
        return 0

    if len(content.strip()) < 20:
        return 0

    title = path.stem
    chunks = chunk_text(content)
    count = 0

    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{path}:{i}:{chunk[:100]}".encode()).hexdigest()

        # Skip if already ingested
        existing = conn.execute("SELECT id FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
        if existing:
            continue

        try:
            embedding = get_embedding(chunk[:2000])  # cap input
        except Exception as e:
            print(f"  ⚠ Embed failed for {path.name}:{i}: {e}", file=sys.stderr)
            continue

        conn.execute(
            "INSERT OR REPLACE INTO chunks (id, path, title, chunk_idx, content, embedding, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (chunk_id, str(path), title, i, chunk, vec_to_bytes(embedding), source, datetime.now().isoformat())
        )
        count += 1

    conn.commit()
    return count


def cmd_ingest(args):
    """Ingest files from a directory."""
    target = Path(args.path).expanduser()
    if not target.exists():
        print(f"Error: {target} not found", file=sys.stderr)
        sys.exit(1)

    conn = init_db(MEMORY_DB)
    total = 0
    files = list(target.rglob("*.md")) if target.is_dir() else [target]
    files = [f for f in files if ".git" not in f.parts and ".obsidian" not in f.parts]

    print(f"Ingesting {len(files)} files from {target}...")
    for i, f in enumerate(files):
        n = ingest_file(conn, f, source=args.source or target.name)
        total += n
        if n > 0:
            print(f"  ✅ {f.name} ({n} chunks)")
        if (i + 1) % 50 == 0:
            print(f"  ... {i + 1}/{len(files)} files processed")

    conn.close()
    print(f"\nIngested {total} new chunks from {len(files)} files.")


def cmd_recall(args):
    """Semantic search — find chunks by meaning."""
    conn = init_db(MEMORY_DB)
    query_vec = get_embedding(args.query)

    rows = conn.execute("SELECT path, title, chunk_idx, content, embedding, source FROM chunks").fetchall()
    if not rows:
        print("Memory is empty. Run: python3 tools/memory.py ingest ~/Vaults/", file=sys.stderr)
        sys.exit(1)

    scored = []
    for path, title, idx, content, emb_bytes, source in rows:
        emb = bytes_to_vec(emb_bytes)
        sim = cosine_sim(query_vec, emb)
        scored.append({
            "path": path,
            "title": title,
            "chunk": idx,
            "content": content[:300],
            "similarity": round(sim, 4),
            "source": source,
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    top = scored[:args.top]

    if args.json:
        print(json.dumps({"query": args.query, "results": top}, indent=2))
    else:
        print(f"🧠 Top {len(top)} memories for '{args.query}':\n")
        for i, r in enumerate(top, 1):
            sim_bar = "█" * int(r["similarity"] * 20) + "░" * (20 - int(r["similarity"] * 20))
            print(f"  {i}. [{r['source']}] {r['title']} (chunk {r['chunk']})")
            print(f"     {sim_bar} {r['similarity']}")
            print(f"     {r['content'][:120]}...")
            print()

    conn.close()


def cmd_read(args):
    """Read a vault note by title or path."""
    query = args.title.lower()

    # Search vault
    for f in VAULT.rglob("*.md"):
        if ".obsidian" in f.parts:
            continue
        if query in f.stem.lower() or query in str(f).lower():
            print(f"📄 {f.relative_to(HOME)}\n")
            print(f.read_text(errors="ignore"))
            return

    print(f"Not found: '{args.title}' in ~/Vaults/", file=sys.stderr)
    sys.exit(1)


def cmd_stats(args):
    """Show memory DB statistics."""
    if not MEMORY_DB.exists():
        print("No memory DB yet. Run: python3 tools/memory.py ingest ~/Vaults/")
        return

    conn = init_db(MEMORY_DB)
    total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    sources = conn.execute(
        "SELECT source, COUNT(*) as n FROM chunks GROUP BY source ORDER BY n DESC"
    ).fetchall()
    latest = conn.execute(
        "SELECT ingested_at FROM chunks ORDER BY ingested_at DESC LIMIT 1"
    ).fetchone()

    print(f"🧠 Memory DB: {MEMORY_DB}")
    print(f"   Total chunks: {total}")
    print(f"   Last ingest: {latest[0] if latest else 'never'}")
    print(f"   Sources:")
    for source, count in sources:
        print(f"     {source}: {count} chunks")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Agent memory: ingest, recall, read")
    sub = parser.add_subparsers(dest="cmd")

    p_ingest = sub.add_parser("ingest", help="Ingest files into memory DB")
    p_ingest.add_argument("path", help="Directory or file to ingest")
    p_ingest.add_argument("--source", help="Source label (default: directory name)")

    p_recall = sub.add_parser("recall", help="Semantic search by meaning")
    p_recall.add_argument("query", help="What to remember")
    p_recall.add_argument("--top", type=int, default=5, help="Number of results")
    p_recall.add_argument("--json", action="store_true")

    p_read = sub.add_parser("read", help="Read a vault note by title")
    p_read.add_argument("title", help="Note title or path fragment")

    p_stats = sub.add_parser("stats", help="Memory DB statistics")

    args = parser.parse_args()
    if args.cmd == "ingest":
        cmd_ingest(args)
    elif args.cmd == "recall":
        cmd_recall(args)
    elif args.cmd == "read":
        cmd_read(args)
    elif args.cmd == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
