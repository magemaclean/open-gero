import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, depictUrl, downloadExport } from "../api";
import { IconDownload, IconUpload } from "../components/icons";
import { ButtonSpinner, SkeletonTable } from "../components/Loading";
import { DropZone, EmptyState, PageHeader, useToast } from "../components/ui";
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
      <p style={{ marginBottom: 0 }}>{text}</p>
    </div>
  );
}

export function LibraryPage() {
  const { projectId } = useParams();
  const toast = useToast();
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
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [view, setView] = useState<"table" | "cards">("table");

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
    load()
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [projectId]);

  async function onImport(e: FormEvent) {
    e.preventDefault();
    setImporting(true);
    try {
      const fd = new FormData();
      if (file) fd.append("file", file);
      else fd.append("text", text);
      fd.append("fmt", file?.name.endsWith(".csv") ? "csv" : file?.name.endsWith(".sdf") ? "sdf" : "smiles");
      const result = await api<ImportReport>(`/api/projects/${projectId}/molecules/import`, {
        method: "POST",
        body: fd,
      });
      setReport(result);
      toast.push({
        kind: result.rejected ? "warn" : "ok",
        title: "Import finished",
        detail: `Accepted ${result.accepted}, merged ${result.duplicates_merged}, rejected ${result.rejected}.`,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  }

  return (
    <div>
      <PageHeader
        kicker="Compound library"
        title={project?.name || "Library"}
        subtitle={project?.description || "Import, filter, and export candidates."}
        actions={
          <div className="tabs" role="tablist">
            <button type="button" className={`tab${view === "table" ? " active" : ""}`} onClick={() => setView("table")}>
              Table
            </button>
            <button type="button" className={`tab${view === "cards" ? " active" : ""}`} onClick={() => setView("cards")}>
              Cards
            </button>
          </div>
        }
      />
      {error && <div className="error" style={{ marginBottom: 12 }}>{error}</div>}
      <div className="grid grid-2">
        <form className="card" onSubmit={onImport}>
          <h2>Import SMILES / CSV / SDF</h2>
          <p className="muted">Up to 50,000 rows. Server re-validates with RDKit, canonicalizes, and merges InChIKey duplicates.</p>
          <textarea rows={5} value={text} onChange={(e) => setText(e.target.value)} />
          <div style={{ margin: "0.7rem 0" }}>
            <DropZone onFile={setFile}>
              <IconUpload />
              <div>
                <strong>{file ? file.name : "Drop a file or browse"}</strong>
                <div className="muted">.smi · .csv · .sdf · .txt</div>
              </div>
              <input
                type="file"
                accept=".smi,.smiles,.csv,.sdf,.sd,.txt"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                style={{ marginTop: 8 }}
              />
            </DropZone>
          </div>
          <button type="submit" disabled={importing}>
            {importing && <ButtonSpinner />}
            {importing ? "Importing structures…" : "Import"}
          </button>
          {report && (
            <p className="muted" style={{ marginTop: 8, marginBottom: 0 }}>
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
              <IconDownload size={16} /> Export CSV
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => downloadExport(projectId!, { format: "sdf" }, "opengero-library.sdf")}
            >
              <IconDownload size={16} /> Export SDF
            </button>
          </div>
        </div>
      </div>
      <MethodsCard projectId={projectId!} />
      {loading ? (
        <div style={{ marginTop: 16 }}>
          <SkeletonTable />
        </div>
      ) : mols.length === 0 ? (
        <div style={{ marginTop: 16 }}>
          <EmptyState title="Library is empty" detail="Import SMILES, CSV, or SDF to populate this project." />
        </div>
      ) : view === "cards" ? (
        <div className="grid grid-3 stagger" style={{ marginTop: 16 }}>
          {mols.map((m) => (
            <Link key={m.id} to={`/projects/${projectId}/molecules/${m.id}`} className="card interactive linkish">
              <div className="mol-thumb">
                <img src={depictUrl(m.canonical_smiles, 200, 140)} alt="" />
              </div>
              <h3 style={{ marginTop: 10 }}>{m.name || "unnamed"}</h3>
              <div className="mono muted">{m.inchikey}</div>
              <div className="chip-row" style={{ marginTop: 8 }}>
                <span className="badge">{m.properties?.mw?.toFixed(1)} MW</span>
                <span className={`badge ${m.properties?.lipinski_pass ? "ok" : "warn"}`}>
                  {m.properties?.lipinski_pass ? "Lipinski" : "flag"}
                </span>
              </div>
            </Link>
          ))}
        </div>
      ) : (
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
                    <div className="mol-thumb" style={{ minHeight: 0, width: 140 }}>
                      <img src={depictUrl(m.canonical_smiles, 140, 100)} alt="" width={140} height={100} />
                    </div>
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
      )}
    </div>
  );
}
