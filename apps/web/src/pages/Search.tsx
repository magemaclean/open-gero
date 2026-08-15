import { FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, depictUrl } from "../api";
import type { DatasetHit, Molecule } from "../types";

export function SearchPage() {
  const { projectId } = useParams();
  const [smiles, setSmiles] = useState("Oc1cc(O)c2c(c1)oc(-c1ccc(O)c(O)c1)c(O)c2=O");
  const [threshold, setThreshold] = useState(0.35);
  const [smarts, setSmarts] = useState("c1ccccc1O");
  const [datasetHits, setDatasetHits] = useState<DatasetHit[]>([]);
  const [libHits, setLibHits] = useState<Molecule[]>([]);
  const [subHits, setSubHits] = useState<Molecule[]>([]);
  const [datasetMeta, setDatasetMeta] = useState("");
  const [savedName, setSavedName] = useState("");

  async function sim(e: FormEvent) {
    e.preventDefault();
    const ds = await api<{ dataset: { name: string; version: string }; hits: DatasetHit[] }>(
      `/api/projects/${projectId}/search/similarity`,
      {
        method: "POST",
        body: JSON.stringify({ smiles, threshold, against: "dataset", dataset_slug: "geroprotectors" }),
      },
    );
    setDatasetHits(ds.hits);
    setDatasetMeta(`${ds.dataset.name} ${ds.dataset.version}`);
    const lib = await api<{ hits: Molecule[] }>(`/api/projects/${projectId}/search/similarity`, {
      method: "POST",
      body: JSON.stringify({ smiles, threshold, against: "library" }),
    });
    setLibHits(lib.hits);
  }

  async function sub(e: FormEvent) {
    e.preventDefault();
    const resp = await api<{ hits: Molecule[] }>(`/api/projects/${projectId}/search/substructure`, {
      method: "POST",
      body: JSON.stringify({ smarts }),
    });
    setSubHits(resp.hits);
  }

  async function save() {
    await api(`/api/projects/${projectId}/searches`, {
      method: "POST",
      body: JSON.stringify({
        name: savedName || "Untitled search",
        kind: "similarity",
        params: { smiles, threshold },
      }),
    });
    setSavedName("");
  }

  return (
    <div>
      <h1>Search</h1>
      <p>Tanimoto similarity on Morgan fingerprints (radius 2, 2048 bits) and SMARTS substructure matching.</p>
      <div className="grid grid-2">
        <form className="card" onSubmit={sim}>
          <h2>Similarity vs geroprotectors</h2>
          <label>Query SMILES</label>
          <textarea rows={3} value={smiles} onChange={(e) => setSmiles(e.target.value)} />
          <label>Tanimoto threshold</label>
          <input type="number" step="0.05" min="0" max="1" value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
          <div className="row" style={{ marginTop: 8 }}>
            <button type="submit">Search</button>
            <input placeholder="Save as…" value={savedName} onChange={(e) => setSavedName(e.target.value)} />
            <button type="button" className="secondary" onClick={save}>
              Save search
            </button>
          </div>
        </form>
        <form className="card" onSubmit={sub}>
          <h2>Substructure (SMARTS)</h2>
          <label>Query</label>
          <input value={smarts} onChange={(e) => setSmarts(e.target.value)} />
          <button type="submit" style={{ marginTop: 8 }}>
            Find matches
          </button>
        </form>
      </div>
      {datasetMeta && <p className="muted">Reference set: {datasetMeta}</p>}
      <h2>Geroprotector hits</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Score</th>
              <th>Name</th>
              <th>Organism</th>
              <th>Effect</th>
              <th>Citation</th>
            </tr>
          </thead>
          <tbody>
            {datasetHits.map((h) => (
              <tr key={h.id}>
                <td className="mono">{h.tanimoto?.toFixed(3)}</td>
                <td>{h.name}</td>
                <td>{h.organism}</td>
                <td>
                  {h.effect_size}
                  <div className="muted">{h.effect_note}</div>
                </td>
                <td>
                  {h.citation}
                  {h.pmid && (
                    <>
                      {" "}
                      <a href={`https://pubmed.ncbi.nlm.nih.gov/${h.pmid}/`} target="_blank" rel="noreferrer">
                        PMID {h.pmid}
                      </a>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h2>Library hits</h2>
      <div className="grid grid-3">
        {libHits.map((m) => (
          <Link key={m.id} to={`/projects/${projectId}/molecules/${m.id}`} className="card" style={{ textDecoration: "none", color: "inherit" }}>
            <img src={depictUrl(m.canonical_smiles, 200, 130)} alt="" />
            <strong>{m.name}</strong>
            <div className="mono">{m.tanimoto?.toFixed(3)}</div>
          </Link>
        ))}
      </div>
      <h2>Substructure hits</h2>
      <ul>
        {subHits.map((m) => (
          <li key={m.id}>
            <Link to={`/projects/${projectId}/molecules/${m.id}`}>{m.name}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
