"""
Streamlit demo shell for the College FAQ Chatbot.

Run backend first (port 8000), then:
    pip install streamlit httpx
    streamlit run app.py
"""

from __future__ import annotations

import uuid

import streamlit as st

from utils.api_client import send_chat

st.set_page_config(page_title="College FAQ Chatbot", page_icon="🎓", layout="centered")
st.title("College FAQ Chatbot")
st.caption("Posts to the FastAPI service at `CHATBOT_API_BASE` (default http://127.0.0.1:8000).")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

session_id = st.text_input("Session ID", value=st.session_state.session_id)
user_q = st.text_area("Your question", placeholder="e.g. When are semester exams for CS?")

if st.button("Send", type="primary") and user_q.strip():
    try:
        data = send_chat(user_q.strip(), session_id)
        st.success(data.get("response", data.get("answer", "")))
        cols = st.columns(3)
        cols[0].metric("Intent", data.get("intent", "—"))
        cols[1].metric("Confidence", f"{float(data.get('confidence', 0)):.2f}")
        cols[2].metric("Fallback", "yes" if data.get("fallback") else "no")
        if data.get("entities"):
            st.json(data["entities"])
        if data.get("suggestions"):
            st.write("Try next:", ", ".join(data["suggestions"]))
    except Exception as exc:  # pragma: no cover - demo UI
        st.error(f"API error: {exc}")
