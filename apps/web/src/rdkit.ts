import type { Properties } from "./types";

let modulePromise: Promise<RDKitModule | null> | null = null;

export function loadRDKit(): Promise<RDKitModule | null> {
  if (modulePromise) return modulePromise;
  modulePromise = new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = "https://unpkg.com/@rdkit/rdkit/dist/RDKit_minimal.js";
    script.onload = () => {
      if (!window.initRDKitModule) {
        resolve(null);
        return;
      }
      window
        .initRDKitModule({
          locateFile: (f) => `https://unpkg.com/@rdkit/rdkit/dist/${f}`,
        })
        .then(resolve)
        .catch(() => resolve(null));
    };
    script.onerror = () => resolve(null);
    document.head.appendChild(script);
  });
  return modulePromise;
}

export async function clientDescriptors(smiles: string): Promise<Properties | null> {
  const rdkit = await loadRDKit();
  if (!rdkit) return null;
  const mol = rdkit.get_mol(smiles);
  if (!mol || !mol.is_valid()) {
    mol?.delete();
    return null;
  }
  const raw = JSON.parse(mol.get_descriptors()) as Record<string, number>;
  mol.delete();
  const mw = raw.amw ?? raw.exactmw;
  const logp = raw.CrippenClogP;
  const tpsa = raw.tpsa;
  const hbd = raw.NumHBD;
  const hba = raw.NumHBA;
  const rot = raw.NumRotatableBonds;
  const rings = raw.NumRings;
  return {
    mw: mw != null ? Math.round(mw * 1000) / 1000 : null,
    logp: logp != null ? Math.round(logp * 1000) / 1000 : null,
    tpsa: tpsa != null ? Math.round(tpsa * 1000) / 1000 : null,
    hbd,
    hba,
    rotatable_bonds: rot,
    ring_count: rings,
    lipinski_pass: mw <= 500 && logp <= 5 && hbd <= 5 && hba <= 10,
    veber_pass: rot <= 10 && tpsa <= 140,
    qed: raw.qed,
  };
}
