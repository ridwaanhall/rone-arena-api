"""Remove the game's unfilled text placeholders from upstream JSON.

The game writes some numbers into its texts at run time, and the content source sometimes ships the
template without them:

- ``<NumN>`` / ``<%NumN>`` in a description (Retribution's "and <Num9> kills or assists to gain <Num10>
  Physical Attack"): the values are nowhere in the record, so the clause that needs them is cut, ending
  the sentence at the last comma before it (the whole sentence goes when it has no comma).
- ``<#bv N>``, a live in-game counter ("(Current: <#bv 25>)"): the parenthesis around it goes, or the
  token alone.

``skilldesc_text`` is left alone: it is a template on purpose, filled from ``numdescribe`` beside it,
and ``skilldesc`` already holds the filled text. Strings without ``<`` are never touched.
"""
from __future__ import annotations

import re
from typing import Any

TEMPLATE_KEYS = frozenset({"skilldesc_text"})

_NUM = re.compile(r"<%?Num\d+>")
_COUNTER_IN_PARENS = re.compile(r"\s*[(（][^()（）]*<#bv[^>]*>[^()（）]*[)）]")
_COUNTER = re.compile(r"<#bv[^>]*>")
# A full stop ends a sentence only before a space or the end ("0.5%" does not); CJK marks and line breaks always do.
_SENTENCE_END = re.compile(r"[.!?](?=\s|$)|[。！？\n]")
_CLAUSE_MARKS = (", ", "，", "、", "، ", "; ")


def _cut_clause(text: str, at: int) -> str:
    """Drop the clause holding the placeholder at ``at``, ending its sentence at the comma before it."""
    start = max((m.end() for m in _SENTENCE_END.finditer(text, 0, at)), default=0)
    after = _SENTENCE_END.search(text, at)
    end = after.start() if after else len(text)
    stop = text[end] if end < len(text) and text[end] != "\n" else ""
    comma = max(text.rfind(mark, start, at) for mark in _CLAUSE_MARKS)
    if comma != -1:
        return text[:comma] + (stop or ".") + text[end + len(stop):]
    # No comma: the whole sentence needs the missing numbers.
    rest = text[end + len(stop):]
    return text[:start] + (rest.lstrip(" ") if start == 0 else rest)


def clean_text(text: str) -> str:
    if "<" not in text:
        return text
    text = _COUNTER.sub("", _COUNTER_IN_PARENS.sub("", text))
    for _ in range(20):  # each pass removes at least one placeholder
        match = _NUM.search(text)
        if not match:
            break
        text = _cut_clause(text, match.start())
    return text


def clean_game_json(data: Any, key: str | None = None) -> Any:
    """Clean every string in a JSON-like structure, except the template fields."""
    if isinstance(data, str):
        return data if key in TEMPLATE_KEYS else clean_text(data)
    if isinstance(data, list):
        return [clean_game_json(item, key) for item in data]
    if isinstance(data, dict):
        return {k: clean_game_json(v, k) for k, v in data.items()}
    return data
