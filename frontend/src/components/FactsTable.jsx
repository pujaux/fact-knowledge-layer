import "./FactsTable.css";

export default function FactsTable({ facts }) {
  const unverifiedCount = facts.filter((f) => !f.quote_verified).length;

  return (
    <div>
      <p className="facts-summary">
        <span className="facts-summary__count">{facts.length}</span> facts grounded so far
        {unverifiedCount > 0 && (
          <span className="facts-summary__warn">
            {" "}
            · {unverifiedCount} quote{unverifiedCount === 1 ? "" : "s"} unverified
          </span>
        )}
      </p>

      {facts.length === 0 ? (
        <div className="empty-state">
          <p>No facts yet. Upload a PDF from the sidebar to get started.</p>
        </div>
      ) : (
        <div className="facts-grid">
          {facts.map((f) => (
            <div className="fact-card" key={f.id}>
              <div className="fact-card__top">
                <span className="fact-card__entity">{f.entity}</span>
                <span
                  className={`fact-card__verify ${f.quote_verified ? "fact-card__verify--ok" : "fact-card__verify--warn"}`}
                  title={f.quote_verified ? "Quote verified against source text" : "Quote could not be verified verbatim"}
                />
              </div>
              <p className="fact-card__metric">{f.metric}</p>
              <p className="fact-card__value">
                {f.value}
                {f.unit ? <span className="fact-card__unit"> {f.unit}</span> : null}
              </p>
              {(f.period || f.scope) && (
                <p className="fact-card__meta">
                  {[f.period, f.scope].filter(Boolean).join(" · ")}
                </p>
              )}
              {f.quote && <p className="fact-card__quote">&ldquo;{f.quote}&rdquo;</p>}
              <p className="fact-card__source">
                {f.doc_name} · p.{f.page}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
