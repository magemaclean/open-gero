import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, depictUrl } from "../api";
import { clientDescriptors } from "../rdkit";
import { ButtonSpinner } from "../components/Loading";
import { Gauge, PageHeader, useToast } from "../components/ui";
import type { Molecule, Properties } from "../types";

const EXAMPLES = [
  { name: "Ethanol", smiles: "CCO" },
  { name: "Resveratrol", smiles: "Oc1ccc(/C=C/c2cc(O)cc(O)c2)cc1" },
  { name: "Metformin", smiles: "CN(C)C(=N)NC(=N)N" },
  { name: "Fisetin", smiles: "O=c1c(O)c(-c2ccc(O)c(O)c2)oc2cc(O)ccc12" },
];

export function EditorPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [smiles, setSmiles] = useState("Oc1ccc(/C=C/c2cc(O)cc(O)c2)cc1");
  const [name, setName] = useState("Resveratrol");
  const [props, setProps] = useState<Properties | null>(null);
  const [source, setSource] = useState<"wasm" | "server" | "">("");
  const [error, setError] = useState("");
  const [computing, setComputing] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError("");
      setComputing(true);
      const local = await clientDescriptors(smiles);
      if (cancelled) return;
      if (local) {
        setProps(local);
        setSource("wasm");
        setComputing(false);
        return;
      }
      try {
        const remote = await api<{ properties: Properties }>("/api/chem/properties", {
          method: "POST",
          body: JSON.stringify({ smiles }),
        });
        if (!cancelled) {
          setProps(remote.properties);
          setSource("server");
        }
      } catch (e) {
        if (!cancelled) {
          setProps(null);
          setError(e instanceof Error ? e.message : "Invalid structure");
        }
      } finally {
        if (!cancelled) setComputing(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [smiles]);

  async function add(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const mol = await api<Molecule>(`/api/projects/${projectId}/molecules`, {
        method: "POST",
        body: JSON.stringify({ smiles, name }),
      });
      toast.push({ kind: "ok", title: "Added to library", detail: mol.name || name });
      navigate(`/projects/${projectId}/molecules/${mol.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add molecule");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <PageHeader
        kicker="Structure editor"
        title="Draw / add a molecule"
        subtitle="Paste SMILES from a sketcher (Ketcher, JSME, ChemDraw). Properties update locally via RDKit.js when WASM loads."
      />
      <div className="grid grid-2">
        <form className="card" onSubmit={add}>
          <div>
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div style={{ marginTop: 8 }}>
            <label>SMILES</label>
            <textarea rows={4} value={smiles} onChange={(e) => setSmiles(e.target.value)} className="mono" />
          </div>
          <div className="chip-row" style={{ marginTop: 10 }}>
            {EXAMPLES.map((ex) => (
              <button
                key={ex.name}
                type="button"
                className={`chip${name === ex.name ? " active" : ""}`}
                onClick={() => {
                  setSmiles(ex.smiles);
                  setName(ex.name);
                }}
              >
                {ex.name}
              </button>
            ))}
          </div>
          <p className="muted">
            External sketcher:{" "}
            <a href="https://lifescience.opensource.epam.com/ketcher/" target="_blank" rel="noreferrer">
              Ketcher
            </a>{" "}
            — copy SMILES back into this field.
          </p>
          <button type="submit" disabled={saving || !!error}>
            {saving && <ButtonSpinner />}
            Add to project
          </button>
        </form>
        <div className="card">
          <div className="mol-thumb" style={{ minHeight: 220 }}>
            {computing ? (
              <div className="muted">Computing depiction…</div>
            ) : (
              <img src={depictUrl(smiles, 320, 220)} alt="2D depiction" />
            )}
          </div>
          <p className="muted" style={{ marginTop: 8 }}>
            Properties{" "}
            {source === "wasm"
              ? "(client-side RDKit.js, no server round-trip)"
              : source === "server"
                ? "(server RDKit)"
                : computing
                  ? "(calculating…)"
                  : ""}
          </p>
          {error && <div className="error">{error}</div>}
          {computing && !props && (
            <div className="progress indeterminate" style={{ margin: "8px 0 12px" }}>
              <span />
            </div>
          )}
          {props && (
            <>
              <div className="gauge-grid" style={{ marginBottom: 12 }}>
                <Gauge label="MW" value={props.mw ?? 0} max={500} />
                <Gauge label="logP" value={props.logp ?? 0} max={5} />
                <Gauge label="TPSA" value={props.tpsa ?? 0} max={140} />
                <Gauge label="QED" value={props.qed ?? 0} max={1} />
              </div>
              <div className="chip-row" style={{ marginBottom: 10 }}>
                <span className={`badge ${props.lipinski_pass ? "ok" : "warn"}`}>
                  Lipinski {props.lipinski_pass ? "pass" : "flag"}
                </span>
                <span className={`badge ${props.veber_pass ? "ok" : "warn"}`}>
                  Veber {props.veber_pass ? "pass" : "flag"}
                </span>
              </div>
              <table>
                <tbody>
                  {Object.entries(props).map(([k, v]) => (
                    <tr key={k}>
                      <th>{k}</th>
                      <td className="mono">{String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
