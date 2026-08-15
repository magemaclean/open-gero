import { FormEvent, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, depictUrl } from "../api";
import { ButtonSpinner, PageLoader } from "../components/Loading";
import { EmptyState, PageHeader, spotlightMove, useToast } from "../components/ui";
import type { DatasetHit, Molecule, SavedSearch } from "../types";

export function SearchPage() {
  const { projectId } = useParams();
  const [params] = useSearchParams();
  const toast = useToast();
  const [tab, setTab] = useState<"similarity" | "smarts">("similarity");
  const [smiles, setSmiles] = useState(params.get("smiles") || "Oc1cc(O)c2c(c1)oc(-c1ccc(O)c(O)c1)c(O)c2=O");
  const [threshold, setThreshold] = useState(0.35);
  const [smarts, setSmarts] = useState("c1ccccc1O");
  const [datasetHits, setDatasetHits] = useState<DatasetHit[]>([]);
  const [libHits, setLibHits] = useState<Molecule[]>([]);
  const [subHits, setSubHits] = useState<Molecule[]>([]);
  const [datasetMeta, setDatasetMeta] = useState("");
  const [savedName, setSavedName] = useState("");
  const [saved, setSaved] = useState<SavedSearch[]>([]);
  const [searching, setSearching] = useState(false);
  const [didSearch, setDidSearch] = useState(false);

  async function loadSaved() {
    if (!projectId) return;
    setSaved(await api<SavedSearch[]>(`/api/projects/${projectId}/searches`));
  }
  useEffect(() => {
    loadSaved().catch(() => undefined);
  }, [projectId]);

  useEffect(() => {
    const q = params.get("smiles");
    if (q) setSmiles(q);
  }, [params]);

  async function runSimilarity(query: string, tanimoto: number) {
    setSearching(true);
    try {
      const ds = await api<{ dataset: { name: string; version: string }; hits: DatasetHit[] }>(
        `/api/projects/${projectId}/search/similarity`,
        {
          method: "POST",
          body: JSON.stringify({ smiles: query, threshold: tanimoto, against: "dataset", dataset_slug: "geroprotectors" }),
        },
      );
      setDatasetHits(ds.hits);
      setDatasetMeta(`${ds.dataset.name} ${ds.dataset.version}`);
      const lib = await api<{ hits: Molecule[] }>(`/api/projects/${projectId}/search/similarity`, {
        method: "POST",
        body: JSON.stringify({ smiles: query, threshold: tanimoto, against: "library" }),
      });
      setLibHits(lib.hits);
      setDidSearch(true);
    } finally {
      setSearching(false);
    }
  }

  async function sim(e: FormEvent) {
    e.preventDefault();
    await runSimilarity(smiles, threshold);
  }

  async function runSubstructure(query: string) {
    setSearching(true);
    try {
      const resp = await api<{ hits: Molecule[] }>(`/api/projects/${projectId}/search/substructure`, {
        method: "POST",
        body: JSON.stringify({ smarts: query }),
      });
      setSubHits(resp.hits);
      setDidSearch(true);
    } finally {
      setSearching(false);
    }
  }

  async function sub(e: FormEvent) {
    e.preventDefault();
    await runSubstructure(smarts);
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
    toast.push({ kind: "ok", title: "Search saved", detail: savedName || "Untitled search" });
    setSavedName("");
    await loadSaved();
  }

  function recall(s: SavedSearch) {
    const p = s.params || {};
    if (typeof p.smarts === "string") {
      setSmarts(p.smarts);
      setTab("smarts");
      void runSubstructure(p.smarts);
      return;
    }
    if (typeof p.smiles === "string") setSmiles(p.smiles);
    if (typeof p.threshold === "number") setThreshold(p.threshold);
    setTab("similarity");
    const query = typeof p.smiles === "string" ? p.smiles : smiles;
    const tanimoto = typeof p.threshold === "number" ? p.threshold : threshold;
    void runSimilarity(query, tanimoto);
  }

  return (
    <div>
      <PageHeader
        kicker="Chemical search"
        title="Search"
        subtitle="Tanimoto similarity on Morgan fingerprints (radius 2, 2048 bits) and SMARTS substructure matching."
        actions={
          <div className="tabs">
            <button type="button" className={`tab${tab === "similarity" ? " active" : ""}`} onClick={() => setTab("similarity")}>
              Similarity
            </button>
            <button type="button" className={`tab${tab === "smarts" ? " active" : ""}`} onClick={() => setTab("smarts")}>
              Substructure
            </button>
          </div>
        }
      />
      {tab === "similarity" ? (
        <form className="card" onSubmit={sim}>
          <h2>Similarity vs geroprotectors</h2>
          <label>Query SMILES</label>
          <textarea rows={3} value={smiles} onChange={(e) => setSmiles(e.target.value)} className="mono" />
          <label>Tanimoto threshold · {threshold.toFixed(2)}</label>
          <input type="range" min="0" max="1" step="0.05" value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
          <div className="row" style={{ marginTop: 8 }}>
            <button type="submit" disabled={searching}>
              {searching && <ButtonSpinner />}
              Search
            </button>
            <input placeholder="Save as…" value={savedName} onChange={(e) => setSavedName(e.target.value)} />
            <button type="button" className="secondary" onClick={save}>
              Save search
            </button>
          </div>
          {saved.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <label>Saved searches</label>
              <div className="chip-row">
                {saved.map((s) => (
                  <button key={s.id} type="button" className="chip" onClick={() => recall(s)}>
                    {s.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </form>
      ) : (
        <form className="card" onSubmit={sub}>
          <h2>Substructure (SMARTS)</h2>
          <label>Query</label>
          <input value={smarts} onChange={(e) => setSmarts(e.target.value)} className="mono" />
          <button type="submit" style={{ marginTop: 8 }} disabled={searching}>
            {searching && <ButtonSpinner />}
            Find matches
          </button>
        </form>
      )}

      {searching && <PageLoader label="Scoring fingerprints…" />}

      {!searching && tab === "similarity" && (
        <>
          {datasetMeta && <p className="muted">Reference set: {datasetMeta}</p>}
          <h2>Geroprotector hits</h2>
          {didSearch && datasetHits.length === 0 ? (
            <EmptyState title="No geroprotector hits" detail="Try lowering the Tanimoto threshold." />
          ) : (
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
                      <td>
                        <div className="mono">{h.tanimoto?.toFixed(3)}</div>
                        <div className="progress" style={{ marginTop: 6, width: 88 }}>
                          <span style={{ width: `${Math.round((h.tanimoto || 0) * 100)}%` }} />
                        </div>
                      </td>
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
          )}
          <h2 style={{ marginTop: 20 }}>Library hits</h2>
          {didSearch && libHits.length === 0 ? (
            <EmptyState title="No library hits" detail="Nothing in this project crossed the threshold." />
          ) : (
            <div className="grid grid-3 stagger">
              {libHits.map((m) => (
                <Link
                  key={m.id}
                  to={`/projects/${projectId}/molecules/${m.id}`}
                  className="card interactive linkish"
                  onMouseMove={spotlightMove}
                >
                  <div className="mol-thumb">
                    <img src={depictUrl(m.canonical_smiles, 200, 130)} alt="" />
                  </div>
                  <strong>{m.name}</strong>
                  <div className="mono">{m.tanimoto?.toFixed(3)}</div>
                  <div className="progress" style={{ marginTop: 8 }}>
                    <span style={{ width: `${Math.round((m.tanimoto || 0) * 100)}%` }} />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </>
      )}

      {!searching && tab === "smarts" && (
        <>
          <h2 style={{ marginTop: 20 }}>Substructure hits</h2>
          {didSearch && subHits.length === 0 ? (
            <EmptyState title="No SMARTS matches" detail="Adjust the query or import more structures." />
          ) : (
            <ul className="stagger">
              {subHits.map((m) => (
                <li key={m.id}>
                  <Link to={`/projects/${projectId}/molecules/${m.id}`}>{m.name}</Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
