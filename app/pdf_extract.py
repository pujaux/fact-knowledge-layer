"""Turn a PDF into a list of (page_number, text) tuples, then into
overlap-free character chunks small enough to send to Groq cheaply."""

import fitz  # PyMuPDF
from app.config import CHUNK_CHAR_SIZE


def extract_pages(pdf_path: str):
    """Returns [{"page": 1, "text": "..."}, ...] for every page with text."""
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": i, "text": text})
    doc.close()
    return pages


def chunk_pages(pages, chunk_size: int = CHUNK_CHAR_SIZE):
    """Groups consecutive pages into chunks under chunk_size chars.
    Keeps a chunk to a single page if that page alone is already large,
    so we never lose the page number a fact came from."""
    chunks = []
    buf_text, buf_pages = "", []

    for p in pages:
        if len(p["text"]) > chunk_size:
            # flush whatever is buffered, then send this big page alone
            if buf_text:
                chunks.append({"pages": buf_pages, "text": buf_text})
                buf_text, buf_pages = "", []
            chunks.append({"pages": [p["page"]], "text": p["text"][:chunk_size * 2]})
            continue

        if len(buf_text) + len(p["text"]) > chunk_size and buf_text:
            chunks.append({"pages": buf_pages, "text": buf_text})
            buf_text, buf_pages = "", []

        buf_text += f"\n\n[Page {p['page']}]\n{p['text']}"
        buf_pages.append(p["page"])

    if buf_text:
        chunks.append({"pages": buf_pages, "text": buf_text})

    return chunks
