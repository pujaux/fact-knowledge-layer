"""Thin wrapper around the Groq API. Groq's API is OpenAI-compatible,
so we reuse the `openai` SDK and just point it at Groq's base URL."""

import json
import re
import time
from openai import OpenAI
from app.config import GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL, MAX_FACTS_TOKENS, MAX_RELATION_TOKENS, REQUEST_DELAY_SECONDS

client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

EXTRACTION_SYSTEM_PROMPT = """You extract verifiable facts from a chunk of a business/economic document.
A "fact" is a specific numerical or clearly-stated semantic claim: a metric with a value, a status, a
relationship, or an event tied to an entity, time period, or scope.

Rules:
- Only extract facts that are explicitly stated in the text. Never infer or calculate new numbers.
- Each fact must include a short verbatim quote (<= 25 words) copied exactly from the text that proves it.
- Include the page number the quote came from (the text is tagged with [Page N] markers).
- If a value has a unit, period, or scope (e.g. "FY24", "as of March 2025", "consolidated"), capture it.
- Skip boilerplate, table-of-contents entries, and vague statements with no concrete value or claim.
- Return AT MOST 12 of the most important facts from this chunk. Prefer facts likely to recur elsewhere
  (revenue, growth rates, headcount, GDP, inflation, ownership %, dates of appointment/resignation, etc.)

Return ONLY valid JSON, no prose, no markdown fences, matching exactly this schema:
{"facts": [
  {"entity": "string", "metric": "string", "value": "string", "unit": "string or null",
   "period": "string or null", "scope": "string or null", "quote": "string", "page": 0}
]}
"""

RELATION_SYSTEM_PROMPT = """You compare two facts extracted from different (or the same) documents and
decide how they relate. Base your judgment ONLY on the two facts and quotes given -- do not assume outside
knowledge.

Classify the relationship as exactly one of:
- "corroborate": both facts state the same underlying truth, even if worded differently or rounded differently.
- "contradict": the facts genuinely conflict with no obvious reconciling explanation in the text given.
- "reconcilable": the facts look different or conflicting on the surface, but differ in period, scope, unit,
  or definition in a way that explains the difference (e.g. standalone vs consolidated, different fiscal years).
- "unrelated": on inspection these aren't actually about the same underlying fact.

Return ONLY valid JSON, no prose, no markdown fences:
{"relation": "corroborate|contradict|reconcilable|unrelated",
 "confidence": 0.0,
 "explanation": "one or two sentences citing what in the two quotes drove this decision"}
"""


def _extract_json(raw: str) -> dict:
    """Parse the model's response into JSON, tolerating markdown fences and
    any stray text around the JSON object (Groq occasionally adds a little
    of both despite instructions not to)."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        raw = raw.rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _call_groq(system_prompt: str, user_content: str, max_tokens: int) -> dict:
    """Call Groq API with rate limit handling and exponential backoff retry.
    
    Handles:
    - 429 (Rate Limit): Waits and retries with exponential backoff
    - 400 (Request Too Large): Reports chunk size issue
    - Other errors: Logs and raises
    """
    max_retries = 3
    base_wait_time = 1  # Start with 1 second
    
    for attempt in range(max_retries):
        try:
            # Rate limit delay before each call
            time.sleep(REQUEST_DELAY_SECONDS)
            
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                temperature=0,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                # NOTE: deliberately NOT using response_format={"type": "json_object"} --
                # on dense, table-heavy pages Groq's strict JSON mode was hard-rejecting
                # the whole response (empty failed_generation, HTTP 400) instead of
                # returning something we could recover. Prompting for JSON + parsing
                # defensively in _extract_json is more forgiving and still reliable.
            )
            raw = resp.choices[0].message.content.strip()
            return _extract_json(raw)
        
        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str or "rate_limit" in error_str.lower()
            is_too_large = "request too large" in error_str.lower() or "400" in error_str
            
            # Rate limit: exponential backoff retry
            if is_rate_limit:
                if attempt < max_retries - 1:
                    wait_time = base_wait_time * (2 ** attempt)  # 1s, 2s, 4s
                    print(f"[⏳ Rate limited] Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[❌ Rate limit] Max retries exhausted after {max_retries} attempts")
                    raise
            
            # Request too large: report and fail
            if is_too_large:
                print(f"[❌ Chunk too large] Request exceeds token limits.")
                print(f"    Reduce CHUNK_CHAR_SIZE in app/config.py (currently 800-1500)")
                raise
            
            # Other errors: log and raise immediately
            print(f"[❌ Groq API error] {e}")
            raise
    
    raise Exception(f"Failed after {max_retries} retries")


def extract_facts(chunk_text: str, doc_name: str) -> list:
    """Extract facts from a text chunk using Groq.
    
    Returns empty list on failure (already logged to console).
    """
    user_content = f"Document: {doc_name}\n\nText:\n{chunk_text}"
    try:
        data = _call_groq(EXTRACTION_SYSTEM_PROMPT, user_content, MAX_FACTS_TOKENS)
        return data.get("facts", [])
    except Exception as e:
        print(f"[extract_facts] failed for {doc_name}: {e}")
        return []


def classify_relationship(fact_a: dict, fact_b: dict) -> dict:
    """Classify relationship between two facts using Groq.
    
    Returns None on failure (already logged to console).
    """
    user_content = (
        f"FACT A (from {fact_a['doc_name']}, page {fact_a['page']}):\n"
        f"entity={fact_a['entity']}, metric={fact_a['metric']}, value={fact_a['value']} {fact_a.get('unit') or ''}, "
        f"period={fact_a.get('period')}, scope={fact_a.get('scope')}\n"
        f"quote: \"{fact_a['quote']}\"\n\n"
        f"FACT B (from {fact_b['doc_name']}, page {fact_b['page']}):\n"
        f"entity={fact_b['entity']}, metric={fact_b['metric']}, value={fact_b['value']} {fact_b.get('unit') or ''}, "
        f"period={fact_b.get('period')}, scope={fact_b.get('scope')}\n"
        f"quote: \"{fact_b['quote']}\""
    )
    try:
        return _call_groq(RELATION_SYSTEM_PROMPT, user_content, MAX_RELATION_TOKENS)
    except Exception as e:
        print(f"[classify_relationship] failed: {e}")
        return None