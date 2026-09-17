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
    """Extract text, or explain why not. This never raises on a bad file.

    Failing soft is the point. A PDF that cannot be opened — encrypted with a
    user password, corrupt, truncated, or not a PDF at all — used to escape as
    an unhandled exception and return HTTP 500, so a reviewer got a stack
    trace where a document should have been. That is the same defect #22 was
    about ("a document we cannot read is treated the same as a document that
    is not advice"), except worse: it was not treated as anything.

    The shape of the result is the same either way, so every caller can read
    it without branching on whether parsing worked. `parse_error` carries the
    reason when it did not, and review.py turns that into a review reason with
    a destination.
    """
    try:
        reader = PdfReader(file_path_or_stream)
        pages_text = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
        page_count = len(reader.pages)
    except Exception as e:
        # Deliberately broad. pypdf raises DependencyError for AES without
        # `cryptography`, PdfReadError for corruption, FileNotDecryptedError
        # for a user password, and plain ValueError/OSError for things that
        # are not PDFs at all. Enumerating them would leave the next kind of
        # bad file crashing, and the caller's response is the same for all of
        # them: hand it to a person and say why.
        return {
            "filename": filename,
            "page_count": 0,
            "char_count": 0,
            "has_selectable_text": False,
            "extracted_text": "",
            "pages": [],
            "parse_error": f"{type(e).__name__}: {e}",
        }

    extracted_text = "\n".join(pages_text)
    return {
        "filename": filename,
        "page_count": page_count,
        "char_count": len(extracted_text),
        "has_selectable_text": len(extracted_text.strip()) > 0,
        "extracted_text": extracted_text,
        "pages": pages_text,
        "parse_error": None,
    }
