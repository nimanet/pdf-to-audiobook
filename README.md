# PDF to Audiobook

Convert PDF documents to MP3 audiobooks using Streamlit and Edge TTS.

## Features

- Upload multiple PDFs
- Choose from several English neural voices
- See word counts and estimated conversion times
- Batch convert to MP3 in parallel
- Download individual MP3s or all as a ZIP

## Usage

```sh
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

- `app.py`: Main Streamlit UI
- `utils/`: PDF and TTS helpers
- `components/`: Streamlit UI components
- `tests/`: Unit tests

## License

MIT