"""
Unit tests for PDF extraction utilities.
"""

from utils.pdf_utils import extract_text_from_pdf_bytes

def test_extract_text_from_pdf_bytes_empty():
    assert extract_text_from_pdf_bytes(b"") == ""