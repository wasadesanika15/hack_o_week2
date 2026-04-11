# 🎓 Student FAQ Chatbot — Hack-O-Week

A progressive, NLP-powered student FAQ chatbot built over 10 weeks as part of the **Hack-O-Week** challenge. The project evolves from a simple rule-based responder into a full-featured retrieval and intent-aware chatbot, complete with a web interface.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pip
- Browser (Chrome / Edge / Firefox)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/wasadesanika15/hack_o_week2.git
   cd hack_o_week2
   ```

2. Install the required dependencies:
   ```bash
   pip install nltk scikit-learn flask
   ```

3. Download NLTK resources (first-time setup):
   ```python
   import nltk
   nltk.download('punkt')
   nltk.download('stopwords')
   nltk.download('punkt_tab')
   ```

---

## 📅 Weekly Progression (Modules)

The chatbot is built progressively over 10 weeks. Each module introduces a new capability on top of the previous one.

| Week | Case Scenario | What's Implemented |
|------|--------------|-------------------|
| **Week 1** | Basic FAQ Responder | Rule-based chatbot answering 10–15 fixed institute FAQs (timings, fees, contacts) using `if–else` / pattern matching. |
| **Week 2** | Preprocessing Student Queries | NLP pipeline: lowercasing, tokenization, stopword removal, punctuation handling, and basic spelling normalization. |
| **Week 3** | Synonym-Aware FAQ Bot | Synonym dictionary / keyword groups so queries like "fees", "tuition", and "payment" all map to the same answer. |
| **Week 4** | FAQ Retrieval with TF-IDF | TF-IDF vectorization + cosine similarity to retrieve the most relevant FAQ answer for any student query. |
| **Week 5** | Intent Classification | Classifier routing queries into 5–7 intents: admissions, exams, timetable, hostel, scholarships, etc. |
| **Week 6** | Entity Extraction | Regex-based extraction of dates, course codes, and semester numbers from queries (e.g., *"When is SEM 5 CS exam?"*). |
| **Week 7** | Context Handling for Follow-ups | Session-based state to handle multi-turn conversations (e.g., *"When is the exam?"* → *"For third year?"*). |
| **Week 8** | Fallbacks and Handover | Strategy for out-of-scope queries: ask for clarification, offer suggestions, or route to a human advisor. |
| **Week 9** | Multichannel Deployment Mockup | Prototype of chatbot behavior across web, mobile app, and WhatsApp — simulated via console/CLI. |
| **Week 10** | Analytics and Continuous Improvement | Interaction logging, sample labeling, and proposals for new intents, FAQs, and better patterns. |

---

## 🌐 Web Application

The `college-faq-chatbot` folder contains a full web interface for the chatbot.

### Running the Web App

1. Navigate to the web app folder:
   ```bash
   cd college-faq-chatbot
   ```

2. Start the server:
   ```bash
   python app.py
   ```

3. Open your browser and visit:
   ```
   http://localhost:5000
   ```

---

## 📂 Project Structure

```
hack_o_week2/
│
├── Student-faq/                         # Weekly module scripts
├── college-faq-chatbot/                 # Full web application (Flask + HTML/CSS/JS)
├── Student FAQ Chatbot (Complete Code).py  # All-in-one combined chatbot script
├── output of hack o week.png            # Sample output screenshot
└── README.md
```

---

## 🧠 Core Chatbot Features (Complete Code)

The file `Student FAQ Chatbot (Complete Code).py` integrates Weeks 1–4 into a single runnable script:

- **FAQ Knowledge Base** — 10 pre-loaded institute FAQs
- **Text Preprocessing** — lowercase, punctuation removal, tokenization, stopword filtering
- **Synonym Normalization** — maps variant terms (e.g., "payment" → "fee") before matching
- **TF-IDF Retrieval** — selects the most relevant answer using cosine similarity
- **Confidence Threshold** — returns a fallback message when similarity score is below 0.3

### Running the Chatbot (CLI)

```bash
python "Student FAQ Chatbot (Complete Code).py"
```

**Example interaction:**
```
Student FAQ Chatbot (type 'exit' to stop)

You: what are the payment details
Bot: The fee structure varies by course. Please check the website.

You: is accommodation provided
Bot: Yes, hostel facilities are available for students.

You: exit
Bot: Goodbye!
```

---

## 🛠️ Built With

| Layer | Technology |
|-------|-----------|
| Language | Python 3 |
| NLP | NLTK (tokenization, stopwords), scikit-learn (TF-IDF, cosine similarity) |
| Web Backend | Flask |
| Frontend | HTML5, CSS3, JavaScript |
| Deployment | Docker (Dockerfile included) |

---

## 👤 Author

**Sanika Wasade**
[GitHub Profile](https://github.com/wasadesanika15)
**Sparsh Goswami**
[GitHub Profile](https://github.com/sparsh566)
**Arya Patle**
[GitHub Profile](https://github.com/Aryapatle)

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
