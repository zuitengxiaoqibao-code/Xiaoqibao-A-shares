import asyncio
import hashlib
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import edge_tts

from qibao_api.speech.models import SpeechSettings


MAX_SPEECH_TEXT_LENGTH = 500
_CACHE_VERSION = "edge-tts-v1"
_WHITESPACE = re.compile(r"\s+")


class Communicator(Protocol):
    async def save(self, path: str) -> None: ...


CommunicatorFactory = Callable[[str, str, str], Communicator]


def _edge_communicator(text: str, voice: str, rate: str) -> Communicator:
    return edge_tts.Communicate(text=text, voice=voice, rate=rate)


class EdgeTTSService:
    def __init__(
        self,
        cache_dir: Path,
        *,
        communicator_factory: CommunicatorFactory = _edge_communicator,
    ) -> None:
        self.cache_dir = cache_dir
        self._communicator_factory = communicator_factory
        self._locks: dict[str, asyncio.Lock] = {}

    async def synthesize(self, text: str, settings: SpeechSettings) -> Path:
        normalized = _WHITESPACE.sub(" ", text).strip()
        if not normalized or len(normalized) > MAX_SPEECH_TEXT_LENGTH:
            raise ValueError("text must contain between 1 and 500 characters")
        key = hashlib.sha256(
            f"{_CACHE_VERSION}\0{settings.voice}\0{settings.rate}\0{normalized}".encode(
                "utf-8"
            )
        ).hexdigest()
        target = self.cache_dir / f"{key}.mp3"
        if target.is_file() and target.stat().st_size > 0:
            return target

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            if target.is_file() and target.stat().st_size > 0:
                return target
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            temporary = self.cache_dir / f".{key}.{os.getpid()}.tmp.mp3"
            try:
                communicator = self._communicator_factory(
                    normalized, settings.voice, settings.edge_rate
                )
                await communicator.save(str(temporary))
                if not temporary.is_file() or temporary.stat().st_size == 0:
                    raise RuntimeError("Edge TTS returned empty audio")
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
                self._locks.pop(key, None)
        return target
