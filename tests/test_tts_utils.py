"""
Unit tests for TTS utilities.
"""

import pytest
from utils.tts_utils import batch_texts_to_mp3

@pytest.mark.asyncio
async def test_batch_texts_to_mp3_empty():
    results = await batch_texts_to_mp3([], voice="en-GB-RyanNeural")
    assert results == []