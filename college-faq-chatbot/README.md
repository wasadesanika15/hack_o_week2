# College FAQ Chatbot

Production-oriented microservice for a campus FAQ assistant: **FastAPI** backend, **TF-IDF** retrieval, **intent classification**, **entity extraction**, **synonym expansion**, and **session context** for multi-turn conversations.

## Architecture

```
college-faq-chatbot/
├── backend/
│   ├── modules/
│   │   ├── chatbot_core.py       # Orchestrator — get_response(query, session_id)
│   │   ├── preprocessor.py       # Task 2: Text normalization + spelling correction
│   │   ├── retrieval.py          # Task 4: TF-IDF + cosine similarity retrieval
│   │   ├── intent_classifier.py  # Task 5: LogisticRegression intent classifier
│   │   ├── entity_extractor.py   # Task 6: Regex-based NER (sem, dept, date, course)
│   │   ├── context_manager.py    # Task 7: Per-session multi-turn context
│   │   └── __init__.py
│   ├── main.py                   # FastAPI server
│   └── requirements.txt
├── data/
│   ├── faq_data.json             # Task 1: 15 FAQ entries with categories + templates
│   ├── synonyms.json             # Task 3: Synonym groups for fuzzy matching
│   └── intents.json              # Task 5: 20+ training examples per intent
├── models/                       # Generated .pkl files (auto-created)
│   ├── tfidf_model.pkl
│   ├── intent_model.pkl
│   └── confusion_matrix.png
├── tests/                        # 7 test files covering all tasks
├── chat.py                       # Task 1: CLI test runner
├── train_models.py               # Train & save all ML models
└── README.md
```

## Quick Start

```bash
cd college-faq-chatbot/backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Train models (creates .pkl files in models/)
cd ..
python train_models.py

# Run CLI chatbot
python chat.py

# Run FastAPI server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API

`POST /chat`

```json
{
  "query": "What are the college timings?",
  "session_id": "user-123"
}
```

Response:

```json
{
  "response": "College timings are 9:00 AM to 5:00 PM on weekdays...",
  "answer": "College timings are 9:00 AM to 5:00 PM on weekdays...",
  "intent": "general",
  "confidence": 0.87,
  "entities": {},
  "suggestions": ["Fee payment deadline", "Semester exam dates"],
  "fallback": false
}
```

## 10 Sample Questions

| # | Question | Expected Topic |
|---|----------|---------------|
| 1 | What are the college timings? | Timings |
| 2 | How do I pay my fees online? | Fees |
| 3 | When are the semester exams? | Exams |
| 4 | How can I apply for admission? | Admissions |
| 5 | Are there any scholarships available? | Scholarships |
| 6 | Does the college have a hostel? | Hostel |
| 7 | How do I contact the IT department? | Contacts |
| 8 | What is the minimum attendance requirement? | Attendance |
| 9 | Where can I find my class timetable? | Timetable |
| 10 | What are the placement opportunities? | Placement |

## 3-Turn Conversation Demo (Task 7)

Multi-turn context allows follow-up queries without restating full context:

```
Student: What is the fee structure for CS?
Bot:     Fees vary by program. For the CS department, tuition for the current
         semester is payable via the online portal or demand draft. Late fees
         apply after the due date.

Student: And for semester 5?
Bot:     Fees vary by program. For the CS department, tuition for semester 5
         is payable via the online portal or demand draft. Late fees apply
         after the due date.

Student: What about exam dates?
Bot:     Semester 5 exams for CS are held at the end of the semester.
         Provisional dates are published on the institute portal at least
         two weeks in advance.
```

Notice how:
- **Turn 2** picks up `department: CS` from Turn 1 context, only adding `semester: 5`
- **Turn 3** carries both `semester: 5` and `department: CS` into the exam answer

## Entity Extraction Examples (Task 6)

| Query | Extracted Entities |
|-------|-------------------|
| `SEM 5 CS exam date` | `{semester: 5, department: 'CS'}` |
| `CS301 course timetable` | `{course_code: 'CS301', department: 'CS'}` |
| `third year EC placement` | `{year: 3, department: 'EC'}` |
| `exam on 15/11/2024 for EE` | `{department: 'EE', dates: ['2024-11-15']}` |
| `FY hostel allotment` | `{year: 1}` |

## Preprocessing Pipeline (Task 2)

| Original Input | After Preprocessing |
|----------------|-------------------|
| What are the college timings? | what college timing |
| How do I PAY my FEES online??? | how pay fee online |
| when is the next semester exam!! | when next semester exam |
| tell me abt scholrship eligibilty | tell scholarship eligibility |
| CS301 exam date for SEM 5 | cs301 exam date sem 5 |

## Running Tests

```bash
cd college-faq-chatbot
set PYTHONPATH=backend&& python -m pytest tests/ -v
```

On Linux/macOS:
```bash
PYTHONPATH=backend python -m pytest tests/ -v
```

Test files:
- `test_backend.py` — Full integration + 10 sample questions
- `test_preprocessor.py` — Normalization steps + before/after table
- `test_synonyms.py` — 5 variations per FAQ + coverage report
- `test_retrieval.py` — TF-IDF matching, fallback, model persistence
- `test_intent.py` — Per-category accuracy + confusion matrix
- `test_entities.py` — 10 queries with expected entity output
- `test_context.py` — Multi-turn, auto-reset, topic change

## Model Training

```bash
python train_models.py
```

Produces:
- `models/tfidf_model.pkl` — TF-IDF vectorizer + FAQ matrix
- `models/intent_model.pkl` — Intent classifier pipeline
- `models/confusion_matrix.png` — Visual evaluation chart

## Handoff to Member B

The final function signature is:

```python
from modules.chatbot_core import get_response

response: str = get_response(query="What are the fees?", session_id="user-123")
```

**No breaking changes after this.** Member B wires `get_response` into FastAPI at `POST /chat`.
