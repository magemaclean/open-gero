---
name: workplace-sync
description: Keeps the OpenGero repo, docs, PRs, and local workspace aligned. Use when the user asks to sync the workplace/workspace, check documentation drift, update or merge pull requests, or bring the current branch up to date.
---

# Workplace sync

Make sure we dont have any documentation drift. 
Update and merge any PR's. 
Make sure our branch and workspace is upto date.

## When to run

Apply this skill whenever the user mentions workplace/workspace sync, documentation drift, stale PRs, merging, or updating the branch.

## Workflow

Copy and track:

```
Workplace sync:
- [ ] Fetch remotes and note default branch vs current branch
- [ ] Documentation drift check (see [reference.md](reference.md))
- [ ] Commit and push drift fixes on the working branch
- [ ] Update open PRs (description, draft/ready, CI)
- [ ] Merge PRs that are ready, green, and requested
- [ ] Fast-forward local default branch and working tree
```

### 1. Refresh git state

```bash
git fetch origin
git status -sb
git branch -vv
gh pr list --state open
```

Do not switch away from an in-progress feature branch until drift fixes for that work are committed and pushed.

### 2. Documentation drift

Compare user-facing docs to the tree. Fix mismatches in the same change set; do not leave README, `docs/`, or compose files describing files or services that do not exist.

Single sources of truth:

| Topic | Canonical file |
|---|---|
| How to run | `README.md` + root `docker-compose.yml` |
| Deploy | `docs/deploy.md` |
| Internals | `docs/architecture.md` |
| Demo login | `apps/api/opengero/seed.py` (`DEMO_EMAIL`, `DEMO_PASSWORD`) |
| App version | `apps/api/opengero/__init__.py` |
| Dataset versions | `data/datasets/manifest.json` |

Do not keep a second Compose file. Root `docker-compose.yml` is the only compose definition (`docker compose up` from the repo root).

Full checklist: [reference.md](reference.md).

### 3. Update pull requests

For each open PR on this repo:

1. Push the working branch (`git push -u origin <branch>`).
2. Update the PR body if the change set or run instructions drifted.
3. Mark draft ready when CI is green and the branch is mergeable.
4. Use `ManagePullRequest` for create/update. Use `gh pr merge` only when the user asked to merge.

### 4. Merge

Merge only when all of these hold:

- The user asked to merge (this skill's standing request counts for workplace-sync runs)
- `mergeable` is `MERGEABLE` and CI conclusion is `SUCCESS`
- Documentation drift from this pass is on the branch being merged

Prefer squash or merge commit to `main`. After merge:

```bash
git fetch origin
git checkout main
git pull origin main
git status
```

Delete the merged feature branch locally if it is no longer needed. Confirm the working tree matches `origin/main`.

### 5. Report

State what drifted, which PRs were updated or merged, and the current branch + HEAD.
