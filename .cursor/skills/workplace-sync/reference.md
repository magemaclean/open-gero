# Workplace-sync drift checklist

Walk this list against the current tree. Fix any row that fails.

## Files that must exist

- `README.md`
- `LICENSE` (Apache 2.0)
- `docker-compose.yml` (repo root; only compose file)
- `docs/prd.md`
- `docs/deploy.md`
- `docs/architecture.md`
- `apps/api/opengero/main.py`
- `apps/worker/worker.py`
- `apps/web/package.json`
- `data/datasets/manifest.json`
- `data/targets/catalog.json`
- `.github/workflows/ci.yml`

## Claims to verify

- Demo email/password in README and `docs/deploy.md` match `DEMO_EMAIL` / `DEMO_PASSWORD` in `apps/api/opengero/seed.py`
- Quick start uses `docker compose up --build` from the repo root and UI port **8080**
- Local dev: `PYTHONPATH=apps/api`, API **8000**, Vite proxies `/api`
- README layout lists directories that exist; no `docs/methods`, `packages/shared-types`, or `deploy/docker-compose.yml`
- Architecture doc matches job flow: RDKit ingest, in-process Tanimoto, RQ/`process_job`, heuristic-v0 when Vina is absent
- `docs/prd.md` matches shipped APIs/UI (no .NET gateway as a goal; P1–P3 workbench items are shipped, not listed as unfinished)
- Dataset version string in `manifest.json` matches what `/api/admin/stats` and exports would show after seed
- CI runs `pytest` from repo root and `npm test` then `npm run build` in `apps/web`

## Compose

- Root `docker-compose.yml` build contexts are `.` (not `..`)
- Services: `postgres`, `redis`, `api`, `worker`, `web`
- No duplicate compose file under `deploy/`

## After edits

Commit, push the working branch, then continue the PR/merge steps in SKILL.md.
