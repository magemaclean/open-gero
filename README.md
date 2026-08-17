# OpenGero

Open-source, self-hostable **in-silico molecule screening** for longevity and geroscience labs.

Import or draw candidates, compute drug-likeness, search a curated geroprotector set, dock against aging-related targets, and export ranked results with full provenance — from one `docker compose up`.

**License:** Apache 2.0  
**Status:** v0.1 MVP  
**Disclaimer:** Research tool only. Not medical advice. Docking scores and similarity ranks are computational prioritization heuristics, not experimental measurements or dosing guidance.

## Why this exists

Academic geroscience groups today stitch together commercial suites, desktop docking GUIs, and spreadsheets. OpenGero is a browser workbench that keeps the workflow in one place: compound management, properties, similarity to known geroprotectors, and job-orchestrated docking.

## Quick start

```bash
docker compose up --build
```

Then open [http://localhost:8080](http://localhost:8080) and sign in:

| | |
|---|---|
| Email | `demo@opengero.local` |
| Password | `demo12345` |

The demo project **Senolytic shortlist** is preloaded so you can run similarity search and a docking job immediately.

### Local development (no Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
export PYTHONPATH=apps/api
export DATABASE_URL=sqlite:///./opengero.db
uvicorn opengero.main:app --reload --port 8000
```

```bash
cd apps/web
npm install
npm run dev
```

The Vite dev server proxies `/api` to port 8000.

## What v0.1 does

1. **Projects** — group molecules, targets, and jobs; edit; confirm soft-delete with 30-day restore.
2. **Import** — SMILES / CSV / SDF, RDKit validation, InChIKey dedupe with a merge report (up to 50k rows).
3. **Editor** — embedded JSME sketcher or paste SMILES; live MW, logP, TPSA, HBD/HBA, Lipinski/Veber via RDKit.js when WASM loads; QED from the server when the client omits it.
4. **Library filters** — text, MW min/max, TPSA, logP max, Lipinski, Veber; paginated table/cards.
5. **Similarity** — Morgan/Tanimoto against the bundled geroprotector set, with organism, effect, and PMID; start from a molecule dossier; save and re-run searches.
6. **Substructure** — SMARTS search over the project library.
7. **Docking jobs** — chunked batches, cancel, WebSocket progress (HTTP poll fallback), result cache keyed on molecule + target + parameters.
8. **Results** — ranked scores, 3D pose viewer, CSV/SDF export with a provenance block, auto-written methods paragraph.
9. **Admin / account** — users, roles, disable/enable (last-admin protected), disk usage, queue health, password change. First registered user is admin; disable the seeded demo admin on a shared lab.
10. **Assistant** — in-app chat that reads the workbench and runs writes after confirm. Lab `ASSISTANT_API_KEY` or a user key on `/account` (Anthropic / OpenAI).

## Architecture

```
apps/web      React 18 + TypeScript + Vite
apps/api      FastAPI (auth, projects, search, jobs, exports, WebSocket, assistant)
apps/worker   RQ worker (descriptor batches + docking)
data/         Versioned geroprotector snapshot + target catalog
```

**Backend:** All-Python FastAPI + RQ worker. Chemistry and docking are already Python/RDKit/Vina; a second runtime would not help the screening workflow. A .NET API gateway is **not a goal** — see [docs/prd.md](docs/prd.md).

**Docking engine:** AutoDock Vina is used when `vina` and Open Babel are on the worker image. If they are missing, a **deterministic heuristic** runs instead and is labeled `heuristic-v0` in the UI and every export. Those scores are not binding energies.

**Search:** App-level Morgan fingerprints in Postgres (bytea) rather than the RDKit cartridge, so `docker compose` stays portable. Cartridge SQL can replace the Python loop later without changing the API.

**Datasets:** The bundled set is a **hand-curated public-literature snapshot**, not a DrugAge dump (FR-8 licensing). The JSON schema is DrugAge-shaped so a lab can drop in an OSI-compatible snapshot under `data/datasets/` and list it in `manifest.json`.

## Repository layout

```
docker-compose.yml   Only Compose file; run from the repo root
apps/web/            React client
apps/api/            FastAPI + RDKit
apps/worker/         RQ consumer
data/datasets/       Geroprotector snapshot + manifest
data/targets/        Aging target catalog (PDB / AlphaFold flags)
deploy/              Optional Caddyfile
docs/                PRD, deploy, and architecture notes
.cursor/skills/      Agent skills (workplace-sync)
```

## Tests

```bash
pip install -r apps/api/requirements.txt
pytest
cd apps/web && npm test && npm run build
```

## Security & product constraints

- JWT email/password, single-organization model; password change at `/account`
- Server-side revalidation of every structure
- Soft-delete with `confirm=true` and owner restore within 30 days
- Persistent UI + HTTP disclaimer: research only, not medical advice
- No DrugBank or other restrictively licensed data is redistributed

## Product requirements

[docs/prd.md](docs/prd.md) is the product source of truth: what v0.1 shipped, remaining polish, and out-of-scope items (ADMET, org roles, API tokens, ZINC-scale import, scheduled re-screens, generative design, .NET gateway).
