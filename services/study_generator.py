"""
Study Generator Service
Fallback AI study content generator using the Grok/Groq API.
Used when IBM credentials are not configured.
"""

import os
import json
import logging
import re

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are StudyGenAI, an intelligent academic study assistant.
Analyze the provided study material and return a single valid JSON object.

RULES:
- Base every answer ONLY on the provided study material.
- Never invent definitions, formulas, or facts not present in the material.
- Do not claim a topic is "frequently asked in exams" unless the material says so.
- Use clear, student-friendly language.
- Return ONLY the raw JSON — no markdown, no preamble, no explanation.

Return this exact JSON structure:
{
  "summary": "<2-4 sentence overview>",
  "key_concepts": [
    {"title": "<name>", "description": "<explanation>"}
  ],
  "important_definitions": [
    {"term": "<term>", "definition": "<definition>"}
  ],
  "formulas": [
    {"name": "<name>", "formula": "<formula>", "description": "<usage>"}
  ],
  "key_takeaways": ["<point>"],
  "important_topics": [
    {
      "topic": "<name>",
      "priority": "High|Medium|Low",
      "reason": "<reason based on material>",
      "estimated_minutes": <integer>
    }
  ],
  "flashcards": [
    {"question": "<q>", "answer": "<a>", "topic": "<topic>"}
  ],
  "quiz": [
    {
      "question": "<q>",
      "options": ["<A>", "<B>", "<C>", "<D>"],
      "answer": "<correct option text>",
      "explanation": "<brief>",
      "topic": "<topic>"
    }
  ],
  "study_recommendations": ["<tip>"]
}

Generate 10-15 flashcards and 8-10 quiz questions appropriate to material length.
"""


class StudyGenerator:
    """Generates study resources using Groq as the primary inference engine."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
        self._client = None

    # ── Public ────────────────────────────────────────────────────────────────

    def generate(self, text_content: str, student_info: dict) -> dict:
        """
        Generate study resources from text_content.
        Falls back to a demo response if no valid API key is configured.
        """
        if not self.api_key or self.api_key.startswith("your_"):
            logger.warning("No valid GROQ_API_KEY — returning demo study content.")
            return self._demo_response(text_content)

        prompt = self._build_prompt(text_content, student_info)
        raw = self._call_groq(prompt)
        return self._parse_response(raw)

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_prompt(self, text_content: str, student_info: dict) -> str:
        prep = student_info.get("prep_level", "Intermediate")
        hours = student_info.get("study_hours", "2")
        exam = student_info.get("exam_date", "not specified")

        return (
            f"Student Profile:\n"
            f"- Preparation level: {prep}\n"
            f"- Study hours available per day: {hours}\n"
            f"- Exam date: {exam}\n\n"
            f"Study Material:\n{text_content}\n\n"
            f"JSON Response:"
        )

    def _call_groq(self, prompt: str) -> str:
        try:
            client = self._get_client()
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=3000,
                temperature=0.3,
            )
            return completion.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("Groq API error in StudyGenerator: %s", exc)
            raise

    def _get_client(self):
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise ImportError("Install groq: pip install groq")
        return self._client

    def _parse_response(self, raw: str) -> dict:
        """Parse JSON from AI response, with fallback handling."""
        text = raw.strip()

        # Strip markdown fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        # Direct parse
        try:
            return self._validate(json.loads(text))
        except json.JSONDecodeError:
            pass

        # Extract first JSON block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return self._validate(json.loads(match.group()))
            except json.JSONDecodeError:
                pass

        logger.warning("StudyGenerator: non-JSON AI response — using fallback display.")
        return {
            "summary": text[:800] if text else "Summary unavailable.",
            "key_concepts": [],
            "important_definitions": [],
            "formulas": [],
            "key_takeaways": [],
            "important_topics": [],
            "flashcards": [],
            "quiz": [],
            "study_recommendations": [
                "The AI returned an unexpected response. Please try again.",
                "If the problem persists, check your API key configuration.",
            ],
            "raw_response": text[:2000],
        }

    @staticmethod
    def _validate(data: dict) -> dict:
        """Ensure all required keys are present."""
        required = {
            "summary": "",
            "key_concepts": [],
            "important_definitions": [],
            "formulas": [],
            "key_takeaways": [],
            "important_topics": [],
            "flashcards": [],
            "quiz": [],
            "study_recommendations": [],
        }
        for key, default in required.items():
            if key not in data:
                data[key] = default
        return data

    @staticmethod
    def _demo_response(text_content: str) -> dict:
        """
        Returns a structured demo response when no API key is configured.
        This lets developers preview the UI without credentials.
        """
        preview = text_content[:200].replace('"', "'")
        return {
            "summary": (
                f"[DEMO MODE — Add GROQ_API_KEY to .env for real AI analysis.] "
                f"This is a preview of the study material: {preview}..."
            ),
            "key_concepts": [
                {"title": "Demo Concept 1", "description": "Configure your API keys to see real AI-generated concepts."},
                {"title": "Demo Concept 2", "description": "Upload your study material and add credentials to get started."},
            ],
            "important_definitions": [
                {"term": "StudyGenAI", "definition": "An AI-powered study companion for students."},
            ],
            "formulas": [],
            "key_takeaways": [
                "Add GROQ_API_KEY to your .env file to enable AI analysis.",
                "For IBM features, also add IBM_API_KEY and IBM_PROJECT_ID.",
            ],
            "important_topics": [
                {
                    "topic": "Getting Started",
                    "priority": "High",
                    "reason": "Configure API keys to unlock full AI features.",
                    "estimated_minutes": 10,
                },
            ],
            "flashcards": [
                {
                    "question": "What is StudyGenAI?",
                    "answer": "An AI-powered study generator that turns notes into summaries, flashcards, quizzes, and study plans.",
                    "topic": "Overview",
                },
                {
                    "question": "Which AI services does StudyGenAI use?",
                    "answer": "IBM watsonx.ai, IBM Langflow/Orchestrate, and the Grok (Groq) API.",
                    "topic": "Architecture",
                },
            ],
            "quiz": [
                {
                    "question": "What does StudyGenAI help students do?",
                    "options": [
                        "Watch videos online",
                        "Turn notes into study resources using AI",
                        "Schedule classes automatically",
                        "Download textbooks",
                    ],
                    "answer": "Turn notes into study resources using AI",
                    "explanation": "StudyGenAI converts study material into summaries, flashcards, quizzes, and study plans.",
                    "topic": "Overview",
                },
            ],
            "study_recommendations": [
                "Add your GROQ_API_KEY to the .env file to unlock real AI-powered study generation.",
                "Optionally add IBM_API_KEY and IBM_PROJECT_ID for IBM watsonx.ai integration.",
            ],
            "demo_mode": True,
        }
