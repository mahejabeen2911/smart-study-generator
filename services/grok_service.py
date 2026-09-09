"""
Groq Service
Conversational AI assistant powered by the Groq API.
Used for the AI Study Assistant, concept explanations, and follow-up questions.
"""

import os
import logging

logger = logging.getLogger(__name__)

# System prompt for the study assistant persona
_SYSTEM_PROMPT = """You are StudyGenAI Assistant, a friendly and knowledgeable academic tutor.
Your role is to help students understand study material clearly and simply.

Guidelines:
- Always explain concepts in plain, easy-to-understand language.
- Use examples to clarify difficult ideas.
- Avoid unnecessary jargon; define technical terms when you use them.
- If a question is unclear, ask for clarification rather than guessing.
- Never invent facts. If you don't know something, say so honestly.
- Keep answers focused and practical for exam preparation.
- When asked for practice questions, generate accurate and relevant ones.
- Adapt your explanation style to the student's level (beginner / intermediate / advanced).
- If study material context is provided, prefer explaining based on that material.
"""


class GrokService:
    """Wraps the Groq SDK for chat completions used by the Study Assistant."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
        self._client = None

    # ── Public API ────────────────────────────────────────────────────────────

    def is_configured(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("your_")

    def chat(self, user_message: str, study_context: str = "") -> str:
        """
        Send a user message and return the assistant's reply.

        Parameters
        ----------
        user_message   : The student's question or message.
        study_context  : Optional context from uploaded study material.

        Returns
        -------
        Assistant reply as a plain string.
        """
        if not self.is_configured():
            return (
                "The AI Study Assistant is not configured yet. "
                "Please add your GROQ_API_KEY to the .env file."
            )

        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

        if study_context:
            messages.append({
                "role": "system",
                "content": f"Uploaded study material context:\n{study_context}"
            })

        messages.append({"role": "user", "content": user_message})

        try:
            client = self._get_client()
            completion = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2048,
                temperature=0.7,
            )
            return completion.choices[0].message.content.strip()

        except Exception as exc:
            logger.error("Groq API error: %s", exc)
            error_msg = str(exc).lower()
            if "rate" in error_msg or "429" in error_msg:
                return "The AI assistant is busy right now (rate limit). Please wait a moment and try again."
            if "auth" in error_msg or "401" in error_msg or "403" in error_msg:
                return "Authentication failed. Please check your GROQ_API_KEY in the .env file."
            if "timeout" in error_msg or "connect" in error_msg:
                return "Connection to the AI assistant timed out. Please check your internet connection and try again."
            return "The AI assistant encountered an error. Please try again in a moment."

    # ── Private ───────────────────────────────────────────────────────────────

    def _get_client(self):
        """Lazy-initialise the Groq client (avoids import errors when key is missing)."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "The 'groq' package is required. Run: pip install groq"
                )
        return self._client
