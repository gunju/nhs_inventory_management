"""
Document chunking strategy for RAG ingestion.
Uses a simple sliding-window character chunker.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings

settings = get_settings()


@dataclass
class Chunk:
    index: int
    content: str
    page_number: int | None = None
    token_estimate: int = 0


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[Chunk]:
    """Split text into overlapping chunks by character count."""
    chunk_size = chunk_size or settings.rag_chunk_size * 4  # chars ≈ tokens * 4
    overlap = overlap or settings.rag_chunk_overlap * 4

    if not text.strip():
        return []

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        # Try to break at sentence boundary
        if end < text_len:
            for sep in [". ", ".\n", "\n\n", "\n"]:
                pos = text.rfind(sep, start, end)
                if pos > start + chunk_size // 2:
                    end = pos + len(sep)
                    break

        content = text[start:end].strip()
        if content:
            chunks.append(Chunk(
                index=idx,
                content=content,
                token_estimate=len(content) // 4,
            ))
            idx += 1
        start = end - overlap

    return chunks


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n\n".join(pages)
    except ImportError:
        raise RuntimeError("pypdf not installed. pip install pypdf")
    except Exception as exc:
        raise RuntimeError(f"PDF extraction failed: {exc}") from exc


def extract_text_from_file(file_path: str, mime_type: str | None = None) -> str:
    """Dispatch text extraction based on file type."""
    if file_path.lower().endswith(".pdf") or mime_type == "application/pdf":
        return extract_text_from_pdf(file_path)
    elif file_path.lower().endswith((".txt", ".md")):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file type: {file_path}")
