import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { ButtonSpinner, SkeletonCards } from "../components/Loading";
import { EmptyState, PageHeader, spotlightMove, useToast } from "../components/ui";
import type { Target, User } from "../types";

export function TargetsPage() {
  const toast = useToast();
  const [targets, setTargets] = useState<Target[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [pdb, setPdb] = useState("");
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  useEffect(() => {
    Promise.all([api<Target[]>("/api/targets"), api<User>("/api/auth/me")])
      .then(([t, u]) => {
        setTargets(t);
        setUser(u);
      })
      .finally(() => setLoading(false));
  }, []);
  async function add(e: FormEvent) {
    e.preventDefault();
    setAdding(true);
    try {
      const t = await api<Target>("/api/targets", { method: "POST", body: JSON.stringify({ pdb_id: pdb }) });
      setTargets((prev) => [...prev, t]);
      setPdb("");
      toast.push({ kind: "ok", title: "Target added", detail: t.name || pdb });
    } finally {
      setAdding(false);
    }
  }
  return (
    <div>
      <PageHeader
        kicker="Aging proteins"
        title="Aging-related targets"
        subtitle="Catalog seeded with mTOR, SIRT1, AMPK, NAD-related enzymes, and FOXO3 (AlphaFold-flagged)."
      />
      {user?.role === "admin" && (
        <form className="card" onSubmit={add} style={{ marginBottom: 16 }}>
          <h2>Add by PDB ID</h2>
          <div className="row">
            <input value={pdb} onChange={(e) => setPdb(e.target.value)} placeholder="4JSV" />
            <button type="submit" disabled={adding || !pdb}>
              {adding && <ButtonSpinner />}
              Fetch from RCSB
            </button>
          </div>
        </form>
      )}
      {loading ? (
        <SkeletonCards count={4} />
      ) : targets.length === 0 ? (
        <EmptyState title="No targets" detail="The catalog is empty. Admins can fetch a structure by PDB ID." />
      ) : (
        <div className="grid grid-2 stagger">
          {targets.map((t) => (
            <div key={t.id} className="card interactive" onMouseMove={spotlightMove}>
              <h3>{t.name}</h3>
              <p>{t.description}</p>
              <div className="chip-row">
                <span className="badge">{t.pathway}</span>
                <span className={`badge ${t.structure_kind === "alphafold" ? "warn" : "ok"}`}>{t.structure_kind}</span>
                {t.pdb_id && <span className="badge">PDB {t.pdb_id}</span>}
              </div>
              <p className="muted" style={{ marginTop: 10, marginBottom: 0 }}>
                Box {t.size_x}³ Å @ ({t.center_x}, {t.center_y}, {t.center_z}) · UniProt {t.uniprot || "—"}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
