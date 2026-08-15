# OpenGero product requirements

Canonical product document. How to run lives in `README.md` and root `docker-compose.yml`. Internals live in `docs/architecture.md`.

**Status:** v0.1.0 shipped (Apache 2.0). Self-hostable in-silico screening workbench for longevity / geroscience labs.

**Disclaimer:** Research tool only. Not medical advice. Docking scores and similarity ranks are computational prioritization heuristics, not experimental measurements or dosing guidance.

## Problem

Academic geroscience groups stitch commercial suites, desktop docking GUIs, and spreadsheets. OpenGero keeps compound management, drug-likeness, geroprotector similarity, and job-orchestrated docking in one browser workbench that starts from `docker compose up`.

## Users

| Role | Who | What they can do today |
|---|---|---|
| Researcher | Lab member with an account | Own projects, import/draw molecules, search, queue docking, export |
| Admin | First registered user, plus the seeded demo account | All researcher actions, plus `/admin` stats, user list, queue health, add targets by PDB ID |

Single-organization model. There are no org roles, teams, or public API tokens.

## Decided architecture

These are closed decisions, not open questions.

| Decision | Choice | Why |
|---|---|---|
| API + worker runtime | All-Python FastAPI + RQ | Chemistry and docking are already Python/RDKit/Vina. A second language does not help the screening workflow. |
| .NET API gateway | **Not a goal** | Would add a runtime and deploy surface. The HTTP API is already a separate FastAPI app, so a host that *must* terminate at ASP.NET could add a gateway later without rewriting workers. Do not build this unless a specific host requires it. |
| Search index | App-level Morgan fingerprints in Postgres (`bytea` / `LargeBinary`) + in-process Tanimoto | Avoids building `postgresql-rdkit` for every host architecture. Cartridge SQL can replace `search.py` later without a schema break. |
| Docking engine | AutoDock Vina when `vina` and Open Babel are on the worker image; otherwise `heuristic-v0` | Heuristic scores are labeled in the UI and every export. They are not binding energies. |
| Reference data | Hand-curated public-literature snapshot (`data/datasets/`), DrugAge-shaped JSON | Not a DrugAge/GenAge dump. No DrugBank or other restrictively licensed data. |
| Compose | One file: root `docker-compose.yml` | Services: `postgres`, `redis`, `api`, `worker`, `web`. |

```
apps/web      React 18 + TypeScript + Vite (dark-first workbench, light theme)
apps/api      FastAPI (auth, projects, search, jobs, exports, WebSocket)
apps/worker   RQ consumer (descriptor batches + docking); reuses the API package
data/         Versioned geroprotector snapshot + aging target catalog
```

## Shipped in v0.1

### Workbench

- JWT email/password auth; register / login; demo account `demo@opengero.local` / `demo12345`
- Dark-first UI with light-mode toggle, command palette (`Ctrl+K` / `⌘K`), orbital loaders, skeletons, toasts
- Persistent research-only disclaimer in the UI and `X-OpenGero-Disclaimer` on HTTP responses
- Projects group molecules, targets, and jobs
- Library: SMILES / CSV / SDF import (up to 50,000 rows), RDKit revalidation, InChIKey dedupe with a merge report
- Descriptors inline for ≤500 new molecules; larger imports enqueue a `descriptor_batch` job
- Filters: text, MW, TPSA, Lipinski (API also supports Veber, MW min, logP max; UI does not expose all of them)
- Table and card views; CSV / SDF export with a provenance block
- Auto-written methods paragraph per project
- Editor: paste SMILES (external Ketcher link); live MW, logP, TPSA, HBD/HBA, Lipinski/Veber via RDKit.js when WASM loads, else the chemistry service
- Molecule dossier: depiction, provenance, computed properties, project job list
- Similarity: Morgan/Tanimoto (radius 2, 2048 bits) vs the bundled geroprotector set and vs the project library
- Substructure: SMARTS over the project library
- Docking jobs: library × catalog target, chunked batches (default 100), cancel, progress poll, result cache on `(molecule_id, target_id, params_hash)`
- Ranked results, 3D pose viewer (3Dmol), ranked CSV export
- Geroprotector dataset browser (manifest version `0.1.0-2026-08`)
- Aging target catalog (mTOR, SIRT1, SIRT6, AMPK, IGF1R, NAMPT, CD38, FOXO3 AlphaFold-flagged, and others in `data/targets/catalog.json`)
- Admin: user count, disk usage, queue health, dataset version

### API that exists but the UI does not use yet

| Capability | API | UI |
|---|---|---|
| Soft-delete project (30-day retain) | `DELETE /api/projects/{id}?confirm=true` | No delete or confirm dialog |
| Soft-delete molecule | `DELETE /api/projects/{id}/molecules/{id}?confirm=true` | No delete |
| Edit project name/description | `PATCH /api/projects/{id}` | Create only |
| List / reopen saved searches | `GET` + `POST /api/projects/{id}/searches` | Save only |
| Change user role | `POST /api/admin/users/{id}/role` | Read-only user table |
| Live job stream | `WS /api/ws/jobs/{id}` | Polls every 1.5s |
| Library pagination | `limit` (default 200, max 2000) + `offset` | Loads one unpaged request |
| Extra library filters | `veber`, `mw_min`, `logp_max` | Text, MW max, TPSA max, Lipinski only |

There is no restore/undelete endpoint for soft-deleted rows.

## Next improvements (in scope)

These are real product gaps against the v0.1 story, not a new milestone.

### P1 — Finish the v0.1 claims

1. **Destructive actions in the UI** — confirm dialogs for project and molecule soft-delete; call `confirm=true`; say that records are retained 30 days.
2. **Edit project** — name and description from the projects page or a project header.
3. **Saved-search recall** — list saved searches and re-run them.
4. **Admin role control** — promote/demote users from `/admin`.

### P2 — Make the workbench hold up

5. **Library pagination** — honor API `limit`/`offset` so a 50k import does not freeze the table.
6. **Job WebSocket** — subscribe to `/api/ws/jobs/{id}` and keep poll as fallback.
7. **Restore soft-deletes** — admin or owner undelete within 30 days (API + UI).
8. **QED display** — stop showing `0.00` when RDKit.js does not emit `qed`; compute on the server or hide the gauge.
9. **Frontend tests** — CI only `npm run build`s the web app today; add smoke tests for auth, library, and job queue.
10. **Worker Vina** — treat `autodock-vina` / Open Babel as required on the worker image, or surface a clear “heuristic-only” banner when they are missing.

### P3 — Screening UX

11. **Embedded sketcher** — Ketcher (or equivalent) in the editor instead of a paste-from-another-tab loop.
12. **Query from library** — start similarity search from a molecule dossier, not only a SMILES box.
13. **Expose remaining filters** — Veber, MW min, logP max in the filter builder.
14. **Password change / disable demo admin** — required before a shared lab instance.

## Out of scope

Do not start these unless this document is revised for a new version.

- ADMET / tox models
- Multi-org roles, SSO, or public API tokens
- ZINC-scale import or catalog-scale virtual screening
- Scheduled re-screens
- Generative design
- RDKit Postgres cartridge (allowed later as an internal swap; not a user-facing feature)
- .NET / ASP.NET API gateway
- DrugAge, GenAge, or DrugBank dumps

## Success for a lab demo

After `docker compose up --build` at [http://localhost:8080](http://localhost:8080):

1. Sign in as the demo admin.
2. Open **Senolytic shortlist** (seeded).
3. Run similarity vs geroprotectors and see organism, effect, PMID.
4. Queue a docking job against a catalog target; scores are labeled Vina or `heuristic-v0`.
5. Export CSV/SDF and read the methods paragraph.

## Sources of truth

| Topic | File |
|---|---|
| This PRD | `docs/prd.md` |
| How to run | `README.md` + root `docker-compose.yml` |
| Deploy | `docs/deploy.md` |
| Internals | `docs/architecture.md` |
| Demo login | `apps/api/opengero/seed.py` |
| App version | `apps/api/opengero/__init__.py` (`0.1.0`) |
| Dataset version | `data/datasets/manifest.json` (`0.1.0-2026-08`) |
| Target catalog | `data/targets/catalog.json` |
