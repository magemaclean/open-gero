import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, depictUrl, downloadExport } from "../api";
import type { ImportReport, Molecule, Project } from "../types";

function MethodsCard({ projectId }: { projectId: string }) {
  const [text, setText] = useState("");
  useEffect(() => {
    api<{ text: string }>(`/api/projects/${projectId}/methods`)
      .then((m) => setText(m.text))
      .catch(() => setText(""));
  }, [projectId]);
  if (!text) return null;
  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h2>Methods paragraph</h2>
      <p>{text}</p>
    </div>
  );
}

export function LibraryPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [mols, setMols] = useState<Molecule[]>([]);
  const [q, setQ] = useState("");
  const [mwMax, setMwMax] = useState("");
  const [tpsaMax, setTpsaMax] = useState("");
  const [lipinski, setLipinski] = useState(false);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [text, setText] = useState("CCO ethanol\nCC(=O)Oc1ccccc1C(=O)O aspirin\n");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");

  async function load() {
    if (!projectId) return;
    setProject(await api<Project>(`/api/projects/${projectId}`));
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (mwMax) params.set("mw_max", mwMax);
    if (tpsaMax) params.set("tpsa_max", tpsaMax);
    if (lipinski) params.set("lipinski", "true");
    setMols(await api<Molecule[]>(`/api/projects/${projectId}/molecules?${params}`));
  }
  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, [projectId]);

  async function onImport(e: FormEvent) {
    e.preventDefault();
    const fd = new FormData();
    if (file) fd.append("file", file);
    else fd.append("text", text);
    fd.append("fmt", file?.name.endsWith(".csv") ? "csv" : file?.name.endsWith(".sdf") ? "sdf" : "smiles");
    const result = await api<ImportReport>(`/api/projects/${projectId}/molecules/import`, {
      method: "POST",
      body: fd,
    });
    setReport(result);
    await load();
  }

  return (
    <div>
      <h1>{project?.name || "Library"}</h1>
      <p>{project?.description}</p>
      {error && <div className="error">{error}</div>}
      <div className="grid grid-2">
        <form className="card" onSubmit={onImport}>
          <h2>Import SMILES / CSV / SDF</h2>
          <p className="muted">Up to 50,000 rows. Server re-validates with RDKit, canonicalizes, and merges InChIKey duplicates.</p>
          <textarea rows={5} value={text} onChange={(e) => setText(e.target.value)} />
          <div style={{ margin: "0.6rem 0" }}>
            <input type="file" accept=".smi,.smiles,.csv,.sdf,.sd,.txt" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </div>
          <button type="submit">Import</button>
          {report && (
            <p className="muted" style={{ marginTop: 8 }}>
              Accepted {report.accepted}, merged {report.duplicates_merged}, rejected {report.rejected}.
              {report.errors[0] && ` First error: ${report.errors[0].error}`}
            </p>
          )}
        </form>
        <div className="card">
          <h2>Filter builder</h2>
          <div className="filters">
            <div>
              <label>Text</label>
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="name / SMILES / InChIKey" />
            </div>
            <div>
              <label>MW ≤</label>
              <input value={mwMax} onChange={(e) => setMwMax(e.target.value)} placeholder="500" />
            </div>
            <div>
              <label>TPSA ≤</label>
              <input value={tpsaMax} onChange={(e) => setTpsaMax(e.target.value)} placeholder="140" />
            </div>
            <div>
              <label>Lipinski</label>
              <select value={lipinski ? "yes" : ""} onChange={(e) => setLipinski(e.target.value === "yes")}>
                <option value="">Any</option>
                <option value="yes">Pass</option>
              </select>
            </div>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button type="button" onClick={() => load()}>
              Apply filters
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => downloadExport(projectId!, { format: "csv" }, "opengero-library.csv")}
            >
              Export CSV
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => downloadExport(projectId!, { format: "sdf" }, "opengero-library.sdf")}
            >
              Export SDF
            </button>
          </div>
        </div>
      </div>
      <MethodsCard projectId={projectId!} />
      <div className="table-wrap" style={{ marginTop: 16 }}>
        <table>
          <thead>
            <tr>
              <th>Structure</th>
              <th>Name</th>
              <th>MW</th>
              <th>logP</th>
              <th>TPSA</th>
              <th>Lipinski</th>
              <th>Veber</th>
            </tr>
          </thead>
          <tbody>
            {mols.map((m) => (
              <tr key={m.id}>
                <td>
                  <img src={depictUrl(m.canonical_smiles, 140, 100)} alt="" width={140} height={100} />
                </td>
                <td>
                  <Link to={`/projects/${projectId}/molecules/${m.id}`}>{m.name || "unnamed"}</Link>
                  <div className="mono muted">{m.inchikey}</div>
                </td>
                <td>{m.properties?.mw?.toFixed(1)}</td>
                <td>{m.properties?.logp?.toFixed(2)}</td>
                <td>{m.properties?.tpsa?.toFixed(1)}</td>
                <td>
                  <span className={`badge ${m.properties?.lipinski_pass ? "ok" : "warn"}`}>
                    {m.properties?.lipinski_pass ? "pass" : "flag"}
                  </span>
                </td>
                <td>
                  <span className={`badge ${m.properties?.veber_pass ? "ok" : "warn"}`}>
                    {m.properties?.veber_pass ? "pass" : "flag"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
