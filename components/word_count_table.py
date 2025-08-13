"""
Streamlit component for displaying PDF word counts and estimated conversion times.
"""

import streamlit as st

def show_word_count_table(file_data):
    """
    Displays a table of file names, word counts, and estimated conversion times.
    Also shows total word count and total estimated time.
    """
    if not file_data:
        return
    st.markdown('<div class="section-header">📊 PDF Word Counts</div>', unsafe_allow_html=True)
    st.table([
        {"File": f["name"], "Words": f["word_count"], "Est. Time (s)": f["est_time"]}
        for f in file_data
    ])
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