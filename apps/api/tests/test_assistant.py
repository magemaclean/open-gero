from unittest.mock import patch

from fastapi.testclient import TestClient

from opengero.assistant.providers import ModelTurn, ToolCall
from opengero.assistant.tools import WRITE_TOOLS, summarize


def test_assistant_status_unconfigured(client: TestClient, auth_headers: dict[str, str]):
    resp = client.get("/api/assistant/status", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is False
    assert body["source"] == "none"
    assert body["has_user_key"] is False


def test_assistant_chat_requires_key(client: TestClient, auth_headers: dict[str, str]):
    resp = client.post(
        "/api/assistant/chat",
        headers=auth_headers,
        json={"messages": [{"role": "user", "content": "list my projects"}]},
    )
    assert resp.status_code == 503
    assert "not configured" in resp.json()["detail"].lower()


def test_assistant_read_lists_projects(client: TestClient, auth_headers: dict[str, str]):
    turns = [
        ModelTurn(
            text="",
            tool_calls=[ToolCall(id="c1", name="list_projects", arguments={})],
        ),
        ModelTurn(text="You have Senolytic shortlist in the workspace."),
    ]

    def fake_complete(**_kwargs):
        return turns.pop(0)

    with (
        patch("opengero.assistant.loop.credentials_for", return_value=("anthropic", "test-key", "lab")),
        patch("opengero.assistant.loop.complete_turn", side_effect=fake_complete),
    ):
        resp = client.post(
            "/api/assistant/chat",
            headers=auth_headers,
            json={"messages": [{"role": "user", "content": "What projects do I have?"}]},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["pending_actions"] == []
    assert body["confirm_id"] is None
    assert "Senolytic" in body["reply"]


def test_assistant_write_waits_for_confirm(client: TestClient, auth_headers: dict[str, str]):
    before = client.get("/api/projects", headers=auth_headers).json()
    names = {p["name"] for p in before}

    turns = [
        ModelTurn(
            text="I can create that project.",
            tool_calls=[
                ToolCall(
                    id="w1",
                    name="create_project",
                    arguments={"name": "Assistant lab", "description": "from chat"},
                )
            ],
        )
    ]

    def fake_complete(**_kwargs):
        return turns.pop(0) if turns else ModelTurn(text="Created Assistant lab.")

    with (
        patch("opengero.assistant.loop.credentials_for", return_value=("anthropic", "test-key", "lab")),
        patch("opengero.assistant.loop.complete_turn", side_effect=fake_complete),
    ):
        proposed = client.post(
            "/api/assistant/chat",
            headers=auth_headers,
            json={"messages": [{"role": "user", "content": "Create a project called Assistant lab"}]},
        )
        assert proposed.status_code == 200, proposed.text
        body = proposed.json()
        assert body["confirm_id"]
        assert body["pending_actions"][0]["name"] == "create_project"
        assert "Assistant lab" in body["pending_actions"][0]["summary"]

        mid = client.get("/api/projects", headers=auth_headers).json()
        assert {p["name"] for p in mid} == names

        confirmed = client.post(
            "/api/assistant/confirm",
            headers=auth_headers,
            json={"confirm_id": body["confirm_id"]},
        )
        assert confirmed.status_code == 200, confirmed.text

    after = client.get("/api/projects", headers=auth_headers).json()
    assert any(p["name"] == "Assistant lab" for p in after)


def test_assistant_reject_does_not_write(client: TestClient, auth_headers: dict[str, str]):
    turns = [
        ModelTurn(
            text="Confirm to create.",
            tool_calls=[ToolCall(id="w1", name="create_project", arguments={"name": "Rejected lab"})],
        )
    ]

    def fake_complete(**_kwargs):
        return turns.pop(0)

    with (
        patch("opengero.assistant.loop.credentials_for", return_value=("anthropic", "test-key", "lab")),
        patch("opengero.assistant.loop.complete_turn", side_effect=fake_complete),
    ):
        proposed = client.post(
            "/api/assistant/chat",
            headers=auth_headers,
            json={"messages": [{"role": "user", "content": "Create Rejected lab"}]},
        )
    confirm_id = proposed.json()["confirm_id"]
    reject = client.post("/api/assistant/reject", headers=auth_headers, json={"confirm_id": confirm_id})
    assert reject.status_code == 204
    gone = client.post("/api/assistant/confirm", headers=auth_headers, json={"confirm_id": confirm_id})
    assert gone.status_code == 404
    names = [p["name"] for p in client.get("/api/projects", headers=auth_headers).json()]
    assert "Rejected lab" not in names


def test_assistant_byok_status(client: TestClient, auth_headers: dict[str, str]):
    saved = client.put(
        "/api/assistant/settings",
        headers=auth_headers,
        json={"provider": "openai", "api_key": "sk-test-user-key"},
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["configured"] is True
    assert body["source"] == "user"
    assert body["has_user_key"] is True
    assert body["provider"] == "openai"
    cleared = client.put("/api/assistant/settings", headers=auth_headers, json={"clear": True})
    assert cleared.status_code == 200
    assert cleared.json()["has_user_key"] is False
    assert cleared.json()["configured"] is False


def test_unknown_provider_rejected(client: TestClient, auth_headers: dict[str, str]):
    resp = client.put(
        "/api/assistant/settings",
        headers=auth_headers,
        json={"provider": "cursor", "api_key": "nope"},
    )
    assert resp.status_code == 400


def test_write_tool_summaries():
    assert "create_project" in WRITE_TOOLS
    assert "list_projects" not in WRITE_TOOLS
    assert "Assistant lab" in summarize("create_project", {"name": "Assistant lab"})
    assert "Import 2 SMILES" in summarize("import_smiles", {"project_id": "p1", "text": "CCO ethanol\nCCO2 ethanol2\n"})
