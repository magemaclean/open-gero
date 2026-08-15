import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, depictUrl } from "../api";
import { PageLoader } from "../components/Loading";
import { Gauge, PageHeader } from "../components/ui";
import type { Job, Molecule } from "../types";

export function MoleculePage() {
  const { projectId, moleculeId } = useParams();
  const [mol, setMol] = useState<Molecule | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  useEffect(() => {
    api<Molecule>(`/api/projects/${projectId}/molecules/${moleculeId}`).then(setMol);
    api<Job[]>(`/api/projects/${projectId}/jobs`).then(setJobs);
  }, [projectId, moleculeId]);
  if (!mol) return <PageLoader label="Loading molecule…" />;
  return (
    <div>
      <PageHeader kicker="Molecule dossier" title={mol.name || "Molecule"} subtitle={<span className="mono">{mol.canonical_smiles}</span>} />
      <div className="grid grid-2">
        <div className="card mol-thumb" style={{ minHeight: 280 }}>
          <img src={depictUrl(mol.canonical_smiles, 360, 260)} alt="" />
        </div>
        <div className="card">
          <h2>Provenance</h2>
          <p>
            InChIKey <span className="mono">{mol.inchikey}</span>
          </p>
          <p>
            Source {mol.source} · formula {mol.formula}
          </p>
          {mol.properties && (
            <div className="gauge-grid" style={{ margin: "12px 0" }}>
              <Gauge label="MW" value={mol.properties.mw ?? 0} max={500} />
              <Gauge label="logP" value={mol.properties.logp ?? 0} max={5} />
              <Gauge label="TPSA" value={mol.properties.tpsa ?? 0} max={140} />
              <Gauge label="QED" value={mol.properties.qed ?? 0} max={1} />
            </div>
          )}
          <h3>Computed properties</h3>
          <table>
            <tbody>
              {mol.properties &&
                Object.entries(mol.properties).map(([k, v]) => (
                  <tr key={k}>
                    <th>{k}</th>
                    <td className="mono">{String(v)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h2>Job history</h2>
        {jobs.length === 0 && <p className="muted">No jobs in this project yet.</p>}
        <ul>
          {jobs.map((j) => (
            <li key={j.id}>
              <Link to={`/projects/${projectId}/jobs/${j.id}`}>
                {j.type} · {j.status}
              </Link>
              {j.cached && <span className="badge">cached</span>}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
