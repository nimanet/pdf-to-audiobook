"""
PDF extraction utilities for pdf-to-audiobook.
"""

import fitz
import streamlit as st

@st.cache_data(show_spinner=False)
def extract_text_from_pdf_bytes(pdf_bytes: bytes, file_name: str = "") -> str:
    """
    Extracts plain text from PDF bytes using PyMuPDF (fitz).
    Skips unreadable pages and warns the user.
    Returns the extracted text or an empty string on failure.
    """
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            texts = []
            for i, page in enumerate(doc):
                try:
                    texts.append(page.get_text())
                except Exception as page_exc:
                    st.warning(f"⚠️ Page {i+1} in **{file_name}** could not be read: {page_exc}")
            return "\n".join(filter(None, texts)).strip()
    except Exception as exc:
        st.error(f"❌ Could not read PDF **{file_name}**: {exc}")
        return ""