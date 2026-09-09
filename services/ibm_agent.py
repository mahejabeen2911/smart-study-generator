"""
IBM Agent Service
Integrates IBM watsonx.ai and IBM Langflow / IBM Orchestrate.

Architecture
────────────
1. IBM Langflow/Orchestrate  – agentic workflow orchestration
2. IBM watsonx.ai            – language model inference

How to connect
──────────────
Set these environment variables in your .env file:

    IBM_API_KEY         – IAM API key from cloud.ibm.com
    IBM_PROJECT_ID      – watsonx.ai project ID
    IBM_SPACE_ID        – (optional) deployment space ID
    IBM_REGION          – cloud region, e.g. us-south  (default: us-south)
    IBM_WX_MODEL        – watsonx model ID (default: ibm/granite-13b-instruct-v2)
    IBM_LANGFLOW_URL    – your IBM Langflow / Orchestrate endpoint URL (optional)
    IBM_LANGFLOW_TOKEN  – bearer token for Langflow endpoint (optional)

If IBM_LANGFLOW_URL is set the agent will call the Langflow pipeline first.
Otherwise it calls the watsonx.ai REST API directly.
"""

import os
import json
import logging
import re
import requests

logger = logging.getLogger(__name__)

# ── System prompt sent to the IBM model ──────────────────────────────────────
_IBM_SYSTEM_PROMPT = """You are StudyGenAI, an intelligent academic study assistant.
Your task is to analyze the provided study material and generate a structured JSON response.

STRICT RULES:
1. Use ONLY information present in the provided study material.
2. Never invent facts, formulas, or definitions not found in the material.
3. Do not claim a topic is "frequently asked in exams" unless the material says so.
4. Use clear, student-friendly language.
5. Return ONLY valid JSON — no markdown fences, no extra commentary.

JSON SCHEMA (return exactly this structure):
{
  "summary": "<2-4 sentence overview of the entire material>",
  "key_concepts": [
    {"title": "<concept name>", "description": "<clear explanation>"}
  ],
  "important_definitions": [
    {"term": "<term>", "definition": "<definition>"}
  ],
  "formulas": [
    {"name": "<formula name>", "formula": "<formula string>", "description": "<usage>"}
  ],
  "key_takeaways": ["<exam-focused point>"],
  "important_topics": [
    {
      "topic": "<topic name>",
      "priority": "High|Medium|Low",
      "reason": "<why this topic is important based on the material>",
      "estimated_minutes": <integer>
    }
  ],
  "flashcards": [
    {"question": "<question>", "answer": "<answer>", "topic": "<topic>"}
  ],
  "quiz": [
    {
      "question": "<question>",
      "options": ["<A>", "<B>", "<C>", "<D>"],
      "answer": "<correct option text>",
      "explanation": "<brief explanation>",
      "topic": "<topic>"
    }
  ],
  "study_recommendations": ["<actionable study tip>"]
}

Generate 10-15 flashcards and 8-10 quiz questions appropriate for the material length.
"""


class IBMAgent:
    """Handles IBM watsonx.ai and optional IBM Langflow integration."""

    def __init__(self):
        self.api_key   = self._real(os.getenv("IBM_API_KEY", ""))
        self.project_id = self._real(os.getenv("IBM_PROJECT_ID", ""))
        self.space_id  = self._real(os.getenv("IBM_SPACE_ID", ""))
        self.region    = os.getenv("IBM_REGION", "us-south")
        self.model_id  = os.getenv("IBM_WX_MODEL", "ibm/granite-13b-instruct-v2")
        self.langflow_url   = self._real(os.getenv("IBM_LANGFLOW_URL", ""))
        self.langflow_token = self._real(os.getenv("IBM_LANGFLOW_TOKEN", ""))
        self._iam_token: str = ""

    # ── Public ────────────────────────────────────────────────────────────────

    @staticmethod
    def _real(value: str) -> str:
        """Return value only if it looks like a real credential, not a placeholder."""
        if not value or value.startswith("your_") or value.startswith("https://your-"):
            return ""
        return value

    def is_configured(self) -> bool:
        """Return True only when real IBM API key + project ID are present."""
        return bool(self.api_key and self.project_id)

    def run_study_workflow(self, text_content: str, student_info: dict) -> dict:
        """
        Run the full study generation workflow.

        Tries IBM Langflow/Orchestrate first (if URL is set),
        then falls back to direct watsonx.ai inference.
        """
        if self.langflow_url:
            try:
                result = self._call_langflow(text_content, student_info)
                if result:
                    result["ibm_used"] = True
                    result["ibm_mode"] = "langflow"
                    return result
            except Exception as exc:
                logger.warning("Langflow call failed, trying watsonx.ai directly: %s", exc)

        result = self._call_watsonx(text_content, student_info)
        result["ibm_used"] = True
        result["ibm_mode"] = "watsonx"
        return result

    # ── IBM Langflow / Orchestrate ────────────────────────────────────────────

    def _call_langflow(self, text_content: str, student_info: dict) -> dict:
        """
        POST to an IBM Langflow / Orchestrate pipeline endpoint.

        The endpoint should accept JSON:
        {
            "input_value": "<study text>",
            "tweaks": { "student_info": { ... } }
        }
        and return JSON containing the AI output in result["outputs"][0]["outputs"][0]["results"]["message"]["text"]
        (standard Langflow response format).
        """
        headers = {"Content-Type": "application/json"}
        if self.langflow_token:
            headers["Authorization"] = f"Bearer {self.langflow_token}"

        payload = {
            "input_value": text_content,
            "tweaks": {"student_info": student_info},
            "output_type": "chat",
            "input_type": "chat",
        }

        response = requests.post(
            self.langflow_url, json=payload, headers=headers, timeout=120
        )
        response.raise_for_status()
        data = response.json()

        # Extract text from standard Langflow response envelope
        try:
            raw_text = (
                data["outputs"][0]["outputs"][0]["results"]["message"]["text"]
            )
        except (KeyError, IndexError, TypeError):
            # Flat response — try "output" or "text" keys
            raw_text = data.get("output") or data.get("text") or json.dumps(data)

        return self._parse_ai_response(raw_text, student_info)

    # ── IBM watsonx.ai ────────────────────────────────────────────────────────

    def _call_watsonx(self, text_content: str, student_info: dict) -> dict:
        """Call IBM watsonx.ai text generation REST API directly."""
        token = self._get_iam_token()
        endpoint = (
            f"https://{self.region}.ml.cloud.ibm.com"
            f"/ml/v1/text/generation?version=2023-05-29"
        )

        prompt = self._build_prompt(text_content, student_info)

        payload = {
            "model_id": self.model_id,
            "input": prompt,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": 3000,
                "temperature": 0.3,
                "repetition_penalty": 1.1,
            },
        }

        # Use project_id or space_id
        if self.project_id:
            payload["project_id"] = self.project_id
        elif self.space_id:
            payload["space_id"] = self.space_id

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        response = requests.post(endpoint, json=payload, headers=headers, timeout=120)

        if response.status_code == 401:
            # Token may have expired — refresh once
            self._iam_token = ""
            token = self._get_iam_token()
            headers["Authorization"] = f"Bearer {token}"
            response = requests.post(endpoint, json=payload, headers=headers, timeout=120)

        response.raise_for_status()
        result_data = response.json()

        raw_text = result_data["results"][0]["generated_text"]
        return self._parse_ai_response(raw_text, student_info)

    # ── IAM Token ─────────────────────────────────────────────────────────────

    def _get_iam_token(self) -> str:
        """Exchange IBM API key for an IAM bearer token (cached per instance)."""
        if self._iam_token:
            return self._iam_token

        response = requests.post(
            "https://iam.cloud.ibm.com/identity/token",
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": self.api_key,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        self._iam_token = response.json()["access_token"]
        return self._iam_token

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_prompt(self, text_content: str, student_info: dict) -> str:
        prep = student_info.get("prep_level", "Intermediate")
        hours = student_info.get("study_hours", "2")
        exam = student_info.get("exam_date", "not specified")

        return (
            f"{_IBM_SYSTEM_PROMPT}\n\n"
            f"Student Profile:\n"
            f"- Preparation level: {prep}\n"
            f"- Available study hours/day: {hours}\n"
            f"- Exam date: {exam}\n\n"
            f"Study Material:\n{text_content}\n\n"
            f"JSON Response:"
        )

    def _parse_ai_response(self, raw_text: str, student_info: dict) -> dict:
        """
        Safely parse AI output.
        Tries direct JSON parse, then extracts JSON block, then returns a fallback.
        """
        text = raw_text.strip()

        # Remove markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        # Try direct parse
        try:
            data = json.loads(text)
            return self._validate_structure(data)
        except json.JSONDecodeError:
            pass

        # Try extracting first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return self._validate_structure(data)
            except json.JSONDecodeError:
                pass

        # Fallback: wrap raw text in a minimal structure
        logger.warning("IBM AI returned non-JSON response; using text fallback.")
        return {
            "summary": text[:800] if text else "Summary not available.",
            "key_concepts": [],
            "important_definitions": [],
            "formulas": [],
            "key_takeaways": [],
            "important_topics": [],
            "flashcards": [],
            "quiz": [],
            "study_recommendations": [
                "Please review the uploaded material carefully.",
                "Try again if the AI response seems incomplete.",
            ],
            "raw_response": text[:2000],
        }

    @staticmethod
    def _validate_structure(data: dict) -> dict:
        """Ensure required keys exist with correct types."""
        defaults = {
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
        for key, default in defaults.items():
            if key not in data:
                data[key] = default
            elif not isinstance(data[key], type(default)):
                data[key] = default
        return data
