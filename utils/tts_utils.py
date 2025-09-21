"""
TTS conversion utilities for pdf-to-audiobook.
"""

import asyncio
from pathlib import Path
from typing import List
from edge_tts import Communicate

CONCURRENCY_LIMIT = 4  # Adjust as needed

async def _async_tts(text: str, out_path: Path, voice: str = "en-GB-RyanNeural", rate: str = "+0%"):
    """
    Asynchronously converts text to MP3 using Edge TTS and saves to out_path.
    """
    try:
        communicate = Communicate(text=text, voice=voice, rate=rate)
        await communicate.save(str(out_path))
    except Exception as exc:
        raise RuntimeError(f"TTS conversion failed: {exc}")

async def _async_tts_limited(text, out_path, voice, rate, sem):
    async with sem:
        await _async_tts(text, out_path, voice, rate)

async def batch_texts_to_mp3(tasks: List[dict], voice: str, rate: str = "+0%"):
    """
    Runs TTS conversion for a batch of tasks in parallel, with concurrency limit.
    Each task is a dict with keys: text, out_path, name.
    Returns a list of result dicts.
    """
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    coros = [
        _async_tts_limited(task["text"], task["out_path"], voice, rate, sem)
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