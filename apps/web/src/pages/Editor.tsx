import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, depictUrl } from "../api";
import { clientDescriptors } from "../rdkit";
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
  const [smiles, setSmiles] = useState("Oc1ccc(/C=C/c2cc(O)cc(O)c2)cc1");
  const [name, setName] = useState("Resveratrol");
  const [props, setProps] = useState<Properties | null>(null);
  const [source, setSource] = useState<"wasm" | "server" | "">("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError("");
      const local = await clientDescriptors(smiles);
      if (cancelled) return;
      if (local) {
        setProps(local);
        setSource("wasm");
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
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [smiles]);

  async function add(e: FormEvent) {
    e.preventDefault();
    const mol = await api<Molecule>(`/api/projects/${projectId}/molecules`, {
      method: "POST",
      body: JSON.stringify({ smiles, name }),
    });
    navigate(`/projects/${projectId}/molecules/${mol.id}`);
  }

  return (
    <div>
      <h1>Draw / add a molecule</h1>
      <p>
        Paste SMILES from a sketcher (Ketcher, JSME, ChemDraw) or type them here. Properties update locally via
        RDKit.js when the WASM module loads; otherwise the chemistry service is used.
      </p>
      <div className="grid grid-2">
        <form className="card" onSubmit={add}>
          <div>
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div style={{ marginTop: 8 }}>
            <label>SMILES</label>
            <textarea rows={4} value={smiles} onChange={(e) => setSmiles(e.target.value)} />
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            {EXAMPLES.map((ex) => (
              <button
                key={ex.name}
                type="button"
                className="secondary"
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
          <button type="submit">Add to project</button>
        </form>
        <div className="card">
          <div className="mol-thumb">
            <img src={depictUrl(smiles, 320, 220)} alt="2D depiction" />
          </div>
          <p className="muted" style={{ marginTop: 8 }}>
            Properties {source === "wasm" ? "(client-side RDKit.js, no server round-trip)" : source === "server" ? "(server RDKit)" : ""}
          </p>
          {error && <div className="error">{error}</div>}
          {props && (
            <table>
              <tbody>
                {Object.entries(props).map(([k, v]) => (
                  <tr key={k}>
                    <th>{k}</th>
                    <td>{String(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
