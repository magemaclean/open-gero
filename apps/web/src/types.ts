export type User = {
  id: string;
  email: string;
  role: string;
  display_name: string;
};

export type Project = {
  id: string;
  name: string;
  description: string;
  molecule_count: number;
  job_count: number;
  created_at: string;
};

export type Properties = {
  mw?: number | null;
  logp?: number | null;
  tpsa?: number | null;
  hbd?: number | null;
  hba?: number | null;
  rotatable_bonds?: number | null;
  ring_count?: number | null;
  lipinski_pass?: boolean | null;
  veber_pass?: boolean | null;
  qed?: number | null;
  formula?: string | null;
};

export type Molecule = {
  id: string;
  project_id: string;
  name: string;
  smiles_raw: string;
  canonical_smiles: string;
  inchikey: string;
  formula: string;
  source: string;
  created_at: string;
  properties?: Properties | null;
  tanimoto?: number;
};

export type Target = {
  id: string;
  slug: string;
  name: string;
  uniprot: string;
  pdb_id: string;
  alphafold_id: string;
  description: string;
  pathway: string;
  structure_kind: string;
  center_x: number;
  center_y: number;
  center_z: number;
  size_x: number;
  size_y: number;
  size_z: number;
  version: string;
};

export type Job = {
  id: string;
  project_id: string;
  type: string;
  status: string;
  params_json: Record<string, unknown>;
  params_hash: string;
  total_items: number;
  completed_items: number;
  failed_items: number;
  cached: boolean;
  error: string;
  batches_done: number;
  batches_total: number;
  created_at: string;
};

export type DockingResult = {
  id: string;
  job_id: string;
  molecule_id: string;
  molecule_name: string;
  canonical_smiles: string;
  target_id: string;
  best_score: number;
  pose_uri: string;
  engine: string;
  cached: boolean;
};

export type Dataset = {
  id: string;
  slug: string;
  name: string;
  version: string;
  license: string;
  description: string;
  compound_count: number;
};

export type DatasetHit = {
  id: string;
  name: string;
  smiles: string;
  organism: string;
  effect_size: string;
  effect_note: string;
  citation: string;
  pmid: string;
  tanimoto?: number;
};

export type ImportReport = {
  accepted: number;
  rejected: number;
  duplicates_merged: number;
  errors: { row?: number; name?: string; error: string }[];
};
