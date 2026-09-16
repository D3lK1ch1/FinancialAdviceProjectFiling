"""
Parser — extracts text + metadata from a PDF.

A PDF with no selectable text (scanned/image-only) is a flag, not silently
empty input — that's why has_selectable_text is returned explicitly rather
than left for the caller to infer from an empty string.

Per-page text is returned as well as the joined text. Extraction is already
page by page — the boundaries existed and were being discarded on the join.
They are the only evidence a split point can be argued from: a firm's file
is regularly one PDF holding more than one document, classically an SOA
with the Authority to Proceed appended (knowledge_base.json, edge_case_flags
-> multi_doc_bundle). Joined text cannot show where one document ends and
the next begins; a page index can.

Keeping both is deliberate. Callers that classify a whole file keep reading
extracted_text unchanged, and "\n".join(pages) == extracted_text always
holds, so the two can never disagree about what was in the file.
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
        "pages": pages_text,
    }
