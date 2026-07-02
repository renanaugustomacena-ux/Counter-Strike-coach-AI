"""
LLM Service for Natural Language Lesson Generation

Uses Ollama for local LLM inference to transform RAP model insights
into readable, educational coaching lessons.

Integration Points:
- lesson_generator.py - Calls this service to generate lessons
- coaching_service.py - Could integrate for contextual tips
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

import requests

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.llm_service")

# Default Ollama configuration. Resolution priority:
#   1. OLLAMA_MODEL environment variable (deployment override)
#   2. user_settings.json LLM_COACH_MODEL (UI selector in CoachScreen)
#   3. "gemma4:e2b" hard default (Gemma 4 E2B, 2.3B effective, 128K ctx)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


def _resolve_default_model() -> str:
    env_choice = os.getenv("OLLAMA_MODEL")
    if env_choice:
        return env_choice
    try:
        from Programma_CS2_RENAN.core.config import get_setting

        setting_choice = get_setting("LLM_COACH_MODEL", "")
        if setting_choice:
            return str(setting_choice)
    except Exception:  # noqa: BLE001 — bootstrap path may run pre-config
        pass
    return "gemma4:e2b"


DEFAULT_MODEL = _resolve_default_model()


class LLMService:
    """Service for generating natural language coaching lessons using Ollama."""

    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = OLLAMA_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._available = None  # Cached availability status
        self._available_checked_at = 0.0  # Timestamp of last check
        self._AVAILABILITY_TTL = 60.0  # Re-check every 60 seconds

    def list_models(self) -> List[Dict[str, Any]]:
        """Return Ollama's installed-model inventory via /api/tags.

        Returns a list of dicts with keys: name (str), size (int bytes),
        modified_at (str ISO timestamp). Empty list if Ollama is
        unreachable. Used by the LLM Coach tab in CoachScreen to populate
        a model selector — letting the user pick between any locally
        installed Gemma / Llama / Mistral / etc. without hardcoding.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if response.status_code != 200:
                return []
            models = response.json().get("models", []) or []
            return [
                {
                    "name": m.get("name", ""),
                    "size": int(m.get("size") or 0),
                    "modified_at": m.get("modified_at", ""),
                }
                for m in models
                if m.get("name")
            ]
        except (requests.ConnectionError, requests.Timeout, ValueError):
            return []

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        if (
            self._available is not None
            and (time.monotonic() - self._available_checked_at) < self._AVAILABILITY_TTL
        ):
            return self._available

        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                self._available = len(models) > 0
                self._available_checked_at = time.monotonic()
                if self._available and self.model not in model_names:
                    requested = self.model
                    # Prefer same model family (gemma4 -> any gemma4 variant -> any gemma -> first available).
                    family_prefix = requested.split(":", 1)[0]
                    same_family = [n for n in model_names if n.split(":", 1)[0] == family_prefix]
                    gemma_any = [n for n in model_names if n.startswith("gemma")]
                    chosen = (same_family or gemma_any or model_names)[0]
                    self.model = chosen
                    logger.warning(
                        "Requested LLM '%s' not installed in Ollama; falling back to '%s'. "
                        "Install with `ollama pull %s` to restore the configured chatbot model.",
                        requested,
                        chosen,
                        requested,
                    )
                return self._available
        except (requests.ConnectionError, requests.Timeout):
            self._available = False
            self._available_checked_at = time.monotonic()

        return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using Ollama.

        Args:
            prompt: The user prompt to respond to
            system_prompt: Optional system instructions

        Returns:
            Generated text or error message
        """
        if not self.is_available():
            return "[LLM Unavailable] Please start Ollama to enable natural language lessons."

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": -1,
                "num_ctx": 32768,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=600)

            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                return f"[LLM Error] Status {response.status_code}"

        except requests.Timeout as e:
            return f"[LLM Timeout] Generation took too long: {str(e)}"
        except requests.ConnectionError as e:
            self._available = False
            return f"[LLM Connection Error] {str(e)}"
        except Exception as e:
            return f"[LLM Error] {str(e)}"

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Multi-turn chat using Ollama's /api/chat endpoint.

        Args:
            messages: Conversation history as list of
                      {"role": "user"|"assistant", "content": "..."} dicts.
            system_prompt: Optional system instructions prepended to messages.

        Returns:
            Assistant response text, or "[LLM ...]" error marker on failure.
        """
        if not self.is_available():
            return "[LLM Unavailable] Please start Ollama to enable coaching dialogue."

        chat_messages: List[Dict[str, str]] = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": chat_messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": -1,
                "num_ctx": 32768,
            },
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=600,
            )

            if response.status_code == 200:
                msg = response.json().get("message", {})
                return msg.get("content", "")
            else:
                return f"[LLM Error] Status {response.status_code}"

        except requests.Timeout as e:
            # Timeout does NOT mean Ollama is down — just a slow generation.
            # Do NOT poison the availability cache.
            return f"[LLM Timeout] Generation took too long: {str(e)}"
        except requests.ConnectionError as e:
            self._available = False
            return f"[LLM Connection Error] {str(e)}"
        except Exception as e:
            return f"[LLM Error] {str(e)}"

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        on_chunk=None,
        connect_timeout: float = 10.0,
        stall_timeout: float = 30.0,
    ) -> str:
        """TASKS#33/F2: streaming multi-turn chat via Ollama's /api/chat.

        Calls ``on_chunk(accumulated_text)`` after every received chunk —
        always the FULL accumulated message (DR-14: whole-message re-render,
        never fragments). Returns the final text.

        The requests read-timeout doubles as stall detection: no bytes for
        ``stall_timeout`` seconds raises ``requests.exceptions.Timeout`` —
        unlike chat(), errors RAISE here instead of returning "[LLM ...]"
        markers, because the caller must decide what to do with an already
        partially-rendered message.
        """
        chat_messages = list(messages)
        if system_prompt:
            chat_messages = [{"role": "system", "content": system_prompt}] + chat_messages

        payload = {
            "model": self.model,
            "messages": chat_messages,
            "stream": True,
        }
        accumulated = ""
        with requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=(connect_timeout, stall_timeout),
            stream=True,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                piece = (data.get("message") or {}).get("content", "")
                if piece:
                    accumulated += piece
                    if on_chunk is not None:
                        on_chunk(accumulated)
                if data.get("done"):
                    break
        return accumulated

    def generate_lesson(self, insights: Dict[str, Any]) -> str:
        """Transform RAP insights into a natural language lesson.

        Args:
            insights: Dictionary containing RAP model analysis results

        Returns:
            Natural language lesson text
        """
        system_prompt = """You are an expert CS2 coach analyzing gameplay.
Your job is to explain tactical insights in simple, actionable terms.
Be encouraging but honest. Focus on ONE key improvement at a time.
Keep responses concise (3-4 paragraphs max)."""

        prompt = f"""Analyze this gameplay data and provide a coaching lesson:

{json.dumps(insights, indent=2)}

Focus on:
1. What went well
2. One key area to improve
3. A specific pro tip to practice

Write naturally, like a coach talking to a player."""

        return self.generate(prompt, system_prompt)

    def explain_round_decision(self, round_data: Dict[str, Any]) -> str:
        """Explain a specific round decision.

        Args:
            round_data: Data about a specific round

        Returns:
            Explanation of what happened and what could be improved
        """
        system_prompt = """You are a CS2 coach explaining a round.
Be specific about what happened and why.
Reference pro player examples when relevant."""

        prompt = f"""Explain this CS2 round to help the player improve:

Round Data: {json.dumps(round_data, indent=2)}

Keep it brief but insightful."""

        return self.generate(prompt, system_prompt)

    def generate_pro_tip(self, context: Dict[str, Any]) -> str:
        """Generate a contextual pro tip based on current situation.

        Args:
            context: Current game context (map, position, economy, etc.)

        Returns:
            A relevant pro tip
        """
        system_prompt = """You are sharing a quick CS2 pro tip.
Keep it to 1-2 sentences. Be specific and actionable."""

        prompt = f"""Give a pro tip for this situation:
{json.dumps(context, indent=2)}"""

        return self.generate(prompt, system_prompt)


# Singleton instance for global access
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def check_ollama_status() -> Dict[str, Any]:
    """Check Ollama status and return diagnostic info."""
    service = get_llm_service()

    status = {"available": service.is_available(), "url": service.base_url, "model": service.model}

    if status["available"]:
        # Get list of available models
        try:
            response = requests.get(f"{service.base_url}/api/tags", timeout=3)
            if response.status_code == 200:
                models = response.json().get("models", [])
                status["available_models"] = [m.get("name") for m in models]
        except Exception as e:
            logger.debug("Could not fetch Ollama model list: %s", e)

    return status
