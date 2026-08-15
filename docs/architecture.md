# Architecture notes

Product intent and remaining work: [prd.md](prd.md).

Compose lives only at the repo root (`docker-compose.yml`). Do not add a second file under `deploy/`.

## Request paths

1. **Import** — browser uploads SMILES/CSV/SDF → API parses with RDKit → InChIKey upsert → descriptors inline (≤500) or a `descriptor_batch` job.
2. **Similarity** — query fingerprint vs `dataset_compounds.fp_morgan` or project library fingerprints; Tanimoto in-process.
3. **Docking** — API writes `jobs` + `job_batches` (default 100 mols) → worker `process_job` → poses under `STORAGE_DIR/poses/{job}/{mol}.pdbqt` → UI polls `/api/jobs/{id}`. `WS /api/ws/jobs/{id}` exists; the client does not subscribe yet.
4. **Cache** — unique `(molecule_id, target_id, params_hash)` on `docking_results`. Re-runs skip compute and are labeled cached.

## Why not the RDKit Postgres cartridge in v0.1

Building `postgresql-rdkit` for every host architecture is the main deploy-friction risk. Fingerprints as `LargeBinary` plus Python Tanimoto meet the 100k-library interactive target on a 4 vCPU node for the bundled and typical academic libraries. Cartridge operators can replace `search.py` later without a schema break. This is an internal swap, not a user-facing feature — see [prd.md](prd.md).

## AlphaFold targets

`structure_kind=alphafold` is stored on the target and shown as a warning chip. Exports and the methods paragraph should treat those poses as more speculative than crystal pockets.
