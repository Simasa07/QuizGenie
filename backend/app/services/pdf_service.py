from typing import List
import fitz  # PyMuPDF


def extract_text_from_pdf(filepath: str) -> str:
    """Extract raw text from a PDF file, page by page, using PyMuPDF."""
    text_parts = []
    with fitz.open(filepath) as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text().strip()
            if page_text:
                text_parts.append(f"[Page {page_num}]\n{page_text}")
    return "\n\n".join(text_parts)


def clean_text(raw_text: str) -> str:
    """Collapse whitespace and drop empty lines."""
    lines = [line.strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def chunk_text(text: str, max_chars: int = 3000) -> List[str]:
    """
    Simple paragraph-packing chunker: groups lines into chunks up to
    max_chars each. This is a V1 placeholder for "semantic chunking" -
    V2 can swap this for an embeddings-based splitter without changing
    the rest of the pipeline.
    """
    lines = text.split("\n")
    chunks: List[str] = []
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > max_chars:
            if current:
                chunks.append(current.strip())
            current = line
        else:
            current += "\n" + line

    if current.strip():
        chunks.append(current.strip())

    return chunks


def select_relevant_chunks(chunks: List[str], max_chunks: int = 6) -> List[str]:
    """
    V1 heuristic retrieval: take the first N chunks, which works fine for
    typical lecture-note-length PDFs. V2 will replace this with proper
    embedding-based relevant-content retrieval.
    """
    return chunks[:max_chunks]
