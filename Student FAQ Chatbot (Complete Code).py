# Install required libraries (run once in Colab)
# !pip install nltk scikit-learn

import nltk
import string
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab') # Added this line to download the missing resource

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# -------------------------------
# 1. FAQ DATA
# -------------------------------
faq_data = {
    "What are the college timings?": "College timings are 9 AM to 5 PM.",
    "What is the fee structure?": "The fee structure varies by course. Please check the website.",
    "How can I contact the office?": "You can contact the office at office@college.com.",
    "When are exams conducted?": "Exams are conducted at the end of each semester.",
    "Is hostel available?": "Yes, hostel facilities are available for students.",
    "How to apply for admission?": "You can apply online through the college website.",
    "Are scholarships available?": "Yes, scholarships are available based on merit.",
    "What courses are offered?": "We offer B.Tech and MBA programs.",
    "Where is the college located?": "The college is located in Nagpur(Wathoda).",
    "What is the exam timetable?": "Exam timetable will be shared before exams."
}

questions = list(faq_data.keys())
answers = list(faq_data.values())

# -------------------------------
# 2. TEXT PREPROCESSING
# -------------------------------
stop_words = set(stopwords.words('english'))

def preprocess(text):
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    tokens = word_tokenize(text)
    tokens = [word for word in tokens if word not in stop_words]
    return " ".join(tokens)

# preprocess all questions
processed_questions = [preprocess(q) for q in questions]

# -------------------------------
# 3. TF-IDF MODEL
# -------------------------------
vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(processed_questions)

# -------------------------------
# 4. SYNONYM HANDLING (simple)
# -------------------------------
synonyms = {
    "fees": "fee",
    "payment": "fee",
    "exam": "exams",
    "test": "exams",
    "hostel": "hostel",
    "admission": "apply",
}

def apply_synonyms(text):
    words = text.split()
    new_words = [synonyms.get(word, word) for word in words]
    return " ".join(new_words)

# -------------------------------
# 5. CHATBOT FUNCTION
# -------------------------------
def chatbot_response(user_input):
    user_input = preprocess(user_input)
    user_input = apply_synonyms(user_input)

    user_vec = vectorizer.transform([user_input])
    similarity = cosine_similarity(user_vec, tfidf_matrix)

    index = similarity.argmax()
    score = similarity[0][index]

    if score < 0.3:
        return "Sorry, I didn't understand that. Please ask something else."

    return answers[index]

# -------------------------------
# 6. CHAT LOOP
# -------------------------------
print("Student FAQ Chatbot (type 'exit' to stop)\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("Bot: Goodbye!")
        break

    response = chatbot_response(user_input)
    print("Bot:", response)
