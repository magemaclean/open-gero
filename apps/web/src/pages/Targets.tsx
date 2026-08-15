import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { Target, User } from "../types";

export function TargetsPage() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [pdb, setPdb] = useState("");
  useEffect(() => {
    api<Target[]>("/api/targets").then(setTargets);
    api<User>("/api/auth/me").then(setUser);
  }, []);
  async function add(e: FormEvent) {
    e.preventDefault();
    const t = await api<Target>("/api/targets", { method: "POST", body: JSON.stringify({ pdb_id: pdb }) });
    setTargets((prev) => [...prev, t]);
    setPdb("");
  }
  return (
    <div>
      <h1>Aging-related targets</h1>
      <p>Catalog seeded with mTOR, SIRT1, AMPK, NAD-related enzymes, and FOXO3 (AlphaFold-flagged).</p>
      {user?.role === "admin" && (
        <form className="card" onSubmit={add} style={{ marginBottom: 16 }}>
          <h2>Add by PDB ID</h2>
          <div className="row">
            <input value={pdb} onChange={(e) => setPdb(e.target.value)} placeholder="4JSV" />
            <button type="submit">Fetch from RCSB</button>
          </div>
        </form>
      )}
      <div className="grid grid-2">
        {targets.map((t) => (
          <div key={t.id} className="card">
            <h3>{t.name}</h3>
            <p>{t.description}</p>
            <div>
              <span className="badge">{t.pathway}</span>{" "}
              <span className={`badge ${t.structure_kind === "alphafold" ? "warn" : "ok"}`}>{t.structure_kind}</span>{" "}
              {t.pdb_id && <span className="badge">PDB {t.pdb_id}</span>}
            </div>
            <p className="muted">
              Box {t.size_x}³ Å @ ({t.center_x}, {t.center_y}, {t.center_z}) · UniProt {t.uniprot || "—"}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
