from fastapi.testclient import TestClient


def test_health(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert "medical advice" in resp.json()["disclaimer"].lower()


def test_login_and_me(client: TestClient, auth_headers: dict[str, str]):
    me = client.get("/api/auth/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["email"] == "demo@opengero.local"
    assert me.json()["role"] == "admin"


def test_projects_and_library(client: TestClient, auth_headers: dict[str, str]):
    projects = client.get("/api/projects", headers=auth_headers)
    assert projects.status_code == 200
    assert any(p["name"] == "Senolytic shortlist" for p in projects.json())
    pid = next(p["id"] for p in projects.json() if p["name"] == "Senolytic shortlist")
    mols = client.get(f"/api/projects/{pid}/molecules", headers=auth_headers)
    assert mols.status_code == 200
    assert len(mols.json()) >= 10
    aspirin = next(m for m in mols.json() if m["name"] == "Aspirin")
    assert aspirin["properties"]["lipinski_pass"] is True


def test_import_dedupe_and_malformed(client: TestClient, auth_headers: dict[str, str]):
    created = client.post(
        "/api/projects",
        headers=auth_headers,
        json={"name": "Import lab", "description": "dedupe test"},
    )
    pid = created.json()["id"]
    text = "CCO ethanol\nOCC ethanol-dup\nnot-a-smiles junk\nCC(=O)Oc1ccccc1C(=O)O aspirin\n"
    resp = client.post(
        f"/api/projects/{pid}/molecules/import",
        headers=auth_headers,
        data={"text": text, "fmt": "smiles"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] == 2
    assert body["duplicates_merged"] == 1
    assert body["rejected"] == 1
    assert body["errors"][0]["error"]


def test_similarity_against_geroprotectors(client: TestClient, auth_headers: dict[str, str]):
    projects = client.get("/api/projects", headers=auth_headers).json()
    pid = next(p["id"] for p in projects if p["name"] == "Senolytic shortlist")
    mols = client.get(f"/api/projects/{pid}/molecules", headers=auth_headers).json()
    quercetin = next(m for m in mols if m["name"] == "Quercetin")
    resp = client.post(
        f"/api/projects/{pid}/search/similarity",
        headers=auth_headers,
        json={
            "molecule_id": quercetin["id"],
            "against": "dataset",
            "dataset_slug": "geroprotectors",
            "threshold": 0.3,
            "limit": 10,
        },
    )
    assert resp.status_code == 200
    hits = resp.json()["hits"]
    assert hits
    assert hits[0]["tanimoto"] >= 0.3
    assert "citation" in hits[0]
    assert resp.json()["dataset"]["version"]


def test_substructure_search(client: TestClient, auth_headers: dict[str, str]):
    projects = client.get("/api/projects", headers=auth_headers).json()
    pid = next(p["id"] for p in projects if p["name"] == "Senolytic shortlist")
    resp = client.post(
        f"/api/projects/{pid}/search/substructure",
        headers=auth_headers,
        json={"smarts": "c1ccccc1O"},
    )
    assert resp.status_code == 200
    names = {h["name"] for h in resp.json()["hits"]}
    assert "Resveratrol" in names or "Quercetin" in names


def test_docking_job_and_export(client: TestClient, auth_headers: dict[str, str]):
    projects = client.get("/api/projects", headers=auth_headers).json()
    pid = next(p["id"] for p in projects if p["name"] == "Senolytic shortlist")
    targets = client.get("/api/targets", headers=auth_headers).json()
    mtor = next(t for t in targets if t["slug"] == "mtor")
    mols = client.get(f"/api/projects/{pid}/molecules", headers=auth_headers).json()[:4]
    job = client.post(
        f"/api/projects/{pid}/jobs",
        headers=auth_headers,
        json={
            "type": "docking",
            "target_id": mtor["id"],
            "molecule_ids": [m["id"] for m in mols],
            "exhaustiveness": 4,
            "seed": 7,
            "batch_size": 2,
        },
    )
    assert job.status_code == 201, job.text
    body = job.json()
    assert body["status"] in {"done", "queued", "running"}
    # sqlite path runs inline
    status = client.get(f"/api/jobs/{body['id']}", headers=auth_headers).json()
    assert status["status"] == "done"
    results = client.get(f"/api/jobs/{body['id']}/results", headers=auth_headers).json()
    assert len(results) == 4
    assert results[0]["best_score"] <= results[-1]["best_score"]
    export = client.post(
        f"/api/projects/{pid}/export",
        headers=auth_headers,
        json={"format": "csv", "job_id": body["id"], "molecule_ids": [m["id"] for m in mols]},
    )
    assert export.status_code == 200
    assert "OpenGero provenance" in export.text
    assert "disclaimer" in export.text.lower()
    methods = client.get(f"/api/projects/{pid}/methods", headers=auth_headers)
    assert methods.status_code == 200
    assert "RDKit" in methods.json()["text"]


def test_soft_delete_requires_confirm(client: TestClient, auth_headers: dict[str, str]):
    created = client.post(
        "/api/projects", headers=auth_headers, json={"name": "Temp", "description": ""}
    )
    pid = created.json()["id"]
    denied = client.delete(f"/api/projects/{pid}", headers=auth_headers)
    assert denied.status_code == 400
    ok = client.delete(f"/api/projects/{pid}?confirm=true", headers=auth_headers)
    assert ok.status_code == 204
    listed = client.get("/api/projects", headers=auth_headers).json()
    assert all(p["id"] != pid for p in listed)


def test_admin_stats(client: TestClient, auth_headers: dict[str, str]):
    resp = client.get("/api/admin/stats", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["users"] >= 1
    assert resp.json()["dataset_version"]
    assert "docking_engine" in resp.json()


def test_restore_project_and_password(client: TestClient, auth_headers: dict[str, str]):
    created = client.post(
        "/api/projects", headers=auth_headers, json={"name": "Restore me", "description": ""}
    )
    pid = created.json()["id"]
    client.delete(f"/api/projects/{pid}?confirm=true", headers=auth_headers)
    gone = client.get("/api/projects?deleted=true", headers=auth_headers).json()
    assert any(p["id"] == pid for p in gone)
    restored = client.post(f"/api/projects/{pid}/restore", headers=auth_headers)
    assert restored.status_code == 200
    live = client.get("/api/projects", headers=auth_headers).json()
    assert any(p["id"] == pid for p in live)
    bad = client.post(
        "/api/auth/password",
        headers=auth_headers,
        json={"current_password": "wrong-password", "new_password": "newpass123"},
    )
    assert bad.status_code == 401
    ok = client.post(
        "/api/auth/password",
        headers=auth_headers,
        json={"current_password": "demo12345", "new_password": "demo12345"},
    )
    assert ok.status_code == 200


def test_library_pagination_header(client: TestClient, auth_headers: dict[str, str]):
    projects = client.get("/api/projects", headers=auth_headers).json()
    pid = next(p["id"] for p in projects if p["name"] == "Senolytic shortlist")
    resp = client.get(f"/api/projects/{pid}/molecules?limit=5&offset=0", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 5
    assert int(resp.headers["x-total-count"]) >= 10
    filtered = client.get(
        f"/api/projects/{pid}/molecules?veber=true&mw_min=100&mw_max=500&logp_max=6",
        headers=auth_headers,
    )
    assert filtered.status_code == 200
    assert int(filtered.headers["x-total-count"]) >= 1


def test_molecule_restore(client: TestClient, auth_headers: dict[str, str]):
    created = client.post(
        "/api/projects", headers=auth_headers, json={"name": "Mol restore", "description": ""}
    )
    pid = created.json()["id"]
    added = client.post(
        f"/api/projects/{pid}/molecules",
        headers=auth_headers,
        json={"smiles": "CCO", "name": "ethanol"},
    )
    assert added.status_code == 201
    mid = added.json()["id"]
    client.delete(f"/api/projects/{pid}/molecules/{mid}?confirm=true", headers=auth_headers)
    live = client.get(f"/api/projects/{pid}/molecules", headers=auth_headers).json()
    assert all(m["id"] != mid for m in live)
    gone = client.get(f"/api/projects/{pid}/molecules?deleted=true", headers=auth_headers).json()
    assert any(m["id"] == mid for m in gone)
    restored = client.post(f"/api/projects/{pid}/molecules/{mid}/restore", headers=auth_headers)
    assert restored.status_code == 200
    live = client.get(f"/api/projects/{pid}/molecules", headers=auth_headers).json()
    assert any(m["id"] == mid for m in live)


def test_saved_search_recall(client: TestClient, auth_headers: dict[str, str]):
    projects = client.get("/api/projects", headers=auth_headers).json()
    pid = next(p["id"] for p in projects if p["name"] == "Senolytic shortlist")
    created = client.post(
        f"/api/projects/{pid}/searches",
        headers=auth_headers,
        json={"name": "quercetin-like", "kind": "similarity", "params": {"smiles": "CCO", "threshold": 0.2}},
    )
    assert created.status_code == 201
    listed = client.get(f"/api/projects/{pid}/searches", headers=auth_headers)
    assert listed.status_code == 200
    assert any(s["name"] == "quercetin-like" for s in listed.json())


def test_admin_last_admin_and_disable(client: TestClient, auth_headers: dict[str, str]):
    me = client.get("/api/auth/me", headers=auth_headers).json()
    self_disable = client.post(f"/api/admin/users/{me['id']}/disable", headers=auth_headers)
    assert self_disable.status_code == 400
    registered = client.post(
        "/api/auth/register",
        json={"email": "labmate@example.com", "password": "labpass12", "display_name": "Lab"},
    )
    assert registered.status_code == 200
    users = client.get("/api/admin/users", headers=auth_headers).json()
    other = next(u for u in users if u["email"] == "labmate@example.com")
    demote_last = client.post(
        f"/api/admin/users/{me['id']}/role?role=user", headers=auth_headers
    )
    assert demote_last.status_code == 400
    disabled = client.post(f"/api/admin/users/{other['id']}/disable", headers=auth_headers)
    assert disabled.status_code == 200
    enabled = client.post(f"/api/admin/users/{other['id']}/enable", headers=auth_headers)
    assert enabled.status_code == 200


def test_meta_engine_and_job_ws_auth(client: TestClient, auth_headers: dict[str, str]):
    meta = client.get("/api/meta")
    assert meta.status_code == 200
    assert meta.json()["docking_engine"]
    projects = client.get("/api/projects", headers=auth_headers).json()
    pid = next(p["id"] for p in projects if p["name"] == "Senolytic shortlist")
    targets = client.get("/api/targets", headers=auth_headers).json()
    mols = client.get(f"/api/projects/{pid}/molecules?limit=2", headers=auth_headers).json()
    job = client.post(
        f"/api/projects/{pid}/jobs",
        headers=auth_headers,
        json={
            "type": "docking",
            "target_id": targets[0]["id"],
            "molecule_ids": [m["id"] for m in mols],
            "exhaustiveness": 4,
            "seed": 7,
            "batch_size": 2,
        },
    )
    assert job.status_code == 201, job.text
    job_id = job.json()["id"]
    token = auth_headers["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/api/ws/jobs/{job_id}?token={token}") as ws:
        payload = ws.receive_json()
        assert payload["id"] == job_id
        assert payload["status"] in {"done", "queued", "running", "failed", "cancelled"}
    denied = False
    try:
        with client.websocket_connect(f"/api/ws/jobs/{job_id}"):
            pass
    except Exception:
        denied = True
    assert denied
