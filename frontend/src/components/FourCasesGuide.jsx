import "./FourCasesGuide.css";

const CASES = [
  {
    n: "01",
    title: "A fact corroborated across documents",
    body: "Filter Relationships to Corroborate. Pick a pair where two documents state the same underlying figure in different words — that's your grounded agreement.",
  },
  {
    n: "02",
    title: "A genuine contradiction",
    body: "Filter to Contradict. Read the explanation critically: does it hold up against both quotes, with no obvious reconciling context?",
  },
  {
    n: "03",
    title: "An apparent contradiction explained by context",
    body: "Filter to Reconciled by context — differing period, scope, or unit (standalone vs consolidated, different fiscal years) explains the surface-level conflict.",
  },
  {
    n: "04",
    title: "An extraction or reasoning failure",
    body: "Check the Facts tab for a dim, unverified dot — a quote that couldn't be matched verbatim to its source. Or a relationship whose explanation doesn't actually hold up.",
  },
];

export default function FourCasesGuide() {
  return (
    <div className="cases">
      
      {CASES.map((c) => (
        <div className="case-item" key={c.n}>
          <span className="case-item__n">{c.n}</span>
          <div>
            <h3 className="case-item__title">{c.title}</h3>
            <p className="case-item__body">{c.body}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
