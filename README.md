# StudyGenAI — Smart Study Generator Agent

> **"Turn your study material into a personalized learning plan."**

An AI-powered full-stack web application that helps students convert scattered study material into useful learning resources — summaries, flashcards, quizzes, and personalized study plans — using **IBM watsonx.ai**, **IBM Langflow / Orchestrate**, and the **Grok (Groq) API**.

---

## Architecture Diagram

```
Student
   ↓
Flask Application  (app.py)
   ↓
AI Orchestration Layer
   ↙              ↓              ↘
IBM Langflow   IBM watsonx.ai   Grok API
(Orchestrate)  (Granite model)  (Llama3)
   ↓              ↓              ↘
         Personalized Study Resources
              ↓
  Summary · Flashcards · Quiz · Study Plan · AI Chat
```

---

## Features

| Feature | Description |
|---|---|
| **Smart Summaries** | Overview, key concepts, definitions, formulas, takeaways |
| **Important Topic Detection** | Topics ranked 🔴 High / 🟡 Medium / 🟢 Low priority |
| **AI Flashcards** | Interactive flip cards with keyboard/swipe support |
| **MCQ Quiz** | Multiple-choice quiz with explanations and scoring |
| **Weak Topic Detection** | Identifies topics where the student needs more practice |
| **Personalized Study Plan** | Day-by-day schedule based on exam date and study hours |
| **AI Study Assistant** | Conversational chatbot for concept explanations (Grok) |
| **Progress Dashboard** | Session-based quiz history and topic overview |
| **IBM AI Integration** | watsonx.ai Granite model + Langflow agentic workflow |
| **Grok API Integration** | Conversational study assistant |

---

## Technology Stack

**Backend**
- Python 3.10+
- Flask 3.x
- python-dotenv
- pypdf (PDF text extraction)
- groq (official Groq SDK)
- requests (IBM watsonx.ai REST API)

**Frontend**
- HTML5 / CSS3 / Vanilla JavaScript
- Font Awesome 6 (icons)
- Responsive dashboard layout

**AI Services**
- IBM watsonx.ai (Granite model — primary study generator)
- IBM Langflow / IBM Orchestrate (agentic workflow orchestration)
- Grok / Groq API (AI Study Assistant + fallback generator)

---

## Project Structure

```
study-generator-agent/
│
├── app.py                        # Flask application & routes
├── requirements.txt
├── .env.example                  # Environment variable template
├── .gitignore
├── README.md
│
├── services/
│   ├── document_processor.py     # PDF / TXT text extraction
│   ├── grok_service.py           # Grok/Groq conversational assistant
│   ├── ibm_agent.py              # IBM watsonx.ai + Langflow integration
│   └── study_generator.py        # Fallback study generator (Groq)
│
├── templates/
│   ├── index.html                # Homepage
│   ├── generator.html            # Upload & form page
│   ├── results.html              # Study results dashboard
│   ├── assistant.html            # AI Study Assistant (chat)
│   ├── dashboard.html            # Progress dashboard
│   └── error.html                # Error page
│
├── static/
│   ├── css/style.css             # Global stylesheet
│   └── js/
│       ├── main.js               # Navigation, form, loading
│       ├── flashcards.js         # Flashcard flip widget
│       └── quiz.js               # Interactive MCQ quiz
│
└── uploads/                      # Temporary upload storage (gitignored)
```

---

## Installation

### Prerequisites

- Python 3.10 or later
- pip

### Step 1 — Clone the repository

```bash
git clone https://github.com/yourusername/studygenai.git
cd studygenai
```

### Step 2 — Create a virtual environment

**Windows**
```
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install dependencies

```
pip install -r requirements.txt
```

### Step 4 — Configure environment variables

```
copy .env.example .env
```

Open `.env` in a text editor and fill in your credentials (see the section below).

### Step 5 — Run the application

```
python app.py
```

Then open your browser at: **http://localhost:5000**

---

## Configuring API Keys

### Grok / Groq API (Required for AI features)

1. Go to [https://console.groq.com/](https://console.groq.com/) and create a free account.
2. Generate an API key.
3. Add it to `.env`:

```
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
```

**Available models:** `qwen/qwen3.8-27b` | `qwen/qwen3.6-27b` | `groq/compound` | `groq/compound-mini`

### IBM watsonx.ai (Optional — IBM integration)

1. Go to [https://cloud.ibm.com/](https://cloud.ibm.com/) and create an account.
2. Create a **Watson Machine Learning** service instance.
3. Create a **watsonx.ai project** and note the Project ID.
4. Generate an **API key** from IAM.
5. Add to `.env`:

```
IBM_API_KEY=your_ibm_api_key_here
IBM_PROJECT_ID=your_project_id_here
IBM_REGION=us-south
IBM_WX_MODEL=ibm/granite-13b-instruct-v2
```

When IBM credentials are present, the application uses IBM watsonx.ai as the primary AI engine.

### IBM Langflow / IBM Orchestrate (Optional — agentic workflow)

1. Deploy an IBM Langflow pipeline or IBM Orchestrate flow that accepts:
   ```json
   {
     "input_value": "<study text>",
     "tweaks": { "student_info": { ... } }
   }
   ```
2. Add the endpoint URL and bearer token to `.env`:

```
IBM_LANGFLOW_URL=https://your-endpoint/api/v1/run/your-flow-id
IBM_LANGFLOW_TOKEN=your_bearer_token
```

The application calls Langflow first (if configured), then falls back to direct watsonx.ai, then falls back to Groq.

---

## AI Workflow — How It Works

```
Student uploads study material
          ↓
  Flask receives request (app.py)
          ↓
  Document processor extracts text
          ↓
  IBM Langflow / Orchestrate (if configured)
          ↓ (fallback)
  IBM watsonx.ai Granite model (if configured)
          ↓ (fallback)
  Grok / Groq Llama3 model
          ↓
  AI generates JSON response:
    - Summary, Key Concepts, Definitions, Formulas
    - Important Topics (priority-ranked)
    - Flashcards (10–15)
    - MCQ Quiz (8–10 questions)
    - Study Recommendations
          ↓
  Results rendered in browser
          ↓
  Student takes quiz → weak topics detected
          ↓
  Personalized study plan generated
          ↓
  AI Study Assistant available for follow-up (Grok)
```

---

## Flask Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Homepage |
| `/generator` | GET | Upload page |
| `/generate-study` | POST | Process material & generate resources |
| `/assistant` | GET | AI Study Assistant page |
| `/assistant/chat` | POST | Send message to Grok assistant |
| `/dashboard` | GET | Progress dashboard |
| `/quiz/submit` | POST | Submit quiz answers |
| `/health` | GET | Health check (`{"status":"ok"}`) |

---

## System Prompt Philosophy

The AI is instructed to:

- Use **only** information from the uploaded material.
- **Never invent facts** or claim topics are "frequently asked" without evidence.
- Use **student-friendly language**.
- Adapt explanations to the student's **preparation level**.
- Generate **practical, exam-oriented** resources.
- Identify **weak topics** based on actual quiz performance only.

---

## Security

- API keys stored in `.env` — never exposed to JavaScript or HTML.
- `.env` is in `.gitignore`.
- Uploaded files are validated (type + size limit: 10 MB).
- Files are deleted after text extraction.
- Flask stack traces are hidden in production (`FLASK_DEBUG=false`).
- User inputs are sanitized via `werkzeug.utils.secure_filename`.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: groq` | Run `pip install groq` |
| `ModuleNotFoundError: pypdf` | Run `pip install pypdf` |
| AI returns demo content | Add `GROQ_API_KEY` to `.env` |
| IBM 401 Unauthorized | Check `IBM_API_KEY` and `IBM_PROJECT_ID` |
| PDF shows no text | PDF may be scanned — paste text manually |
| Port already in use | Change `PORT=5001` in `.env` |

---

## Development Phases

The project was built in phases for beginner-friendliness:

1. Flask application + homepage
2. PDF/TXT upload and text extraction  
3. IBM AI workflow integration
4. Summary and important topic generation
5. Flashcard generation
6. MCQ quiz generation
7. Quiz scoring and weak-topic detection
8. Personalized study plan
9. Grok AI Study Assistant
10. Progress dashboard
11. UI polish and error handling

---

## Future Improvements

- [ ] RAG (Retrieval-Augmented Generation) for multi-document study sessions
- [ ] User authentication and persistent progress storage
- [ ] Export study materials to PDF
- [ ] Spaced repetition algorithm for flashcard scheduling
- [ ] Voice-based study assistant
- [ ] Multi-language support
- [ ] Integration with Google Calendar for study plan scheduling
- [ ] Leaderboard / gamification for quiz scores

---

## License

MIT License — free for personal, educational, and commercial use.

---

*Built for college hackathons, GitHub portfolios, and resumes.*  
*Demonstrates: IBM watsonx.ai · IBM Langflow / Orchestrate · Grok API · Agentic AI workflow · Flask · Responsive web design*
