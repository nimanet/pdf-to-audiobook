"""
Unit tests for PDF extraction utilities.
"""

import os
from utils.pdf_utils import extract_text_from_pdf_bytes

def test_extract_text_from_pdf_bytes_empty():
    """Should return empty string for empty bytes."""
    assert extract_text_from_pdf_bytes(b"") == ""

def test_extract_text_from_pdf_bytes_invalid():
    """Should return empty string for invalid PDF bytes."""
    assert extract_text_from_pdf_bytes(b"not a pdf", "fake.pdf") == ""

def test_extract_text_from_pdf_bytes_real_pdf():
    """Should extract text from a real PDF file."""
    # Create a simple PDF for testing
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello, PDF test!")
    pdf_bytes = doc.write()
    doc.close()
    text = extract_text_from_pdf_bytes(pdf_bytes, "test.pdf")
    assert "Hello, PDF test!" in text