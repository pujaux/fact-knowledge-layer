# Fact Knowledge Layer (Groq-powered)

Extracts grounded facts from PDFs, links each to its source quote + page, and
uses Groq to judge whether facts across documents corroborate, contradict, or
are reconcilable through context (period/scope/unit differences).

## Setup and Run Instructions

1. **Python 3.10+** and a Groq API key (https://console.groq.com).
2. `cd` into this folder, create a virtualenv, install deps:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and paste your key:
   ```bash
   cp .env.example .env
   ```
4. Start the API (terminal 1):
   ```bash
   uvicorn app.api:app --reload --port 8000
   ```
5. Start the UI (terminal 2, same venv):
   ```bash
   streamlit run streamlit_app.py
   ```
6. Open the Streamlit URL it prints, upload a PDF from the sidebar, click
   **Process PDF**. Upload a second/third PDF from the same or a different
   domain to see cross-document relationships appear.

Facts persist in `data/facts.db` (SQLite) between runs — you don't need to
re-upload PDFs to see prior results.

## Video Demo
[link to be added]

## Approach

- **Extraction**: PDFs are split page-by-page (PyMuPDF), grouped into ~3000-char
  chunks, and each chunk is sent to Groq once with a strict JSON schema prompt
  asking for entity/metric/value/unit/period/scope + a short verbatim quote and
  page number. No hard-coded fields, filenames, or document-specific rules —
  the schema is generic enough to apply to any PDF.
- **Grounding**: every fact stores the exact quote and page it came from, so
  every claim in the UI is traceable back to source text. This is enforced,
  not just requested in the prompt: `app/grounding.py` checks that each
  fact's `quote` is an actual literal (whitespace/case-insensitive) substring
  of the page/chunk it claims to come from. Facts that fail this check are
  still stored (dropping them silently would hide the failure), but flagged
  with `quote_verified = False`, visible in the Streamlit "All Facts" tab.
  This is also real material for the "extraction/reasoning failure" case —
  a fact with an unverified quote is either a genuine hallucination or a
  quote mangled by a PDF-layout quirk (e.g. multi-column text), and the UI
  makes both visible rather than silently trusting the model.
- **Cross-document comparison (the token-saving trick)**: instead of asking an
  LLM to compare every fact to every other fact (O(n²) and expensive), all
  facts are embedded locally and for free with `sentence-transformers`
  (all-MiniLM-L6-v2). Cosine similarity narrows the field to each fact's
  top-5 cross-document neighbors above a threshold. **Only those candidate
  pairs get a Groq call**, which classifies the pair as
  corroborate / contradict / reconcilable / unrelated with a one-line
  explanation. This is what keeps this usable on a near-free API budget.
- **Incremental relationship discovery**: every classified pair — including
  ones judged `unrelated` — is stored in `relationships`, keyed by a
  normalized `(fact_a_id, fact_b_id)` pair under a UNIQUE index. Before
  calling Groq on any candidate pair, `db.relationship_exists()` checks
  whether that exact pair has already been judged; if so, it's skipped.
  So uploading a new document and re-running relationship discovery only
  spends Groq calls on genuinely new candidate pairs, never on pairs from
  documents already in the knowledge layer.
- **Storage**: plain SQLite — three tables (documents, facts, relationships).
  Deliberately boring so the reasoning stays inspectable and debuggable.
- **Interface**: FastAPI backend (`/upload`, `/facts`, `/relationships`) +
  a Streamlit front end for browsing facts, filtering relationships, and
  viewing evidence side by side.
- **AI tools used**: Groq (Llama/GPT-OSS models) for fact extraction and relationship
  classification; Claude for scaffolding this codebase.

## Limitations and Next Steps

- Extraction quality depends on chunk boundaries — a fact split across a
  page break can be missed or garbled. Next step: overlap chunks by ~200
  chars instead of hard-splitting on page boundaries.
- Unit/period normalization is left to the LLM's judgement at comparison time
  rather than a separate normalization pass — a dedicated unit-normalizer
  would make the embedding-based candidate search more precise.
- Relationship discovery is incremental (see above — already-judged pairs
  are never re-sent to Groq), but candidate *generation* itself still
  re-embeds and re-scans every fact on every run. Fine at this scale
  (embeddings are local/free), but would need an index (e.g. FAISS) and a
  "only generate candidates involving the newest document" mode for
  many-document scale.
- Schema is currently flat/fixed (entity/metric/value/unit/period/scope) —
  it generalizes across our two starter domains (corporate + macro) but a
  fully dynamic schema (fields appearing/disappearing per document type)
  would need a second Groq pass to propose new fields.
- Evidence-quote verification (`grounding.py`) only checks that the quote
  exists verbatim on the page — it doesn't check that the quote actually
  *supports* the claimed value (a plausible-sounding but irrelevant quote
  would still pass). A stronger check would ask the LLM to re-justify the
  value from the verified quote alone, as a second pass.

## Additional Notes

- The four required demo cases (corroboration, contradiction,
  context-explained contradiction, and a failure case) are documented and
  reproducible in the Streamlit "Four Required Cases" tab, using the
  Delhivery prospectus/annual-report/earnings-deck trio and the
  Economic-Survey/RBI/IMF trio from the starter dataset.
