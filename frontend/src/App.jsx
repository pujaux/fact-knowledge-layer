import { useEffect, useState, useCallback } from "react";
import { api } from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import GlowBackground from "./components/GlowBackground.jsx";
import FactsTable from "./components/FactsTable.jsx";
import RelationshipsPanel from "./components/RelationshipsPanel.jsx";
import FourCasesGuide from "./components/FourCasesGuide.jsx";
import "./App.css";

const TABS = ["Facts", "Relationships", "Four Required Cases"];

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [facts, setFacts] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [relationFilter, setRelationFilter] = useState("all");
  const [activeTab, setActiveTab] = useState("Facts");
  const [busy, setBusy] = useState(false);
  const [statusLine, setStatusLine] = useState("");

  const refreshAll = useCallback(async () => {
    const [docs, f] = await Promise.all([api.documents(), api.facts()]);
    setDocuments(docs);
    setFacts(f);
  }, []);

  const refreshRelationships = useCallback(async (filter) => {
    const r = await api.relationships(filter);
    setRelationships(r);
  }, []);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    refreshRelationships(relationFilter);
  }, [relationFilter, refreshRelationships]);

  async function handleUpload(file) {
    setBusy(true);
    setStatusLine(`Extracting facts from ${file.name} with Groq…`);
    try {
      await api.upload(file);
      await refreshAll();
      await refreshRelationships(relationFilter);
      setStatusLine("");
    } catch (e) {
      setStatusLine(`Failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleRebuild() {
    setBusy(true);
    setStatusLine("Re-scanning facts for cross-document relationships…");
    try {
      await api.rebuildRelationships();
      await refreshRelationships(relationFilter);
      setStatusLine("");
    } catch (e) {
      setStatusLine(`Failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  const verifiedCount = facts.filter((f) => f.quote_verified).length;

  return (
    <div className="app">
      <GlowBackground />
      <Sidebar
        documents={documents}
        onUpload={handleUpload}
        onRebuild={handleRebuild}
        busy={busy}
        statusLine={statusLine}
      />

      <main className="main">
        <header className="hero">
          <h1 className="hero__title">Fact Knowledge Layer</h1>
          <p className="hero__stat">
            <span className="hero__number">{facts.length}</span>
            <span className="hero__label">
              facts grounded across {documents.length} document{documents.length === 1 ? "" : "s"}
              {facts.length > 0 && (
                <span className="hero__sub"> · {verifiedCount} quote-verified</span>
              )}
            </span>
          </p>
        </header>

        <nav className="tabbar">
          {TABS.map((tab) => (
            <button
              key={tab}
              className={`tabbar__tab ${activeTab === tab ? "tabbar__tab--active" : ""}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </nav>

        <div className="panel">
          {activeTab === "Facts" && <FactsTable facts={facts} />}
          {activeTab === "Relationships" && (
            <RelationshipsPanel
              relationships={relationships}
              filter={relationFilter}
              onFilterChange={setRelationFilter}
            />
          )}
          {activeTab === "Four Required Cases" && <FourCasesGuide />}
        </div>
      </main>
    </div>
  );
}
