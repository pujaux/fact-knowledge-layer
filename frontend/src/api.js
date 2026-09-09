const API_BASE = "http://localhost:8000";

async function json(res) {
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const api = {
  documents: () => fetch(`${API_BASE}/documents`).then(json),
  facts: () => fetch(`${API_BASE}/facts`).then(json),
  relationships: (relation) =>
    fetch(
      `${API_BASE}/relationships${relation && relation !== "all" ? `?relation=${relation}` : ""}`
    ).then(json),
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${API_BASE}/upload`, { method: "POST", body: form }).then(json);
  },
  rebuildRelationships: () =>
    fetch(`${API_BASE}/relationships/rebuild`, { method: "POST" }).then(json),

  deleteDocument: (id) =>
    fetch(`${API_BASE}/documents/${id}`, { method: "DELETE" }).then(json),
};
