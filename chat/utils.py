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