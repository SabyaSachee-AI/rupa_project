"""Speech-to-text via Groq Whisper."""

from __future__ import annotations

from groq import Groq

from app.config import get_settings
from app.exceptions import LLMConfigurationError, STTError
from app.logging_setup import get_logger
from app.runtime_keys import get_groq_api_key

logger = get_logger(__name__)


class SpeechToTextService:
    """Wraps Groq's Whisper Large v3 endpoint."""

    def __init__(self) -> None:
        settings = get_settings()
        api_key = get_groq_api_key()
        if not api_key:
            raise LLMConfigurationError(
                "Groq API key is not configured. Add it in the sidebar under API keys."
            )
        self._client = Groq(api_key=api_key)
        self._model = settings.llm.stt_model

    def transcribe(self, audio_bytes: bytes, *, filename: str = "audio.wav") -> str:
        """Return the transcript for ``audio_bytes``.

        Raises:
            STTError: on provider failure or empty audio.
        """

        if not audio_bytes:
            raise STTError("Empty audio payload")

        try:
            response = self._client.audio.transcriptions.create(
                file=(filename, audio_bytes),
                model=self._model,
            )
            text = (response.text or "").strip()
            logger.debug("stt.transcribed", chars=len(text), bytes=len(audio_bytes))
            return text
        except Exception as exc:
            logger.exception("stt.failed")
            raise STTError(f"STT transcription failed: {exc}", cause=exc) from exc


__all__ = ["SpeechToTextService"]
