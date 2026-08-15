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
