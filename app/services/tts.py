"""Text-to-speech via Microsoft edge-tts.

Generates MP3 audio with per-session filenames (UUID-based) under the
configured cache directory so concurrent users do not collide.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import edge_tts

from app.config import get_settings
from app.exceptions import TTSError
from app.logging_setup import get_logger
from app.utils.text import sanitise_for_tts

logger = get_logger(__name__)


_VOICE_MAP = {
    "Bangla": "bn-BD-NabanitaNeural",
    "English": "en-US-EmmaNeural",
}


class TextToSpeechService:
    """Generate spoken audio for assistant responses."""

    def __init__(self) -> None:
        settings = get_settings()
        self._cache_dir = settings.paths.cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def synthesise(
        self,
        text: str,
        *,
        language: str = "Bangla",
        mood: str = "Happy",
        session_id: str | None = None,
    ) -> Path | None:
        """Render ``text`` to MP3 and return its path.

        Returns ``None`` if the sanitised text is empty (silently skipped).
        Raises :class:`TTSError` for actual synthesis failures.
        """

        clean = sanitise_for_tts(text)
        if not clean:
            logger.debug("tts.skipped_empty")
            return None

        voice = _VOICE_MAP.get(language, _VOICE_MAP["English"])
        pitch = "+5Hz" if mood == "Happy" else "-5Hz"
        rate = "+15%" if language == "English" else "+8%"

        filename = f"tts_{session_id or uuid.uuid4().hex}.mp3"
        out_path = self._cache_dir / filename

        try:
            asyncio.run(self._synthesise_async(clean, voice, rate, pitch, out_path))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self._synthesise_async(clean, voice, rate, pitch, out_path))
            finally:
                loop.close()
        except Exception as exc:
            logger.exception("tts.failed", voice=voice, language=language)
            raise TTSError(f"TTS synthesis failed: {exc}", cause=exc) from exc

        logger.debug(
            "tts.synthesised",
            path=str(out_path),
            chars=len(clean),
            voice=voice,
            mood=mood,
        )
        return out_path

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    @staticmethod
    async def _synthesise_async(
        text: str, voice: str, rate: str, pitch: str, out_path: Path
    ) -> None:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await communicate.save(str(out_path))


__all__ = ["TextToSpeechService"]
