import { useRef, useState } from "react";
import "./Sidebar.css";

export default function Sidebar({ documents, onUpload, onRebuild, busy, statusLine }) {
  const fileInputRef = useRef(null);
  const [pendingFile, setPendingFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  function handleFiles(fileList) {
    const file = fileList?.[0];
    if (file && file.type === "application/pdf") setPendingFile(file);
  }

  return (
    <aside className="sidebar">
      <div className="sidebar__section">
        <h2 className="sidebar__title">Upload a PDF</h2>

        <div
          className={`dropzone ${dragOver ? "dropzone--active" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleFiles(e.dataTransfer.files);
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            hidden
            onChange={(e) => handleFiles(e.target.files)}
          />
          {pendingFile ? (
            <div className="dropzone__file">
              <span className="dropzone__filename">{pendingFile.name}</span>
              <span className="dropzone__filesize">
                {(pendingFile.size / (1024 * 1024)).toFixed(1)} MB
              </span>
            </div>
          ) : (
            <>
              <span className="dropzone__label">Drop a PDF here, or click to choose</span>
              <span className="dropzone__hint">Facts are extracted per page-chunk</span>
            </>
          )}
        </div>

        <button
          className="btn btn--ember"
          disabled={!pendingFile || busy}
          onClick={async () => {
            await onUpload(pendingFile);
            setPendingFile(null);
          }}
        >
          {busy ? "Processing…" : "Process PDF"}
        </button>

        {busy && statusLine && <p className="sidebar__status">{statusLine}</p>}
      </div>

      <div className="sidebar__divider" />

      <div className="sidebar__section">
        <button className="btn btn--ghost" onClick={onRebuild} disabled={busy}>
          Re-run relationship discovery
        </button>
      </div>

      <div className="sidebar__divider" />

      <div className="sidebar__section sidebar__section--grow">
        <h2 className="sidebar__title">Documents ingested</h2>
        {documents.length === 0 ? (
          <p className="sidebar__empty">Nothing uploaded yet.</p>
        ) : (
          <ul className="doc-list">
            {documents.map((d) => (
              <li key={d.id} className="doc-list__item">
                <span
                  className={`doc-list__dot ${d.processed ? "doc-list__dot--lit" : ""}`}
                  aria-hidden="true"
                />
                <span className="doc-list__name">{d.filename}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
