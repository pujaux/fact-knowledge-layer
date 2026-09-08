import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Fact Knowledge Layer", layout="wide")
st.title("📄 Fact Knowledge Layer")
st.caption("Upload PDFs. Every fact is grounded in a quote + page. Groq classifies how facts across documents relate.")

# --- Upload ---
with st.sidebar:
    st.header("Upload a PDF")
    uploaded = st.file_uploader("Choose a PDF", type=["pdf"])
    if uploaded and st.button("Process PDF"):
        with st.spinner("Extracting facts with Groq... this calls the API once per page-chunk."):
            resp = requests.post(
                f"{API_BASE}/upload",
                files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
            )
        if resp.ok:
            st.success(resp.json())
        else:
            st.error(resp.text)

    st.divider()
    if st.button("🔁 Re-run relationship discovery"):
        with st.spinner("Re-scanning all facts for cross-document relationships..."):
            resp = requests.post(f"{API_BASE}/relationships/rebuild")
        st.success(resp.json())

    st.divider()
    docs = requests.get(f"{API_BASE}/documents").json()
    st.subheader("Documents ingested")
    for d in docs:
        st.write(f"- {d['filename']} {'✅' if d['processed'] else '⏳'}")

tab_facts, tab_relations, tab_cases = st.tabs(["All Facts", "Relationships", "Four Required Cases"])

with tab_facts:
    facts = requests.get(f"{API_BASE}/facts").json()
    unverified = [f for f in facts if not f.get("quote_verified")]
    st.write(f"{len(facts)} facts extracted so far"
             + (f" — ⚠️ {len(unverified)} have a quote that couldn't be verified verbatim on the page" if unverified else ""))
    st.dataframe(
        [{"doc": f["doc_name"], "page": f["page"], "entity": f["entity"], "metric": f["metric"],
          "value": f["value"], "unit": f["unit"], "period": f["period"], "scope": f["scope"],
          "quote": f["quote"], "verified": "✅" if f.get("quote_verified") else "⚠️ unverified"}
         for f in facts],
        use_container_width=True,
    )

with tab_relations:
    relation_filter = st.selectbox("Filter", ["all", "corroborate", "contradict", "reconcilable"])
    rels = requests.get(
        f"{API_BASE}/relationships",
        params={} if relation_filter == "all" else {"relation": relation_filter},
    ).json()
    st.write(f"{len(rels)} relationships found")
    for r in rels:
        badge = {"corroborate": "🟢", "contradict": "🔴", "reconcilable": "🟡"}.get(r["relation"], "⚪")
        with st.expander(f"{badge} {r['relation'].upper()} — {r['a_metric']} vs {r['b_metric']} (sim {r['similarity']:.2f})"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**{r['a_doc']}**, page {r['a_page']}")
                st.write(f"{r['a_entity']} · {r['a_metric']} = {r['a_value']} {r['a_unit'] or ''} ({r['a_period']})")
                st.info(f"“{r['a_quote']}”")
            with col2:
                st.markdown(f"**{r['b_doc']}**, page {r['b_page']}")
                st.write(f"{r['b_entity']} · {r['b_metric']} = {r['b_value']} {r['b_unit'] or ''} ({r['b_period']})")
                st.info(f"“{r['b_quote']}”")
            st.markdown(f"**Groq's reasoning:** {r['explanation']}")
            st.caption(f"confidence: {r['confidence']}")

with tab_cases:
    st.markdown("""
    Use this tab as your demo script. Pull one example of each into your video:

    1. **Corroborated fact** — filter Relationships to `corroborate`, pick a pair where two documents
       state the same figure in different words.
    2. **Genuine contradiction** — filter to `contradict`.
    3. **Context-explained contradiction** — filter to `reconcilable` (e.g. standalone vs consolidated
       revenue, or different fiscal years).
    4. **Extraction/reasoning failure** — scroll the All Facts tab for a row where the quote doesn't
       actually support the value, or a relationship where Groq's explanation is wrong/unconvincing.
       Screenshot it and explain what you'd fix (e.g. better page-boundary handling, unit normalization).
    """)
