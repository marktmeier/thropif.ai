#!/usr/bin/env python3
"""
ocr.py — Extract text from images and PDFs.

Three backends, auto-selected:
  1. PyMuPDF (PDFs with embedded text — fast, no AI)
  2. Tesseract (images / scanned PDFs — local, fast)
  3. LM Studio vision model (complex layouts — slow, best quality)

Usage:
  python3 tools/ocr.py invoice.pdf
  python3 tools/ocr.py photo.jpg
  python3 tools/ocr.py scan.png --backend vision
  python3 tools/ocr.py document.pdf --pages 1-3
  python3 tools/ocr.py receipt.jpg --json

Output: extracted text to stdout (or JSON with --json).
"""
import sys, json, subprocess, argparse, base64, tempfile
from pathlib import Path

def ocr_pymupdf(path: Path, pages: list[int] | None = None) -> list[dict]:
    """Extract text from PDF using PyMuPDF (embedded text only)."""
    import fitz
    doc = fitz.open(str(path))
    results = []
    for i, page in enumerate(doc):
        if pages and (i + 1) not in pages:
            continue
        text = page.get_text("text").strip()
        if text:
            results.append({"page": i + 1, "text": text, "backend": "pymupdf"})
    doc.close()
    return results


def ocr_tesseract(path: Path) -> list[dict]:
    """OCR an image using Tesseract."""
    r = subprocess.run(
        ["tesseract", str(path), "stdout", "-l", "eng+deu+tur"],
        capture_output=True, text=True, timeout=30
    )
    text = r.stdout.strip()
    if text:
        return [{"page": 1, "text": text, "backend": "tesseract"}]
    return []


def ocr_vision(path: Path, model: str = "surya-ocr-2") -> list[dict]:
    """OCR using LM Studio vision model (best for complex layouts)."""
    from openai import OpenAI
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="unused")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        # Convert first page to image via PyMuPDF
        import fitz
        doc = fitz.open(str(path))
        page = doc[0]
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        doc.close()
    else:
        img_bytes = path.read_bytes()

    b64 = base64.b64encode(img_bytes).decode()
    mime = "image/png" if suffix in (".png", ".pdf") else "image/jpeg"

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text from this image. Return only the text, preserving layout and structure. No commentary."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                ]
            }],
            max_tokens=4096,
            temperature=0.1,
        )
        text = resp.choices[0].message.content.strip()
        return [{"page": 1, "text": text, "backend": f"vision:{model}"}]
    except Exception as e:
        return [{"page": 1, "text": "", "backend": f"vision:{model}", "error": str(e)}]


def pdf_to_images(path: Path, pages: list[int] | None = None) -> list[Path]:
    """Convert PDF pages to temporary PNG files for Tesseract."""
    import fitz
    doc = fitz.open(str(path))
    tmp_dir = Path(tempfile.mkdtemp())
    paths = []
    for i, page in enumerate(doc):
        if pages and (i + 1) not in pages:
            continue
        pix = page.get_pixmap(dpi=200)
        out = tmp_dir / f"page_{i+1}.png"
        pix.save(str(out))
        paths.append(out)
    doc.close()
    return paths


def parse_pages(s: str) -> list[int]:
    """Parse '1-3,5' into [1,2,3,5]."""
    result = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            result.extend(range(int(a), int(b) + 1))
        else:
            result.append(int(part))
    return result


def main():
    parser = argparse.ArgumentParser(description="OCR: extract text from images and PDFs")
    parser.add_argument("file", help="Image or PDF file")
    parser.add_argument("--backend", choices=["auto", "pymupdf", "tesseract", "vision"], default="auto")
    parser.add_argument("--model", default="surya-ocr-2", help="Vision model for --backend vision")
    parser.add_argument("--pages", help="Page range for PDFs (e.g. 1-3,5)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    path = Path(args.file).expanduser()
    if not path.exists():
        print(f"Error: {path} not found", file=sys.stderr)
        sys.exit(1)

    pages = parse_pages(args.pages) if args.pages else None
    is_pdf = path.suffix.lower() == ".pdf"
    results = []

    if args.backend == "auto":
        if is_pdf:
            # Try embedded text first
            results = ocr_pymupdf(path, pages)
            if not results:
                # Scanned PDF — convert to images, run tesseract
                imgs = pdf_to_images(path, pages)
                for img in imgs:
                    page_num = int(img.stem.split("_")[1])
                    for r in ocr_tesseract(img):
                        r["page"] = page_num
                        results.append(r)
        else:
            results = ocr_tesseract(path)
    elif args.backend == "pymupdf":
        results = ocr_pymupdf(path, pages)
    elif args.backend == "tesseract":
        if is_pdf:
            imgs = pdf_to_images(path, pages)
            for img in imgs:
                page_num = int(img.stem.split("_")[1])
                for r in ocr_tesseract(img):
                    r["page"] = page_num
                    results.append(r)
        else:
            results = ocr_tesseract(path)
    elif args.backend == "vision":
        results = ocr_vision(path, args.model)

    if args.json:
        print(json.dumps({"file": str(path), "pages": len(results), "results": results}, indent=2))
    else:
        for r in results:
            if len(results) > 1:
                print(f"--- Page {r['page']} ({r['backend']}) ---")
            print(r["text"])
            if r.get("error"):
                print(f"[Error: {r['error']}]", file=sys.stderr)

    sys.exit(0 if results else 1)


if __name__ == "__main__":
    main()
