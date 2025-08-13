import asyncio
import tempfile
from pathlib import Path
from typing import List

import streamlit as st
import fitz                     # PyMuPDF (fitz) – PDF parser
from edge_tts import Communicate


# ----------------------------------------------------------------------
# Helper: extract text from a PDF (bytes -> str) – uses PyMuPDF (fitz)
# ----------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def extract_text_from_pdf_bytes(pdf_bytes: bytes, file_name: str = "") -> str:
    """
    Reads the given PDF bytes with PyMuPDF (fitz) and returns the extracted
    plain‑text content. If a page cannot be read, the function skips it and
    continues with the remaining pages. Shows warnings for unreadable pages.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texts = []
        for i, page in enumerate(doc):
            try:
                texts.append(page.get_text())
            except Exception as page_exc:
                st.warning(f"⚠️ Page {i+1} in **{file_name}** could not be read: {page_exc}")
        doc.close()
        return "\n".join(filter(None, texts)).strip()
    except Exception as exc:
        st.error(f"❌ Could not read PDF **{file_name}**: {exc}")
        return ""


# ----------------------------------------------------------------------
# Async wrapper for Edge‑TTS (offline)
# ----------------------------------------------------------------------
async def _async_tts(text: str, out_path: Path, voice: str = "en-GB-RyanNeural"):
    try:
        communicate = Communicate(text=text, voice=voice)
        await communicate.save(str(out_path))
    except Exception as exc:
        raise RuntimeError(f"TTS conversion failed: {exc}")


def text_to_mp3(text: str, out_path: Path, voice: str = "en-GB-RyanNeural"):
    asyncio.run(_async_tts(text, out_path, voice))


async def batch_texts_to_mp3(tasks: List[dict], voice: str):
    results = []
    for task in tasks:
        try:
            await _async_tts(task["text"], task["out_path"], voice)
            results.append({"name": task["name"], "success": True, "out_path": task["out_path"]})
        except Exception as exc:
            results.append({"name": task["name"], "success": False, "error": str(exc)})
    return results


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
st.set_page_config(page_title="PDF → MP3 (offline Edge‑TTS)", layout="centered")
st.title("📚 PDF → MP3 Converter")

st.markdown(
    """
    Upload **one or more** PDF files, pick a voice, and get back an MP3 for each.
    The conversion uses the **offline Edge TTS engine** – no external cloud service required.
    """
)

# Voice selector
VOICE_OPTIONS = {
    "English (UK) – Ryan (Neural)": "en-GB-RyanNeural",
    "English (US) – Jenny (Neural)": "en-US-JennyNeural",
    "English (US) – Guy (Neural)":   "en-US-GuyNeural",
    "Spanish (Spain) – Lucia (Neural)": "es-ES-LuciaNeural",
    "German (Germany) – Jonas (Neural)": "de-DE-JonasNeural",
}
voice_name = st.selectbox("🔊 Choose a voice", list(VOICE_OPTIONS.keys()))
voice_id = VOICE_OPTIONS[voice_name]

# File uploader
uploaded_files = st.file_uploader(
    "📂 Drag & drop PDF files here (or click to browse)",
    type=["pdf"],
    accept_multiple_files=True,
)

# ----------------------------------------------------------------------
# Prevent the same file from being processed twice
# ----------------------------------------------------------------------
# Deduplicate and store file bytes to avoid double reading
if uploaded_files:
    unique_files: List[dict] = []
    seen_names = set()
    for f in uploaded_files:
        if f.name not in seen_names:
            unique_files.append({"name": f.name, "bytes": f.read()})
            seen_names.add(f.name)
        else:
            st.warning(f"⚠️ Duplicate file `{f.name}` was ignored.")
    uploaded_files = unique_files

if not uploaded_files:
    st.info("👈 Select at least one PDF to start.")
    st.stop()

# ----------------------------------------------------------------------
# Create a *temporary* output directory that will vanish automatically
# ----------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp_dir:
    output_dir = Path(tmp_dir)
    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    generated_files: List[Path] = []

    # Prepare tasks
    tts_tasks = []
    extraction_failures = []
    for idx, uploaded in enumerate(uploaded_files, start=1):
        status_placeholder.info(f"🔎 **{uploaded['name']}** – extracting text…")
        text = extract_text_from_pdf_bytes(uploaded["bytes"], file_name=uploaded["name"])
        if not text:
            st.warning(f"⚠️ No readable text found in **{uploaded['name']}** – skipping.")
            extraction_failures.append(uploaded["name"])
            continue
        base_name = Path(uploaded['name']).stem
        out_path = output_dir / f"{base_name}_edge.mp3"
        tts_tasks.append({"text": text, "out_path": out_path, "name": uploaded['name']})
        generated_files.append(out_path)
        progress_bar.progress(idx / len(uploaded_files))

    if extraction_failures:
        st.info(f"ℹ️ The following files could not be extracted and were skipped: {', '.join(extraction_failures)}")

    # Batch TTS conversion
    if tts_tasks:
        status_placeholder.info("🎙️ Converting all files to MP3 in parallel…")
        try:
            results = asyncio.run(batch_texts_to_mp3(tts_tasks, voice=voice_id))
            success_count = 0
            for res in results:
                if res.get("success"):
                    st.success(f"✅ **{res['name']}** → `{Path(res['out_path']).name}`")
                    success_count += 1
                else:
                    st.error(f"❌ **{res['name']}** failed: {res['error']}")
            if success_count == 0:
                st.warning("⚠️ No files were converted successfully.")
        except Exception as exc:
            st.exception(exc)
    else:
        st.warning("⚠️ No valid PDF files to convert.")

    status_placeholder.empty()
    st.balloons()

    # ----------------------------------------------------------------------
    # Download section
    # ----------------------------------------------------------------------
    if generated_files:
        st.subheader("⬇️ Download your MP3 files")
        for mp3_path in generated_files:
            with open(mp3_path, "rb") as f:
                st.download_button(
                    label=f"Download `{mp3_path.name}`",
                    data=f,
                    file_name=mp3_path.name,
                    mime="audio/mpeg",
                )
    else:
        st.info("No MP3 files were generated.")