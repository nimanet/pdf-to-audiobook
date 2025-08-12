# ──────────────────────────────────────────────────────────────────────────────
#  Streamlit PDF → MP3 converter (offline Edge‑TTS)
#  -------------------------------------------------
#  Requirements (install once):
#      pip install streamlit PyPDF2 edge-tts
#
#  Run:
#      streamlit run app.py
# ──────────────────────────────────────────────────────────────────────────────
import os
import io
import asyncio
from pathlib import Path
from typing import List

import streamlit as st
import PyPDF2
from edge_tts import Communicate

# -------------------------------------------------
# Helper: extract text from a PDF (bytes -> str)
# -------------------------------------------------
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Return all extractable text from a PDF supplied as bytes."""
    text = ""
    try:
        with io.BytesIO(pdf_bytes) as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        st.error(f"❌ Could not read PDF: {e}")
    return text.strip()


# -------------------------------------------------
# Async wrapper for Edge‑TTS (offline)
# -------------------------------------------------
async def _async_tts(text: str, out_path: Path, voice: str = "en-GB-RyanNeural"):
    """
    Save `text` to `out_path` as an MP3 using Edge‑TTS.
    This runs completely offline on Windows 10+ (Edge engine).
    """
    try:
        communicate = Communicate(text=text, voice=voice)
        await communicate.save(str(out_path))
    except Exception as exc:
        raise RuntimeError(f"TTS conversion failed: {exc}")


def text_to_mp3(text: str, out_path: Path, voice: str = "en-GB-RyanNeural"):
    """
    Synchronous wrapper around the async Edge‑TTS call.
    Streamlit runs in a sync context, so we call asyncio.run().
    """
    asyncio.run(_async_tts(text, out_path, voice))


# -------------------------------------------------
# UI
# -------------------------------------------------
st.set_page_config(page_title="PDF → MP3 (offline Edge‑TTS)",
                   layout="centered")
st.title("📚 PDF → MP3 Converter")

st.markdown(
    """
    Upload **one or more** PDF files, pick a voice, and get back an MP3 for each.
    The conversion uses the **offline Edge TTS engine** – no external cloud service required.
    """
)

# ---- Voice selector -------------------------------------------------
# A small curated list – you can expand it later.
VOICE_OPTIONS = {
    "English (UK) – Ryan (Neural)": "en-GB-RyanNeural",
    "English (US) – Jenny (Neural)": "en-US-JennyNeural",
    "English (US) – Guy (Neural)":   "en-US-GuyNeural",
    "Spanish (Spain) – Lucia (Neural)": "es-ES-LuciaNeural",
    "German (Germany) – Jonas (Neural)": "de-DE-JonasNeural",
}
voice_name = st.selectbox("🔊 Choose a voice", list(VOICE_OPTIONS.keys()))
voice_id = VOICE_OPTIONS[voice_name]

# ---- File uploader -------------------------------------------------
uploaded_files = st.file_uploader(
    "📂 Drag & drop PDF files here (or click to browse)",
    type=["pdf"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("👈 Select at least one PDF to start.")
    st.stop()

# ---- Process each file -----------------------------------------------
progress_bar = st.progress(0)
status_placeholder = st.empty()

output_dir = Path("tmp_outputs")
output_dir.mkdir(exist_ok=True)

generated_files: List[Path] = []

for idx, uploaded in enumerate(uploaded_files, start=1):
    # 1️⃣  Show status
    status_placeholder.info(f"🔎 **{uploaded.name}** – extracting text…")
    # 2️⃣  Extract text
    pdf_bytes = uploaded.read()
    text = extract_text_from_pdf_bytes(pdf_bytes)

    if not text:
        st.warning(f"⚠️ No readable text found in **{uploaded.name}** – skipping.")
        continue

    # 3️⃣  Convert to MP3
    base_name = Path(uploaded.name).stem
    out_path = output_dir / f"{base_name}_edge.mp3"

    status_placeholder.info(f"🎙️ Converting **{uploaded.name}** to MP3…")
    try:
        text_to_mp3(text, out_path, voice=voice_id)
        generated_files.append(out_path)
        st.success(f"✅ **{uploaded.name}** → `{out_path.name}`")
    except Exception as exc:
        st.error(f"❌ Failed on **{uploaded.name}** – {exc}")

    # 4️⃣  Update progress bar
    progress_bar.progress(idx / len(uploaded_files))

status_placeholder.empty()
st.balloons()

# ---- Download section -------------------------------------------------
if generated_files:
    st.subheader("⬇️ Download your MP3 files")
    for mp3_path in generated_files:
        with open(mp3_path, "rb") as f:
            btn = st.download_button(
                label=f"Download `{mp3_path.name}`",
                data=f,
                file_name=mp3_path.name,
                mime="audio/mpeg",
            )
else:
    st.info("No MP3 files were generated.")