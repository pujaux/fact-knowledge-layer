"""Grounding check: confirms a fact's quote is an actual verbatim substring of
the page/chunk text it claims to come from, rather than trusting the LLM's
claim at face value.

Why this matters: without this check, a hallucinated quote is indistinguishable
in the UI from a real one -- both just look like quoted text next to a fact.
This is the system's only real defense against ungrounded facts, and it's also
what the assignment asks for directly ("link every fact to evidence in its
source document").
"""

import re


def _normalize(s: str) -> str:
    # Collapse whitespace/case so verification survives PDF line-wrap quirks
    # (a quote that wraps mid-sentence in the source shouldn't fail just
    # because of a newline where the model's copy has a space).
    return re.sub(r"\s+", " ", s or "").strip().lower()


def verify_quote(quote: str, source_text: str) -> bool:
    """True if `quote` is a literal (whitespace/case-insensitive) substring
    of `source_text`. False for empty/missing quotes."""
    if not quote or not source_text:
        return False
    return _normalize(quote) in _normalize(source_text)
