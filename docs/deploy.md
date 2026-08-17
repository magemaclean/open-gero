# Deploying OpenGero

## One-command host

```bash
git clone https://github.com/magemaclean/open-gero.git
cd open-gero
cp .env.example .env   # set SECRET_KEY
docker compose up --build -d   # uses the root docker-compose.yml only
```

Services:

| Service | Port | Role |
|---|---|---|
| web | 8080 | Nginx SPA + `/api` reverse proxy |
| api | 8000 | FastAPI |
| worker | — | RQ docking / descriptor batches |
| postgres | 5432 (internal) | Metadata, fingerprints, jobs |
| redis | 6379 (internal) | Queue (AOF) + job pub/sub |

Change the default Postgres password before any network-exposed deploy.

## Backups

- Postgres: `docker compose exec postgres pg_dump -U opengero opengero > backup.sql`
- Object/pose files: volume `storage`
- Redis AOF: volume `redisdata` (jobs can be rebuilt from Postgres)

## Users

The first account created on a blank database is an admin. The seeded demo user is also admin (`demo@opengero.local` / `demo12345`). Before a shared lab deploy: change passwords on `/account`, create a second admin if needed, then disable the demo account from `/admin`. The last remaining admin cannot be demoted or disabled.

Optional workbench assistant: set `ASSISTANT_API_KEY` and `ASSISTANT_PROVIDER` (`anthropic` or `openai`) on the API service, or let each user paste a key on `/account`. Prompts are sent to that provider. Writes still require an in-UI confirm.

## Adding DrugAge / GenAge snapshots

Place an OSI-compatible JSON file in `data/datasets/` and add an entry to `manifest.json` with `slug`, `version`, `license`, and `file`. Restart the API so `seed_all` loads new slugs. Do not commit restrictively licensed dumps.

## ARM64 / AMD64

Images are based on official `python:3.12-slim`, `postgres:16-alpine`, `redis:7-alpine`, and `nginx` multi-arch tags. RDKit wheels are published for both architectures.
