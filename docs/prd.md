# OpenGero product requirements

Canonical product document. How to run lives in `README.md` and root `docker-compose.yml`. Internals live in `docs/architecture.md`.

**Status:** v0.1.0 shipped (Apache 2.0). Self-hostable in-silico screening workbench for longevity / geroscience labs.

**Disclaimer:** Research tool only. Not medical advice. Docking scores and similarity ranks are computational prioritization heuristics, not experimental measurements or dosing guidance.

## Problem

Academic geroscience groups stitch commercial suites, desktop docking GUIs, and spreadsheets. OpenGero keeps compound management, drug-likeness, geroprotector similarity, and job-orchestrated docking in one browser workbench that starts from `docker compose up`.

## Users

| Role | Who | What they can do today |
|---|---|---|
| Researcher | Lab member with an account | Own projects, import/draw molecules, search, queue docking, export, change password |
| Admin | First registered user, plus the seeded demo account | All researcher actions, plus `/admin` stats, user list, role changes, disable/enable accounts, queue health, add targets by PDB ID |

Single-organization model. There are no org roles, teams, or public API tokens. Disable the seeded demo admin before sharing a lab instance.

## Decided architecture

These are closed decisions, not open questions.

| Decision | Choice | Why |
|---|---|---|
| API + worker runtime | All-Python FastAPI + RQ | Chemistry and docking are already Python/RDKit/Vina. A second language does not help the screening workflow. |
| .NET API gateway | **Not a goal** | Would add a runtime and deploy surface. The HTTP API is already a separate FastAPI app, so a host that *must* terminate at ASP.NET could add a gateway later without rewriting workers. Do not build this unless a specific host requires it. |
| Search index | App-level Morgan fingerprints in Postgres (`bytea` / `LargeBinary`) + in-process Tanimoto | Avoids building `postgresql-rdkit` for every host architecture. Cartridge SQL can replace `search.py` later without a schema break. |
| Docking engine | AutoDock Vina when `vina` and Open Babel are on the worker image; otherwise `heuristic-v0` | Heuristic scores are labeled in the UI (banner + job results) and every export. They are not binding energies. |
| Reference data | Hand-curated public-literature snapshot (`data/datasets/`), DrugAge-shaped JSON | Not a DrugAge/GenAge dump. No DrugBank or other restrictively licensed data. |
| Compose | One file: root `docker-compose.yml` | Services: `postgres`, `redis`, `api`, `worker`, `web`. |
| Workbench assistant | First-party tool-calling in the API | Chat in the UI uses Anthropic or OpenAI (lab env key or per-user key on `/account`). Tools call existing OpenGero actions as the signed-in user. Writes wait for an in-UI confirm. Claude Code, Cursor, and Codex are **not** Compose services. |

```
apps/web      React 18 + TypeScript + Vite (dark-first workbench, light theme)
apps/api      FastAPI (auth, projects, search, jobs, exports, WebSocket)
apps/worker   RQ consumer (descriptor batches + docking); reuses the API package
data/         Versioned geroprotector snapshot + aging target catalog
```

## Shipped in v0.1

### Workbench

- JWT email/password auth; register / login; password change at `/account`; demo account `demo@opengero.local` / `demo12345`
- Dark-first UI with light-mode toggle, command palette (`Ctrl+K` / `⌘K`), orbital loaders, skeletons, toasts
- Workbench assistant (spark control or `Ctrl+Shift+J`): read library/jobs/search; writes (create project, import, dock, export, …) wait for confirm. Lab key `ASSISTANT_API_KEY` or a user key on `/account` (Anthropic or OpenAI). Prompts leave the host to that provider.
- Persistent research-only disclaimer in the UI and `X-OpenGero-Disclaimer` on HTTP responses
- Projects group molecules, targets, and jobs; edit name/description; confirm soft-delete; restore within 30 days
- Library: SMILES / CSV / SDF import (up to 50,000 rows), RDKit revalidation, InChIKey dedupe with a merge report
- Descriptors inline for ≤500 new molecules; larger imports enqueue a `descriptor_batch` job
- Filters: text, MW min/max, TPSA max, logP max, Lipinski, Veber
- Paginated table and card views (50 per page, `X-Total-Count`); CSV / SDF export with a provenance block
- Soft-delete molecules with confirm; restore from “Show deleted”
- Auto-written methods paragraph per project
- Editor: embedded JSME sketcher plus SMILES textarea; live MW, logP, TPSA, HBD/HBA, Lipinski/Veber via RDKit.js when WASM loads, else the chemistry service; QED from the server when the client module omits it (gauges show `—`, not `0.00`)
- Molecule dossier: depiction, provenance, computed properties, project job list, search-similar, delete
- Similarity: Morgan/Tanimoto (radius 2, 2048 bits) vs the bundled geroprotector set and vs the project library; start from a dossier SMILES
- Saved searches: save, list, and re-run from chips on the search page
- Substructure: SMARTS over the project library
- Docking jobs: library × catalog target, chunked batches (default 100), cancel, WebSocket progress with HTTP poll fallback, result cache on `(molecule_id, target_id, params_hash)`
- Ranked results, 3D pose viewer (3Dmol), ranked CSV export
- Heuristic-only banner when AutoDock Vina is not on the worker
- Geroprotector dataset browser (manifest version `0.1.0-2026-08`)
- Aging target catalog (mTOR, SIRT1, SIRT6, AMPK, IGF1R, NAMPT, CD38, FOXO3 AlphaFold-flagged, and others in `data/targets/catalog.json`)
- Admin: user count, disk usage, queue health, dataset version, docking engine; promote/demote roles; disable/enable users (last admin and self cannot be disabled)

### API restore and hygiene

| Capability | API | UI |
|---|---|---|
| Soft-delete project (30-day retain) | `DELETE /api/projects/{id}?confirm=true` | Confirm dialog; recently-deleted list |
| Restore project | `POST /api/projects/{id}/restore` | Restore on the projects page |
| Soft-delete molecule | `DELETE /api/projects/{id}/molecules/{id}?confirm=true` | Confirm from library and dossier |
| Restore molecule | `POST /api/projects/{id}/molecules/{id}/restore` | Library “Show deleted” |
| Edit project | `PATCH /api/projects/{id}` | Edit modal |
| Saved searches | `GET` + `POST /api/projects/{id}/searches` | Save, list, re-run |
| Change role | `POST /api/admin/users/{id}/role` | Role `<select>` |
| Disable / enable user | `POST /api/admin/users/{id}/disable` · `/enable` | Confirm disable; last-admin protected |
| Change password | `POST /api/auth/password` | `/account` |
| Live job stream | `WS /api/ws/jobs/{id}?token=` | Subscribe; poll if the socket drops |
| Library pagination | `limit` (default 50, max 2000) + `offset` + `X-Total-Count` | Pager |
| Extra library filters | `veber`, `mw_min`, `logp_max` | Filter builder |
| Workbench assistant | `POST /api/assistant/chat` · `/confirm` · `/reject`; `GET /status`; `PUT /settings` | Chat panel; confirm card for writes |

## Next improvements

P1–P3 from the v0.1 story are shipped. Remaining items are polish, not unfinished claims:

1. **Playwright (or similar) browser e2e** — CI runs `pytest` plus `vitest` (query builder, job socket URL, QED formatting) and `npm run build`. Full click-through auth/library/job coverage is still a gap.
2. **Ketcher** — the editor embeds **JSME** (CDN). Ketcher remains an optional external sketcher if a lab prefers it; do not vendor a 30MB npm tree unless someone needs Ketcher-specific features.
3. **2D depiction** — still RDKit SVG via `/api/chem/depict`, not a client-side canvas renderer.

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
- Claude Code / Cursor / Codex containers in Compose, or embedding those CLIs as the workbench assistant
- Unattended “do everything” agent (no confirm)

## Success for a lab demo

After `docker compose up --build` at [http://localhost:8080](http://localhost:8080):

1. Sign in as the demo admin.
2. Open **Senolytic shortlist** (seeded).
3. Run similarity vs geroprotectors and see organism, effect, PMID.
4. Queue a docking job against a catalog target; scores are labeled Vina or `heuristic-v0`. If Vina is missing, a banner says so.
5. Export CSV/SDF and read the methods paragraph.
6. Soft-delete a molecule, restore it, change password on `/account`. On a shared lab, create a second admin and disable `demo@opengero.local`.
7. Optional: save an Anthropic or OpenAI key on `/account`, open the assistant, ask about the library, and confirm an import or docking job.

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
