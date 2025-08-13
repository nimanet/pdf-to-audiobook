import asyncio
import tempfile
import io
import zipfile
from pathlib import Path
from typing import List

import streamlit as st
import fitz                     # PyMuPDF (fitz) – PDF parser
from edge_tts import Communicate
import concurrent.futures

CONCURRENCY_LIMIT = 4  # Adjust this number based on your CPU/memory


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


async def _async_tts_limited(text, out_path, voice, sem):
    async with sem:
        await _async_tts(text, out_path, voice)


async def batch_texts_to_mp3(tasks: List[dict], voice: str):
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    coros = [
        _async_tts_limited(task["text"], task["out_path"], voice, sem)
        for task in tasks
    ]
    results = []
    for idx, coro in enumerate(asyncio.as_completed(coros), start=1):
        try:
            await coro
            results.append({"name": tasks[idx-1]["name"], "success": True, "out_path": tasks[idx-1]["out_path"]})
        except Exception as exc:
            results.append({"name": tasks[idx-1]["name"], "success": False, "error": str(exc)})
    return results


async def extract_text_limited(uploaded, sem):
    async with sem:
        return extract_text_from_pdf_bytes(uploaded.read(), uploaded.name)

async def extract_all_texts(uploaded_files):
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = [
        extract_text_limited(uploaded, sem)
        for uploaded in uploaded_files
    ]
    return await asyncio.gather(*tasks)


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
st.set_page_config(page_title="PDF → MP3 (offline Edge‑TTS)", layout="centered")
st.markdown(
    """
    <style>
    .big-title {font-size:2.2rem;font-weight:700;margin-bottom:0.5em;}
    .section-header {font-size:1.3rem;font-weight:600;margin-top:2em;margin-bottom:0.5em;}
    .result-card {background:#f6f6fa;padding:1em 1.5em;border-radius:0.7em;margin-bottom:1em;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<div class="big-title">📚 PDF → MP3 Converter</div>', unsafe_allow_html=True)
st.markdown(
    """
    Convert your PDF documents to MP3 audiobooks using the **offline Edge TTS engine**.<br>
    <span style="color:#888">No external cloud service required. All processing is local.</span>
    """,
    unsafe_allow_html=True,
)

st.divider()
st.markdown('<div class="section-header">1️⃣ Upload PDF Files</div>', unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    "📂 Drag & drop PDF files here (or click to browse)",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="visible",
)

if uploaded_files:
    st.markdown('<div class="section-header">📊 PDF Word Counts</div>', unsafe_allow_html=True)
    file_data = []
    for uploaded in uploaded_files:
        pdf_bytes = uploaded.read()
        text = extract_text_from_pdf_bytes(pdf_bytes, uploaded.name)
        word_count = len(text.split())
        # Estimate: 2 seconds per 100 words, minimum 1 second
        est_time = max(1, int(word_count / 100 * 2))
        file_data.append({
            "uploaded": uploaded,
            "name": uploaded.name,
            "bytes": pdf_bytes,
            "text": text,
            "word_count": word_count,
            "est_time": est_time,
        })
    st.table([
        {"File": f["name"], "Words": f["word_count"], "Est. Time (s)": f["est_time"]}
        for f in file_data
    ])
    # Add total word count and total estimated time
    total_words = sum(f["word_count"] for f in file_data)
    total_est_time = sum(f["est_time"] for f in file_data)
    st.markdown(
        f"""
        <div style="font-size:1.1rem; margin-top:0.5em;">
            <b>Total words:</b> {total_words:,} &nbsp;|&nbsp; 
            <b>Total estimated time:</b> {total_est_time:,} seconds
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    file_data = []

st.divider()
st.markdown('<div class="section-header">2️⃣ Select Voice</div>', unsafe_allow_html=True)
VOICE_OPTIONS = {
    "English (UK) – Ryan (Male, Neural)": "en-GB-RyanNeural",
    "English (UK) – Sonia (Female, Neural)": "en-GB-SoniaNeural",
    "English (US) – Jenny (Female, Neural)": "en-US-JennyNeural",
    "English (US) – Guy (Male, Neural)": "en-US-GuyNeural",
    "English (Australia) – Natasha (Female, Neural)": "en-AU-NatashaNeural",
    "English (Australia) – William (Male, Neural)": "en-AU-WilliamNeural",
}
voice_name = st.selectbox(
    "🔊 Choose an English voice",
    list(VOICE_OPTIONS.keys()),
    index=0,
    label_visibility="visible",
    key="voice_picker",
)
voice_id = VOICE_OPTIONS[voice_name]

st.divider()
st.markdown('<div class="section-header">3️⃣ Conversion</div>', unsafe_allow_html=True)

convert_clicked = st.button("🚀 Convert PDFs to MP3", type="primary")

if not uploaded_files:
    st.info("👈 Select at least one PDF to start.")
    st.stop()

if convert_clicked:
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_dir = Path(tmp_dir)
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        generated_files: List[Path] = []

        # Use cached text from file_data
        tts_tasks = []
        extraction_failures = []
        warning_msgs = []
        for f in file_data:
            if not f["text"]:
                warning_msgs.append(f"⚠️ No readable text found in **{f['name']}** – skipping.")
                extraction_failures.append(f["name"])
                continue
            base_name = Path(f["name"]).stem
            out_path = output_dir / f"{base_name}_edge.mp3"
            tts_tasks.append({"text": f["text"], "out_path": out_path, "name": f["name"]})

        # Show all warnings at once
        if warning_msgs:
            st.warning("\n".join(warning_msgs))
        if extraction_failures:
            st.info(f"ℹ️ The following files could not be extracted and were skipped: {', '.join(extraction_failures)}")

        # Batch TTS conversion
        generated_files: List[Path] = []  # Reset to only include successful conversions
        if tts_tasks:
            status_placeholder.info("🎙️ Converting all files to MP3 in parallel…")
            try:
                results = asyncio.run(batch_texts_to_mp3(tts_tasks, voice=voice_id))
                success_msgs = []
                error_msgs = []
                for res in results:
                    if res.get("success"):
                        success_msgs.append(f"✅ **{res['name']}** → `{Path(res['out_path']).name}`")
                        generated_files.append(res['out_path'])  # Only add successful files
                    else:
                        error_msgs.append(f"❌ **{res['name']}** failed: {res['error']}")
                if success_msgs:
                    st.success("\n".join(success_msgs))
                if error_msgs:
                    st.error("\n".join(error_msgs))
                if not success_msgs:
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
            st.markdown('<div class="section-header">4️⃣ Download Results</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="result-card">🎉 <b>{len(generated_files)}</b> MP3 file(s) ready for download!</div>',
                unsafe_allow_html=True,
            )
            # Individual download buttons
            for mp3_path in generated_files:
                with open(mp3_path, "rb") as f:
                    st.download_button(
                        label=f"Download `{mp3_path.name}`",
                        data=f,
                        file_name=mp3_path.name,
                        mime="audio/mpeg",
                    )
            # Download all as ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for mp3_path in generated_files:
                    zipf.write(mp3_path, arcname=mp3_path.name)
            zip_buffer.seek(0)
            st.download_button(
                label="⬇️ Download ALL as ZIP",
                data=zip_buffer,
                file_name="converted_mp3s.zip",
                mime="application/zip",
            )
        else:
            st.info("No MP3 files were generated.")