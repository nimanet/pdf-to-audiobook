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
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Reads the given PDF bytes with PyMuPDF (fitz) and returns the extracted
    plain‑text content.  If a page cannot be read the function simply skips it
    and continues with the remaining pages.
    """
    try:
        # Open the PDF directly from the in‑memory bytes object.
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texts = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(filter(None, texts)).strip()
    except Exception as exc:                     # pragma: no cover
        st.error(f"❌ Could not read PDF: {exc}")
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
    coros = [
        _async_tts(task["text"], task["out_path"], voice)
        for task in tasks
    ]
    await asyncio.gather(*coros)


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
    for idx, uploaded in enumerate(uploaded_files, start=1):
        status_placeholder.info(f"🔎 **{uploaded['name']}** – extracting text…")
        text = extract_text_from_pdf_bytes(uploaded["bytes"])
        if not text:
            st.warning(f"⚠️ No readable text found in **{uploaded['name']}** – skipping.")
            continue
        base_name = Path(uploaded['name']).stem
        out_path = output_dir / f"{base_name}_edge.mp3"
        tts_tasks.append({"text": text, "out_path": out_path, "name": uploaded['name']})
        generated_files.append(out_path)
        progress_bar.progress(idx / len(uploaded_files))

    # Batch TTS conversion
    if tts_tasks:
        status_placeholder.info("🎙️ Converting all files to MP3 in parallel…")
        try:
            asyncio.run(batch_texts_to_mp3(tts_tasks, voice=voice_id))
            for task in tts_tasks:
                st.success(f"✅ **{task['name']}** → `{Path(task['out_path']).name}`")
        except Exception as exc:
            st.error(f"❌ Batch TTS conversion failed: {exc}")

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