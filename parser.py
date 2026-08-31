"""
Parser — extracts text + metadata from a PDF.

A PDF with no selectable text (scanned/image-only) is a flag, not silently
empty input — that's why has_selectable_text is returned explicitly rather
than left for the caller to infer from an empty string.
"""

from pypdf import PdfReader


def parse_pdf(file_path_or_stream, filename: str) -> dict:
    reader = PdfReader(file_path_or_stream)
    pages_text = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
    extracted_text = "\n".join(pages_text)

    return {
        "filename": filename,
        "page_count": len(reader.pages),
        "char_count": len(extracted_text),
        "has_selectable_text": len(extracted_text.strip()) > 0,
        "extracted_text": extracted_text,
    }
