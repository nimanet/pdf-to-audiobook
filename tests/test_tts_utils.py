"""
Unit tests for TTS utilities.
"""

import os
import asyncio
import pytest
from pathlib import Path
from utils.tts_utils import batch_texts_to_mp3

def test_batch_texts_to_mp3_empty():
    """Should return empty list for empty tasks."""
    results = asyncio.run(batch_texts_to_mp3([], voice="en-GB-RyanNeural"))
    assert results == []

def test_batch_texts_to_mp3_success(tmp_path):
    """Should create an MP3 file for a simple text."""
    out_path = tmp_path / "test.mp3"
    tasks = [{
        "text": "Hello, this is a test.",
        "out_path": out_path,
        "name": "test.txt"
    }]
    results = asyncio.run(batch_texts_to_mp3(tasks, voice="en-GB-RyanNeural"))
    assert results[0]["success"] is True
    assert out_path.exists()
    assert out_path.stat().st_size > 0