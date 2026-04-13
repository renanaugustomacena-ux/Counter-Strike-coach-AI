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

# Default Ollama configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")  # Gemma 4 E2B (2.3B effective, 128K ctx)


class LLMService:
    """Service for generating natural language coaching lessons using Ollama."""

    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = OLLAMA_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._available = None  # Cached availability status
        self._available_checked_at = 0.0  # Timestamp of last check
        self._AVAILABILITY_TTL = 60.0  # Re-check every 60 seconds

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
                # Check if any model is available (we can use whatever is installed)
                self._available = len(models) > 0
                self._available_checked_at = time.monotonic()
                if self._available and self.model not in model_names:
                    # Use first available model
                    self.model = model_names[0] if model_names else DEFAULT_MODEL
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
