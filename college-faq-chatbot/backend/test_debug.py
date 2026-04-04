from modules.chatbot_core import get_chat_payload

TEST_QUERIES = [
    "What is the fee structure?",
    "btech fees?",
    "Fee payment deadline",
    "What is the exam schedule?",
    "How do I contact the administration?",
    "What scholarships are available?",
    "What are the placement statistics?",
    "mba?",
    "ok",
    "thanks",
    "bye",
    "hello",
    "hi",
    "What is my college name?",
    "What are the college timings?",
    "Does the college have hostel?",
    "What is the minimum attendance?",
]

if __name__ == "__main__":
    sid = "test-session"
    results = []
    for q in TEST_QUERIES:
        res = get_chat_payload(q, sid)
        fb = "YES" if res["fallback"] else "no"
        ans = res["answer"][:90].replace("\n", " ")
        results.append(f"Q: {q}\n  Intent={res['intent']}  Conf={res['confidence']:.2f}  Fallback={fb}\n  A: {ans}\n")
    
    with open("test_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results))
    
    for r in results:
        print(r)
