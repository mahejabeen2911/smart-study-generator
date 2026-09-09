"""
StudyGenAI — Smart Study Generator Agent
Main Flask application entry point.
"""

import os
import json
import uuid
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from services.document_processor import DocumentProcessor
from services.study_generator import StudyGenerator
from services.grok_service import GrokService
from services.ibm_agent import IBMAgent

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(32))

# ── Upload configuration ──────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"pdf", "txt", "jpg", "jpeg", "png"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Service instances ─────────────────────────────────────────────────────────
doc_processor = DocumentProcessor()
study_generator = StudyGenerator()
grok_service = GrokService()
ibm_agent = IBMAgent()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generator")
def generator():
    return render_template("generator.html")


@app.route("/generate-study", methods=["POST"])
def generate_study():
    """Receive study material, process it, and return generated resources."""
    try:
        text_content = ""

        # ── 1. Extract text ───────────────────────────────────────────────────
        if "study_file" in request.files and request.files["study_file"].filename:
            file = request.files["study_file"]
            if not allowed_file(file.filename):
                return render_template(
                    "error.html",
                    error="Unsupported file type. Please upload a PDF, TXT, JPG, JPEG, or PNG file."
                )
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], f"{uuid.uuid4()}_{filename}")
            file.save(filepath)

            ext = filename.rsplit(".", 1)[1].lower()
            text_content = doc_processor.extract_text(filepath, ext)

            # Clean up uploaded file after extraction
            try:
                os.remove(filepath)
            except OSError:
                pass

        elif request.form.get("pasted_text", "").strip():
            text_content = request.form["pasted_text"].strip()
        else:
            return render_template("error.html", error="Please upload a file or paste your study notes.")

        # ── 2. Basic length guard ─────────────────────────────────────────────
        if len(text_content) < 50:
            return render_template("error.html", error="Study material is too short. Please provide more content.")

        # Truncate very large inputs to avoid token overflow
        if len(text_content) > 15000:
            text_content = text_content[:15000] + "\n\n[Content truncated to fit AI limits]"

        # ── 3. Student / exam metadata ────────────────────────────────────────
        student_info = {
            "name": request.form.get("student_name", "Student"),
            "course": request.form.get("course", ""),
            "branch": request.form.get("branch", ""),
            "semester": request.form.get("semester", ""),
            "exam_date": request.form.get("exam_date", ""),
            "study_hours": request.form.get("study_hours", "2"),
            "prep_level": request.form.get("prep_level", "Intermediate"),
            "preferred_method": request.form.get("preferred_method", "Mixed learning"),
        }

        # ── 4. Try IBM agent first, fall back to local generator ──────────────
        result = None
        ibm_available = ibm_agent.is_configured()

        if ibm_available:
            try:
                result = ibm_agent.run_study_workflow(text_content, student_info)
            except Exception as ibm_err:
                app.logger.warning("IBM agent failed, falling back: %s", ibm_err)
                result = None

        if not result:
            result = study_generator.generate(text_content, student_info)

        # ── 5. Store in session for quiz submission ───────────────────────────
        session["study_result"] = result
        session["student_info"] = student_info

        return render_template(
            "results.html",
            result=result,
            student_info=student_info,
            ibm_used=ibm_available and result.get("ibm_used", False),
        )

    except Exception as exc:
        app.logger.error("generate_study error: %s", exc)
        return render_template(
            "error.html",
            error="Sorry, we couldn't generate your study material right now. Please try again."
        )


@app.route("/assistant")
def assistant():
    return render_template("assistant.html")


@app.route("/assistant/chat", methods=["POST"])
def assistant_chat():
    """Handle chat messages from the AI Study Assistant."""
    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"error": "Please enter a message."}), 400

        # Provide optional study context from session
        study_context = ""
        study_result = session.get("study_result")
        if study_result:
            summary = study_result.get("summary", "")
            if summary:
                study_context = f"The student has uploaded study material. Summary: {summary[:800]}"

        response_text = grok_service.chat(user_message, study_context)
        return jsonify({"response": response_text})

    except Exception as exc:
        app.logger.error("assistant_chat error: %s", exc)
        return jsonify({"error": "AI assistant is unavailable right now. Please try again."}), 500


@app.route("/dashboard")
def dashboard():
    study_result = session.get("study_result")
    student_info = session.get("student_info", {})
    quiz_scores = session.get("quiz_scores", [])
    return render_template(
        "dashboard.html",
        study_result=study_result,
        student_info=student_info,
        quiz_scores=quiz_scores,
    )


@app.route("/quiz/submit", methods=["POST"])
def quiz_submit():
    """Process quiz answers and identify weak/strong topics."""
    try:
        data = request.get_json(silent=True) or {}
        answers = data.get("answers", [])   # [{question_index, selected, correct}, …]
        quiz = session.get("study_result", {}).get("quiz", [])

        if not answers or not quiz:
            return jsonify({"error": "No quiz data found. Please generate study material first."}), 400

        total = len(answers)
        correct_count = sum(1 for a in answers if a.get("is_correct", False))
        score_pct = round((correct_count / total) * 100) if total else 0

        # Simple topic performance: group by question index
        weak_topics = []
        strong_topics = []
        for i, answer in enumerate(answers):
            if i < len(quiz):
                q = quiz[i]
                topic = q.get("topic", f"Question {i + 1}")
                if answer.get("is_correct"):
                    strong_topics.append(topic)
                else:
                    weak_topics.append(topic)

        # Remove duplicates, keep order
        weak_topics = list(dict.fromkeys(weak_topics))
        strong_topics = list(dict.fromkeys(strong_topics))

        quiz_result = {
            "total": total,
            "correct": correct_count,
            "wrong": total - correct_count,
            "score_pct": score_pct,
            "weak_topics": weak_topics,
            "strong_topics": strong_topics,
        }

        # Persist score history in session
        scores = session.get("quiz_scores", [])
        scores.append(score_pct)
        session["quiz_scores"] = scores[-10:]  # keep last 10
        session["quiz_result"] = quiz_result

        return jsonify(quiz_result)

    except Exception as exc:
        app.logger.error("quiz_submit error: %s", exc)
        return jsonify({"error": "Could not process quiz results."}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(413)
def request_entity_too_large(_):
    return render_template("error.html", error="File is too large. Maximum upload size is 10 MB."), 413


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", error="Page not found."), 404


@app.errorhandler(500)
def internal_server_error(_):
    return render_template("error.html", error="An unexpected error occurred. Please try again."), 500


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
