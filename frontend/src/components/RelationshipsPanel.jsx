import { useState } from "react";
import Badge from "./Badge.jsx";
import "./RelationshipsPanel.css";

const FILTERS = ["all", "corroborate", "contradict", "reconcilable"];

function EvidenceSide({ label, doc, page, entity, metric, value, unit, period, quote }) {
  return (
    <div className="evidence">
      <p className="evidence__source">
        {doc} · p.{page}
      </p>
      <p className="evidence__claim">
        {entity} · {metric} <strong>{value}</strong> {unit || ""}
        {period ? <span className="evidence__period"> ({period})</span> : null}
      </p>
      <p className="evidence__quote">&ldquo;{quote}&rdquo;</p>
    </div>
  );
}

export default function RelationshipsPanel({ relationships, filter, onFilterChange }) {
  const [openId, setOpenId] = useState(null);

  return (
    <div>
      <div className="filter-row">
        {FILTERS.map((f) => (
          <button
            key={f}
            className={`filter-chip ${filter === f ? "filter-chip--active" : ""}`}
            onClick={() => onFilterChange(f)}
          >
            {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <p className="facts-summary">
        <span className="facts-summary__count">{relationships.length}</span> relationship
        {relationships.length === 1 ? "" : "s"} found
      </p>

      {relationships.length === 0 ? (
        <div className="empty-state">
          <p>
            Nothing here yet. Relationships only form across documents — upload a second PDF and
            re-run relationship discovery.
          </p>
        </div>
      ) : (
        <div className="rel-list">
          {relationships.map((r) => {
            const isOpen = openId === r.id;
            return (
              <div className="rel-card" key={r.id}>
                <button
                  className="rel-card__header"
                  onClick={() => setOpenId(isOpen ? null : r.id)}
                  aria-expanded={isOpen}
                >
                  <Badge relation={r.relation} />
                  <span className="rel-card__title">
                    {r.a_metric} <span className="rel-card__vs">vs</span> {r.b_metric}
                  </span>
                  <span className="rel-card__sim">sim {r.similarity?.toFixed(2)}</span>
                </button>

                {isOpen && (
                  <div className="rel-card__body">
                    <div className="evidence-row">
                      <EvidenceSide
                        doc={r.a_doc}
                        page={r.a_page}
                        entity={r.a_entity}
                        metric={r.a_metric}
                        value={r.a_value}
                        unit={r.a_unit}
                        period={r.a_period}
                        quote={r.a_quote}
                      />
                      <EvidenceSide
                        doc={r.b_doc}
                        page={r.b_page}
                        entity={r.b_entity}
                        metric={r.b_metric}
                        value={r.b_value}
                        unit={r.b_unit}
                        period={r.b_period}
                        quote={r.b_quote}
                      />
                    </div>
                    <p className="rel-card__explanation">{r.explanation}</p>
                    <div className="confidence-bar">
                      <div
                        className="confidence-bar__fill"
                        style={{ width: `${Math.round((r.confidence || 0) * 100)}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
