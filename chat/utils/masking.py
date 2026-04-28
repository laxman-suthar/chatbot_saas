import re


# ── Placeholder map (session-level, not persisted) ────────────────────────────
# Used to anonymize text before sending to LLM

def anonymize_for_llm(text: str, visitor_details: dict = None) -> str:
    """
    Replace PII with readable placeholders before sending to LLM.
    LLM sees [NAME], [EMAIL] etc — never real values.
    """
    if not text:
        return text

    counter = {'n': 0}

    def next_ph(label):
        counter['n'] += 1
        return f"[{label}_{counter['n']}]" if counter['n'] > 1 else f"[{label}]"

    # replace known collected fields first (highest priority)
    if visitor_details:
        for key, value in visitor_details.items():
            if value and isinstance(value, str) and len(value) > 1:
                placeholder = f"[{key.upper()}]"
                text = text.replace(value, placeholder)

    # replace emails
    text = re.sub(
        r'[\w\.-]+@[\w\.-]+\.\w+',
        lambda m: next_ph('EMAIL'),
        text
    )

    # replace phones (10+ digits, with optional spaces/dashes)
    text = re.sub(
        r'\b\d[\d\s\-]{8,}\d\b',
        lambda m: next_ph('PHONE'),
        text
    )

    # replace credit cards
    text = re.sub(
        r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
        lambda m: next_ph('CARD'),
        text
    )

    return text


def mask_for_display(text: str, visitor_details: dict = None) -> str:
    """
    Partially mask PII for display in widget history.
    Shows first 2 chars then ***
    e.g. laxman@gmail.com → la***@***.***
         9876543210       → 98********
         Laxman           → La****
    """
    if not text:
        return text

    # mask known collected fields
    if visitor_details:
        for key, value in visitor_details.items():
            if value and isinstance(value, str) and len(value) > 2:
                masked = value[:2] + '*' * (len(value) - 2)
                text = text.replace(value, masked)

    # mask emails
    def mask_email(m):
        parts = m.group().split('@')
        return parts[0][:2] + '***@***.***'
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', mask_email, text)

    # mask phones
    text = re.sub(
        r'\b\d[\d\s\-]{8,}\d\b',
        lambda m: m.group()[:2] + '*' * (len(m.group()) - 2),
        text
    )

    # mask credit cards
    text = re.sub(
        r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
        '**** **** **** ****',
        text
    )

    return text

import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.output_parsers.react_single_input import ReActSingleInputOutputParser


# ── Patch the exact line that crashes ──────────────────────────────────────
_original_parse_result = ReActSingleInputOutputParser.parse_result

def _patched_parse_result(self, result, *, partial=False):
    # result[0].text is what crashes — flatten it if it's a list
    if result and hasattr(result[0], "text") and isinstance(result[0].text, list):
        parts = result[0].text
        result[0].text = " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in parts
        )
    return _original_parse_result(self, result, partial=partial)

ReActSingleInputOutputParser.parse_result = _patched_parse_result
# ───────────────────────────────────────────────────────────────────────────


class FlattenedGemini(ChatGoogleGenerativeAI):
    pass  # subclass kept so imports don't break elsewhere