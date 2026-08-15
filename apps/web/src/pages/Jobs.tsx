import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, depictUrl, downloadExport } from "../api";
import type { DockingResult, Job, Molecule, Target } from "../types";

export function JobsPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [mols, setMols] = useState<Molecule[]>([]);
  const [targetId, setTargetId] = useState("");
  const [exhaustiveness, setExhaustiveness] = useState(8);
  const [seed, setSeed] = useState(42);
  const [error, setError] = useState("");

  async function load() {
    setJobs(await api<Job[]>(`/api/projects/${projectId}/jobs`));
    const t = await api<Target[]>("/api/targets");
    setTargets(t);
    if (t[0] && !targetId) setTargetId(t[0].id);
    setMols(await api<Molecule[]>(`/api/projects/${projectId}/molecules`));
  }
  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, [projectId]);

  const selected = targets.find((t) => t.id === targetId);

  async function queue(e: FormEvent) {
    e.preventDefault();
    const job = await api<Job>(`/api/projects/${projectId}/jobs`, {
      method: "POST",
      body: JSON.stringify({
        type: "docking",
        target_id: targetId,
        exhaustiveness,
        seed,
        batch_size: 100,
      }),
    });
    navigate(`/projects/${projectId}/jobs/${job.id}`);
  }

  return (
    <div>
      <h1>Docking jobs</h1>
      <p>
        Scores are <strong>prioritization heuristics</strong>, not binding free energies. Identical
        molecule/target/parameter hashes return cached poses instantly.
      </p>
      {error && <div className="error">{error}</div>}
      <form className="card" onSubmit={queue}>
        <h2>Queue library × target</h2>
        <div className="filters">
          <div>
            <label>Target</label>
            <select value={targetId} onChange={(e) => setTargetId(e.target.value)}>
              {targets.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} {t.structure_kind === "alphafold" ? "(AlphaFold)" : ""}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>Exhaustiveness</label>
            <input type="number" value={exhaustiveness} onChange={(e) => setExhaustiveness(Number(e.target.value))} />
          </div>
          <div>
            <label>Seed</label>
            <input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
          </div>
          <div>
            <label>Library size</label>
            <input value={mols.length} readOnly />
          </div>
        </div>
        {selected && (
          <p className="muted">
            Default box {selected.size_x}×{selected.size_y}×{selected.size_z} Å at ({selected.center_x}, {selected.center_y}, {selected.center_z})
            {selected.pdb_id && ` · PDB ${selected.pdb_id}`}
            {selected.structure_kind === "alphafold" && " · predicted structure, treat poses cautiously"}
          </p>
        )}
        <button type="submit">Queue docking</button>
      </form>
      <div className="table-wrap" style={{ marginTop: 16 }}>
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Status</th>
              <th>Progress</th>
              <th>Cached</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id}>
                <td>
                  <Link to={`/projects/${projectId}/jobs/${j.id}`}>{j.type}</Link>
                </td>
                <td>
                  <span className={`badge ${j.status === "done" ? "ok" : j.status === "failed" ? "danger" : "warn"}`}>
                    {j.status}
                  </span>
                </td>
                <td>
                  {j.completed_items}/{j.total_items} · batches {j.batches_done}/{j.batches_total}
                </td>
                <td>{j.cached ? "yes" : "no"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function JobDetailPage() {
  const { projectId, jobId } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [results, setResults] = useState<DockingResult[]>([]);
  const [pose, setPose] = useState("");
  const [selected, setSelected] = useState<string>("");
  const viewerRef = useRef<HTMLDivElement>(null);

  async function refresh() {
    const j = await api<Job>(`/api/jobs/${jobId}`);
    setJob(j);
    if (j.status === "done" || j.completed_items > 0) {
      const rows = await api<DockingResult[]>(`/api/jobs/${jobId}/results`);
      setResults(rows);
      if (rows[0] && !selected) setSelected(rows[0].molecule_id);
    }
  }
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 1500);
    return () => clearInterval(t);
  }, [jobId]);

  useEffect(() => {
    if (!selected || !jobId) return;
    fetch(`/api/jobs/${jobId}/poses/${selected}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("opengero_token") || ""}` },
    })
      .then((r) => r.text())
      .then(setPose)
      .catch(() => setPose(""));
  }, [selected, jobId]);

  useEffect(() => {
    if (!pose || !viewerRef.current || !window.$3Dmol) return;
    const viewer = window.$3Dmol.createViewer(viewerRef.current, { backgroundColor: "0x111111" });
    viewer.clear();
    viewer.addModel(pose, pose.includes("ATOM") ? "pdb" : "sdf");
    viewer.setStyle({}, { stick: {} });
    viewer.zoomTo();
    viewer.render();
  }, [pose]);

  if (!job) return <p>Loading…</p>;
  const pct = job.total_items ? Math.round((job.completed_items / job.total_items) * 100) : 0;
  return (
    <div>
      <h1>Job {job.type}</h1>
      <p>
        Status <span className="badge">{job.status}</span>
        {job.cached && <span className="badge ok">cached</span>} · engine params hash{" "}
        <span className="mono">{job.params_hash.slice(0, 12)}</span>
      </p>
      <div className="progress" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <span style={{ width: `${pct}%` }} />
      </div>
      <p className="muted">
        {job.completed_items}/{job.total_items} molecules · {job.batches_done}/{job.batches_total} batches · {job.failed_items} failed
      </p>
      {job.error && <div className="error">{job.error}</div>}
      <div className="row">
        <button className="secondary" onClick={() => api(`/api/jobs/${job.id}/cancel`, { method: "POST" }).then(() => refresh())}>
          Cancel
        </button>
        <button
          className="secondary"
          onClick={() => downloadExport(projectId!, { format: "csv", job_id: job.id, include_docking: true }, "opengero-docking.csv")}
        >
          Export ranked CSV
        </button>
      </div>
      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Score</th>
                <th>Molecule</th>
                <th>Engine</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.id} onClick={() => setSelected(r.molecule_id)} style={{ cursor: "pointer" }}>
                  <td className="mono">{r.best_score.toFixed(3)}</td>
                  <td>
                    <img src={depictUrl(r.canonical_smiles, 90, 70)} alt="" />
                    <div>{r.molecule_name}</div>
                  </td>
                  <td>
                    {r.engine}
                    {r.cached && <div className="badge">cached</div>}
                    {r.engine.startsWith("heuristic") && <div className="badge warn">not Vina</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <div ref={viewerRef} className="viewer" />
          <p className="muted">3D pose (Mol*/3Dmol). Lower scores are better for Vina-style ranking.</p>
        </div>
      </div>
    </div>
  );
}
