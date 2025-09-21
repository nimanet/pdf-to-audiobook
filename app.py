import asyncio
import tempfile
import io
import zipfile
from pathlib import Path
from typing import List, Dict, Any
import time

import streamlit as st

from utils.pdf_utils import extract_text_from_pdf_bytes
from utils.tts_utils import batch_texts_to_mp3
from components.word_count_table import show_word_count_table

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

# Deduplicate uploaded files by name
if uploaded_files:
    unique_files = []
    seen_names = set()
    for uploaded in uploaded_files:
        if uploaded.name not in seen_names:
            unique_files.append(uploaded)
            seen_names.add(uploaded.name)
        else:
            st.warning(f"���️ Duplicate file `{uploaded.name}` was ignored.")
    uploaded_files = unique_files

# Prepare file data and show word count table
if uploaded_files:
    file_data = []
    for uploaded in uploaded_files:
        # Read PDF bytes once and reuse
        pdf_bytes = uploaded.read()
        text = extract_text_from_pdf_bytes(pdf_bytes, uploaded.name)
        word_count = len(text.split())
        est_time = max(1, int(word_count / 100 * 2))
        file_data.append({
            "uploaded": uploaded,
            "name": uploaded.name,
            "bytes": pdf_bytes,
            "text": text,
            "word_count": word_count,
            "est_time": est_time,
        })
    show_word_count_table(file_data)
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

        tts_tasks = []
        extraction_failures = []
        warning_msgs = []
        
        # Process files with better error handling and progress tracking
        for i, f in enumerate(file_data):
            if not f["text"]:
                warning_msgs.append(f"���️ No readable text found in **{f['name']}** – skipping.")
                extraction_failures.append(f["name"])
                continue
            
            base_name = Path(f["name"]).stem
            out_path = output_dir / f"{base_name}_edge.mp3"
            tts_tasks.append({"text": f["text"], "out_path": out_path, "name": f["name"]})
            
            # Update progress bar
            progress_bar.progress((i + 1) / len(file_data))

        if warning_msgs:
            st.warning("\n".join(warning_msgs))
        if extraction_failures:
            st.info(f"ℹ️ The following files could not be extracted and were skipped: {', '.join(extraction_failures)}")

        generated_files: List[Path] = []
        if tts_tasks:
            status_placeholder.info("🎙️ Converting all files to MP3 in parallel…")
            start_time = time.perf_counter()
            
            try:
                # Process tasks in batches to avoid overwhelming the system
                batch_size = min(5, len(tts_tasks))  # Limit concurrent tasks
                results = []
                
                for i in range(0, len(tts_tasks), batch_size):
                    batch = tts_tasks[i:i + batch_size]
                    batch_results = asyncio.run(batch_texts_to_mp3(batch, voice=voice_id))
                    results.extend(batch_results)
                    
                    # Update progress bar for batch completion
                    progress_bar.progress(min((i + batch_size) / len(tts_tasks), 1.0))
                
                elapsed = time.perf_counter() - start_time
                
                success_msgs = []
                error_msgs = []
                for res in results:
                    if res.get("success"):
                        success_msgs.append(f"��� **{res['name']}** → `{Path(res['out_path']).name}`")
                        generated_files.append(res['out_path'])
                    else:
                        error_msgs.append(f"❌ **{res['name']}** failed: {res['error']}")
                        
                if success_msgs:
                    st.success("\n".join(success_msgs))
                if error_msgs:
                    st.error("\n".join(error_msgs))
                if not success_msgs:
                    st.warning("���️ No files were converted successfully.")
                st.info(f"⏱️ Conversion completed in {elapsed:.1f} seconds.")
                
            except Exception as exc:
                st.exception(exc)
        else:
            st.warning("���️ No valid PDF files to convert.")

        status_placeholder.empty()
        st.balloons()

        if generated_files:
            st.markdown('<div class="section-header">4️⃣ Download Results</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="result-card">🎉 <b>{len(generated_files)}</b> MP3 file(s) ready for download!</div>',
                unsafe_allow_html=True,
            )
            for idx, mp3_path in enumerate(generated_files):
                with open(mp3_path, "rb") as f:
                    st.download_button(
                        label=f"Download `{mp3_path.name}`",
                        data=f,
                        file_name=mp3_path.name,
                        mime="audio/mpeg",
                        key=f"download_{mp3_path.name}_{idx}",  # <-- ensures uniqueness
                    )
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