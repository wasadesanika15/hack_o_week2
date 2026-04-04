"""
Orchestrates preprocessing, synonyms, intent, entities, retrieval, and session context.

Final deliverable function: ``get_response(query: str, session_id: str) -> str``
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .context_manager import get_context_manager
from .entity_extractor import extract_entities
from .intent_classifier import get_classifier, predict_intent
from .preprocessor import preprocess
from .retrieval import get_best_match, log_query


def _data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data"


@lru_cache(maxsize=1)
def _synonym_map() -> dict[str, list[str]]:
    path = _data_dir() / "synonyms.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("synonyms.json must be a JSON object")
    return data


def expand_synonyms(preprocessed: str) -> str:
    """
    Map synonym tokens onto canonical keys listed in ``data/synonyms.json``.

    ``preprocessed`` must be the whitespace-separated output of ``preprocess``.
    """
    syn_map = _synonym_map()
    reverse: dict[str, str] = {}
    for canon, syns in syn_map.items():
        key = str(canon).lower()
        reverse[key] = key
        for s in syns:
            reverse[str(s).lower()] = key
    tokens = (preprocessed or "").split()
    return " ".join(reverse.get(t, t) for t in tokens)


def _clean_entities(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if v is None or v == "" or v == []:
            continue
        out[k] = v
    return out


def _inject_entities(template: str, entities: dict[str, Any]) -> str:
    """
    Replace ``{entity_key}`` placeholders in *template* with actual entity values.

    If a placeholder has no matching entity, remove it gracefully with a generic phrase.
    """
    if not entities or "{" not in template:
        return template

    result = template
    for key, value in entities.items():
        placeholder = "{" + key + "}"
        if placeholder in result:
            result = result.replace(placeholder, str(value))

    # Remove any remaining unfilled placeholders gracefully
    result = re.sub(r"\{semester\}", "the current semester", result)
    result = re.sub(r"\{department\}", "your department", result)
    result = re.sub(r"\{course_code\}", "the relevant course", result)
    result = re.sub(r"\{date\}", "the scheduled date", result)
    result = re.sub(r"\{year\}", "your year", result)

    return result


def _suggestions(is_fallback: bool, intent: str) -> list[str]:
    chips = [
        "College timings",
        "Fee payment deadline",
        "Semester exam dates",
        "Hostel allotment",
        "Scholarships",
        "Placement cell contact",
    ]
    if not is_fallback:
        if intent == "fees":
            return ["Tuition fees", "Hostel fees", "Late fee policy"]
        if intent == "exam":
            return ["Exam timetable", "Supplementary exams"]
        if intent == "hostel":
            return ["Hostel fees", "Hostel allotment", "Mess menu"]
        if intent == "placement":
            return ["Placement stats", "Internship opportunities"]
        if intent == "library":
            return ["Library timing", "Book borrowing rules"]
        if intent == "attendance":
            return ["Attendance requirement", "Medical exemption"]
        return chips[:4]
    return chips


def get_chat_payload(query: str, session_id: str) -> dict[str, Any]:
    """
    Full bot result used by FastAPI and the static CampusBot frontend.

    Keys align with ``Student-faq/frontend/script.js`` expectations.
    """
    q = (query or "").strip()
    mgr = get_context_manager()
    state = mgr.get(session_id)

    # --- Entity extraction ---
    fresh = _clean_entities(extract_entities(q))
    merged = {**state.last_entities, **fresh}

    # --- Intent classification ---
    intent = predict_intent(q)
    clf = get_classifier()
    prob_map = clf.predict_proba_dict(q)
    intent_confidence = float(prob_map.get(intent, 0.0))

    # --- Preprocessing + synonym expansion ---
    processed = preprocess(q)
    expanded = expand_synonyms(processed)

    # Light follow-up boost: very short utterances reuse last non-general topic
    retrieval_query = expanded
    
    is_short_followup = len(q.split()) <= 4
    has_followup_keywords = q.lower().startswith(("and ", "what about ", "how about ", "for "))
    
    if (
        (is_short_followup or has_followup_keywords)
        and state.last_intent
        and state.last_intent != "general"
        and intent == "general"
    ):
        retrieval_query = f"{expanded} {state.last_intent}".strip()
        intent = state.last_intent  # Reuse intent for filtering

    # --- TF-IDF retrieval (intent-filtered for precision) ---
    match = get_best_match(retrieval_query, intent_filter=intent)

    # --- Entity injection into answer template (Task 6) ---
    answer_template = match.get("answer_template", match["answer"])
    if merged and answer_template:
        answer = _inject_entities(answer_template, merged)
    else:
        answer = match["answer"]

    # --- Query logging (Task 4) ---
    log_query(q, match.get("matched_question"), float(match["confidence"]))

    # Blend displayed confidence
    combined_confidence = max(
        float(match["confidence"]),
        intent_confidence * 0.35,
    )
    if match["fallback"]:
        combined_confidence = float(match["confidence"])

    payload = {
        "response": answer,
        "answer": answer,
        "intent": intent,
        "confidence": round(min(combined_confidence, 1.0), 4),
        "entities": merged,
        "suggestions": _suggestions(match["fallback"], intent),
        "fallback": match["fallback"],
    }

    # --- Update session context (Task 7 — includes auto-reset / topic change) ---
    mgr.update(
        session_id,
        intent=intent,
        entities=merged,
        response=answer,
        user_message=q,
    )
    return payload


def get_response(query: str, session_id: str) -> str:
    """
    Primary hook required by the hackathon brief — returns answer text only.

    This is the FINAL function signature: ``get_response(query: str, session_id: str) -> str``.
    Member B wires this into FastAPI.
    """
    return get_chat_payload(query, session_id)["response"]
