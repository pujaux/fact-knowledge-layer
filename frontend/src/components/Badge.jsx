import "./Badge.css";

const RELATION_LABEL = {
  corroborate: "Corroborates",
  contradict: "Contradicts",
  reconcilable: "Reconciled by context",
  unrelated: "Unrelated",
};

export default function Badge({ relation }) {
  return (
    <span className={`badge badge--${relation}`}>
      <span className="badge__dot" aria-hidden="true" />
      {RELATION_LABEL[relation] || relation}
    </span>
  );
}
