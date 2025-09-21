# PDF to Audiobook

Streamlit app for converting uploaded PDF files to MP3 audiobooks using the offline Edge TTS engine.
Main Features:

-   Allows users to upload multiple PDF files, deduplicates by filename, and extracts readable text.
-   Displays a word count table for each uploaded PDF and estimates conversion time.
-   Lets users select from several English neural voices for MP3 generation.
-   Converts PDFs to MP3 files in parallel batches, with progress tracking and error handling.
-   Provides individual and batch (ZIP) download options for generated MP3 files.
-   All processing is performed locally; no external cloud services are required.
    Key Components:
-   PDF text extraction via `extract_text_from_pdf_bytes`.
-   Text-to-speech conversion via `batch_texts_to_mp3`.
-   UI elements for file upload, voice selection, conversion progress, and download links.
-   Handles extraction failures, duplicate files, and conversion errors gracefully.
    Intended Usage:
    Run as a Streamlit app for local PDF-to-audiobook conversion, suitable for privacy-conscious users.

You can adjust the reading speed of the generated audiobooks using the slider in the conversion settings. The speed control allows you to:

-   **Slow down** readings with negative values (e.g., -50%)
-   **Maintain normal speed** at 0%
-   **Speed up** readings with positive values (up to +100%)

This feature gives you more flexibility in creating audiobooks that match your preferred listening pace.

## Features

-   Upload multiple PDFs
-   Choose from several English neural voices
-   See word counts and estimated conversion times
-   Batch convert to MP3 in parallel
-   Download individual MP3s or all as a ZIP
-   adjust the reading speed

## Usage

```sh
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

-   `app.py`: Main Streamlit UI
-   `utils/`: PDF and TTS helpers
-   `components/`: Streamlit UI components
-   `tests/`: Unit tests

## License

MIT
