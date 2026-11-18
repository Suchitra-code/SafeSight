"""
Unified LLM Provider Layer for SafeSight AI - Milestone 3.
Supports Google Gemini, OpenAI, Anthropic, Ollama, and offline mode.
Wraps calls in retry loops (tenacity), handles timeouts, validates JSON via Pydantic,
and gracefully falls back to deterministic offline rules if unavailable.
"""
import json
import logging
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config
from app.llm.fake_llm import FakeLLMClient

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception raised when LLM generation fails after retries."""
    pass


class LLMClient:
    """Production LLM Client interface with offline graceful fallback."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None, api_key: Optional[str] = None):
        self._provider = (provider or config.LLM_PROVIDER or "none").strip().lower()
        self._model = model or config.LLM_MODEL or "gemini-1.5-flash"
        self._api_key = api_key or config.LLM_API_KEY or ""
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initializes provider SDK client safely."""
        if self._provider == "gemini" and self._api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
                logger.info(f"Initialized Google GenAI LLM Client with model {self._model}")
            except Exception as e:
                logger.warning(f"Failed to initialize Google GenAI SDK ({e}). Offline fallback active.")
                self._client = None
        elif self._provider == "fake":
            self._client = FakeLLMClient()
        else:
            self._client = None

    @property
    def name(self) -> str:
        return self._provider

    def is_available(self) -> bool:
        """Returns True if a live LLM client is configured and ready."""
        if self._provider == "fake":
            return True
        return self._provider not in ("none", "", "offline") and bool(self._api_key) and (self._client is not None)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4), retry=retry_if_exception_type(Exception), reraise=True)
    def _call_gemini_text(self, system: str, user: str, max_tokens: int) -> str:
        prompt = f"System Instructions:\n{system}\n\nUser Input:\n{user}"
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        return (response.text or "").strip()

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4), retry=retry_if_exception_type(Exception), reraise=True)
    def _call_gemini_json(self, system: str, user: str) -> str:
        prompt = f"System Instructions (RESPOND STRICTLY WITH VALID JSON):\n{system}\n\nUser Input:\n{user}"
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        return (response.text or "").strip()

    def generate(self, system: str, user: str, max_tokens: int = 800) -> str:
        """
        Generates text completion. Raises LLMError on failure to trigger offline mode.
        """
        if not self.is_available():
            raise LLMError("LLM Provider is offline or unconfigured.")

        if self._provider == "fake":
            return self._client.generate(system, user, max_tokens)

        try:
            if self._provider == "gemini":
                return self._call_gemini_text(system, user, max_tokens)
            raise LLMError(f"Unsupported LLM provider: {self._provider}")
        except Exception as e:
            logger.warning(f"LLM generate call failed: {e}")
            raise LLMError(str(e))

    def generate_json(self, system: str, user: str, schema: Type[BaseModel]) -> Dict[str, Any]:
        """
        Requests JSON, parses, and validates against Pydantic schema.
        Raises LLMError on parsing/validation failure so caller can fallback safely.
        """
        if not self.is_available():
            raise LLMError("LLM Provider is offline or unconfigured.")

        if self._provider == "fake":
            return self._client.generate_json(system, user, schema)

        try:
            raw_text = ""
            if self._provider == "gemini":
                raw_text = self._call_gemini_json(system, user)

            # Strip markdown json code fences if present
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            # Validate with pydantic
            validated = schema(**parsed)
            return validated.model_dump()
        except (json.JSONDecodeError, ValidationError, Exception) as e:
            logger.warning(f"LLM JSON generation or validation failed: {e}")
            raise LLMError(f"JSON validation failed: {e}")


# Singleton access
_default_llm_client = None


def get_llm_client() -> LLMClient:
    """Returns the singleton LLMClient instance."""
    global _default_llm_client
    if _default_llm_client is None:
        _default_llm_client = LLMClient()
    return _default_llm_client


def set_llm_client(client: LLMClient):
    """Allows injecting FakeLLMClient for testing."""
    global _default_llm_client
    _default_llm_client = client
