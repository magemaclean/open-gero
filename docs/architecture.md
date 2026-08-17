# Architecture notes

Product intent and remaining work: [prd.md](prd.md).

Compose lives only at the repo root (`docker-compose.yml`). Do not add a second file under `deploy/`.

## Request paths

1. **Import** — browser uploads SMILES/CSV/SDF → API parses with RDKit → InChIKey upsert → descriptors inline (≤500) or a `descriptor_batch` job.
2. **Similarity** — query fingerprint vs `dataset_compounds.fp_morgan` or project library fingerprints; Tanimoto in-process.
3. **Docking** — API writes `jobs` + `job_batches` (default 100 mols) → worker `process_job` → poses under `STORAGE_DIR/poses/{job}/{mol}.pdbqt` → UI subscribes to `WS /api/ws/jobs/{id}?token=` and falls back to polling `/api/jobs/{id}` if the socket drops. When `vina` / Open Babel are missing, scores are labeled `heuristic-v0` and the workbench shows a heuristic-only banner. The worker publishes the engine name to Redis on start (`opengero:docking_engine`).
4. **Cache** — unique `(molecule_id, target_id, params_hash)` on `docking_results`. Re-runs skip compute and are labeled cached.
5. **Soft-delete** — projects and molecules set `deleted_at`; list endpoints omit them unless `deleted=true`. `POST .../restore` clears the flag inside `soft_delete_days` (30). Disabled users cannot authenticate.
6. **Assistant** — `POST /api/assistant/chat` runs a short tool loop as the JWT user. Read tools execute immediately. Write tools are stored (Redis or memory, 15 min) until `POST /api/assistant/confirm`. Lab key: `ASSISTANT_API_KEY` / `ASSISTANT_PROVIDER`. Optional per-user key in `assistant_settings` (encrypted with `SECRET_KEY`). No vendor coding-agent containers.

## Why not the RDKit Postgres cartridge in v0.1

Building `postgresql-rdkit` for every host architecture is the main deploy-friction risk. Fingerprints as `LargeBinary` plus Python Tanimoto meet the 100k-library interactive target on a 4 vCPU node for the bundled and typical academic libraries. Cartridge operators can replace `search.py` later without a schema break. This is an internal swap, not a user-facing feature — see [prd.md](prd.md).

## AlphaFold targets

`structure_kind=alphafold` is stored on the target and shown as a warning chip. Exports and the methods paragraph should treat those poses as more speculative than crystal pockets.
