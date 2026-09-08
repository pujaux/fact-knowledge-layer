from app import db
from app.pdf_extract import extract_pages, chunk_pages
from app.llm_client import extract_facts, classify_relationship
from app.embeddings import embed_facts, top_k_candidate_pairs
from app.grounding import verify_quote
from app.config import TOP_K_CANDIDATES_PER_FACT, SIMILARITY_THRESHOLD


def process_document(pdf_path: str, filename: str) -> dict:
    """Full ingestion for one PDF: extract text -> chunk -> Groq extracts facts -> store."""
    doc_id = db.add_document(filename)

    pages = extract_pages(pdf_path)
    chunks = chunk_pages(pages)

    total_facts = 0
    unverified_facts = 0
    for chunk in chunks:
        raw_facts = extract_facts(chunk["text"], filename)
        # attach a sensible default page if the model didn't set one
        default_page = chunk["pages"][0] if chunk["pages"] else None
        for f in raw_facts:
            if not f.get("page"):
                f["page"] = default_page
            # Ground every fact: confirm its quote is a real, literal substring
            # of the chunk it claims to come from, rather than trusting the
            # model's claim at face value. A fact whose quote doesn't verify
            # is still kept (dropping it silently would just hide the
            # failure) but flagged so the UI can surface it -- this is also
            # good raw material for the "extraction/reasoning failure" case
            # the assignment asks for.
            f["quote_verified"] = verify_quote(f.get("quote", ""), chunk["text"])
            if not f["quote_verified"]:
                unverified_facts += 1
        db.add_facts(doc_id, filename, raw_facts)
        total_facts += len(raw_facts)

    db.mark_processed(doc_id)
    return {
        "doc_id": doc_id,
        "filename": filename,
        "chunks": len(chunks),
        "facts_extracted": total_facts,
        "facts_with_unverified_quotes": unverified_facts,
    }


def build_relationships() -> dict:
    """Finds cross-document candidate pairs locally via embeddings (free),
    then calls Groq only on candidates that haven't already been classified.

    Every classified pair (including 'unrelated' ones) is stored, and
    `db.relationship_exists` is checked before spending a Groq call -- so
    re-running this after a new upload only asks Groq about genuinely new
    pairs, never pairs it already judged in a previous run. This is what
    makes adding a new document to the knowledge layer incremental rather
    than a full recompute of every relationship from scratch.
    """
    facts = db.get_all_facts()
    if len(facts) < 2:
        return {"pairs_checked": 0, "pairs_skipped_already_known": 0, "relationships_found": 0}

    embeddings = embed_facts(facts)
    candidates = top_k_candidate_pairs(
        facts, embeddings, k=TOP_K_CANDIDATES_PER_FACT, threshold=SIMILARITY_THRESHOLD
    )

    found = 0
    skipped = 0
    for i, j, sim in candidates:
        fact_a, fact_b = facts[i], facts[j]
        if db.relationship_exists(fact_a["id"], fact_b["id"]):
            skipped += 1
            continue
        result = classify_relationship(fact_a, fact_b)
        relation = result.get("relation", "unrelated")
        db.add_relationship(
            fact_a["id"], fact_b["id"], relation,
            result.get("confidence", 0), result.get("explanation", ""), sim,
        )
        if relation != "unrelated":
            found += 1

    return {
        "pairs_checked": len(candidates),
        "pairs_skipped_already_known": skipped,
        "relationships_found": found,
    }
