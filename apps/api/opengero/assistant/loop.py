from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..models import AssistantSettings, User
from ..config import get_settings
from .crypto import decrypt_secret
from .pending import put_pending
from .providers import AssistantError, complete_turn, resolve_model
from .tools import TOOLS, WRITE_TOOLS, run_tool, summarize

MAX_ROUNDS = 6
MAX_RESULT_CHARS = 8_000

SYSTEM = """You are the OpenGero workbench assistant for a longevity / geroscience screening lab.
You help the signed-in researcher inspect projects, compound libraries, geroprotector similarity, docking jobs, and methods text.
Writes (create/update project, import SMILES, add molecule, save search, queue/cancel docking, export) are proposed only — the UI asks the user to confirm before they run. Never claim a write already happened.
This is a research tool, not medical advice. Docking scores and similarity ranks are computational prioritization heuristics, not experimental measurements or dosing guidance. If the engine is heuristic-v0, say so.
Do not attempt admin, password change, delete, or restore. Prefer tools over guessing IDs. Keep answers concise.
Current project id: {project_id}.
"""


def credentials_for(user: User, db: Session) -> tuple[str, str, str]:
    """Return (provider, api_key, source) where source is lab|user|none."""
    settings = get_settings()
    row = db.get(AssistantSettings, user.id)
    if row and row.api_key_enc:
        key = decrypt_secret(settings.secret_key, row.api_key_enc)
        provider = (row.provider or settings.assistant_provider or "anthropic").lower()
        if key:
            return provider, key, "user"
    lab_key = (settings.assistant_api_key or "").strip()
    if lab_key:
        return (settings.assistant_provider or "anthropic").lower(), lab_key, "lab"
    return (settings.assistant_provider or "anthropic").lower(), "", "none"


def status_payload(user: User, db: Session) -> dict[str, Any]:
    provider, key, source = credentials_for(user, db)
    row = db.get(AssistantSettings, user.id)
    return {
        "configured": bool(key),
        "provider": provider if key else (settings_provider()),
        "source": source if key else "none",
        "has_user_key": bool(row and row.api_key_enc),
        "model": resolve_model(provider if key else settings_provider()),
    }


def settings_provider() -> str:
    return (get_settings().assistant_provider or "anthropic").lower()


def run_chat(
    *,
    db: Session,
    user: User,
    messages: list[dict[str, str]],
    project_id: str | None,
) -> dict[str, Any]:
    provider, api_key, source = credentials_for(user, db)
    if not api_key:
        raise AssistantError("Assistant is not configured. Add an API key on Account, or set ASSISTANT_API_KEY on the API.")
    system = SYSTEM.format(project_id=project_id or "none")
    history: list[dict[str, Any]] = [{"role": m["role"], "content": m["content"]} for m in messages]
    pending: list[dict[str, Any]] = []
    reply = ""
    for _ in range(MAX_ROUNDS):
        turn = complete_turn(provider=provider, api_key=api_key, system=system, messages=history, tools=TOOLS)
        reply = turn.text
        if not turn.tool_calls:
            break
        tool_results: list[dict[str, Any]] = []
        assistant_calls = []
        for call in turn.tool_calls:
            assistant_calls.append({"id": call.id, "name": call.name, "arguments": call.arguments})
            result = run_tool(
                call.name,
                call.arguments,
                db=db,
                user=user,
                allow_writes=False,
                default_project_id=project_id,
            )
            if result.get("_pending"):
                pending.append(
                    {
                        "name": result["name"],
                        "arguments": result["arguments"],
                        "summary": result["summary"],
                    }
                )
                tool_results.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {
                                "status": "awaiting_user_confirm",
                                "summary": result["summary"],
                                "note": "Do not claim this write ran. The user must confirm in the UI.",
                            }
                        ),
                    }
                )
            else:
                tool_results.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": _clip(json.dumps(result, default=str)),
                    }
                )
        history.append({"role": "assistant", "content": turn.text, "tool_calls": assistant_calls})
        history.extend(tool_results)
        if pending:
            break
    confirm_id = None
    pending_out = []
    if pending:
        confirm_id = put_pending(
            user.id,
            {"actions": pending, "project_id": project_id, "messages": messages},
        )
        pending_out = [{"name": p["name"], "summary": p["summary"], "arguments": _public_args(p["name"], p["arguments"])} for p in pending]
        if not reply:
            reply = "I can do that. Confirm the action below to run it on your project."
    return {
        "reply": reply or "Done.",
        "pending_actions": pending_out,
        "confirm_id": confirm_id,
        "downloads": [],
        "configured": True,
        "source": source,
    }


def run_confirmed(*, db: Session, user: User, payload: dict[str, Any]) -> dict[str, Any]:
    provider, api_key, _source = credentials_for(user, db)
    executed: list[dict[str, Any]] = []
    downloads: list[dict[str, str]] = []
    for action in payload.get("actions") or []:
        name = action.get("name") or ""
        if name not in WRITE_TOOLS:
            executed.append({"name": name, "error": "not a write tool"})
            continue
        result = run_tool(
            name,
            action.get("arguments") or {},
            db=db,
            user=user,
            allow_writes=True,
            default_project_id=payload.get("project_id"),
        )
        executed.append({"name": name, "summary": summarize(name, action.get("arguments") or {}), "result": result})
        url = None
        if isinstance(result.get("result"), dict):
            url = result["result"].get("url")
            filename = result["result"].get("filename")
            if url and filename:
                downloads.append({"filename": filename, "url": url})
    summary_text = _format_executed(executed)
    reply = summary_text
    if api_key:
        try:
            turn = complete_turn(
                provider=provider,
                api_key=api_key,
                system=SYSTEM.format(project_id=payload.get("project_id") or "none"),
                messages=[
                    {
                        "role": "user",
                        "content": "The user confirmed the proposed writes. Summarize what actually ran. Results:\n"
                        + _clip(json.dumps(executed, default=str)),
                    }
                ],
                tools=[],
            )
            if turn.text:
                reply = turn.text
        except AssistantError:
            pass
    return {
        "reply": reply,
        "pending_actions": [],
        "confirm_id": None,
        "downloads": downloads,
        "configured": True,
        "executed": executed,
    }


def _clip(text: str) -> str:
    if len(text) <= MAX_RESULT_CHARS:
        return text
    return text[: MAX_RESULT_CHARS - 20] + "…[truncated]"


def _public_args(name: str, args: dict[str, Any]) -> dict[str, Any]:
    public = dict(args)
    if name == "import_smiles" and "text" in public:
        lines = [ln for ln in str(public["text"]).splitlines() if ln.strip() and not ln.strip().startswith("#")]
        public["text"] = f"({len(lines)} SMILES lines)"
        public["line_count"] = len(lines)
    return public


def _format_executed(executed: list[dict[str, Any]]) -> str:
    lines = []
    for item in executed:
        if item.get("result", {}).get("ok"):
            lines.append(f"Ran {item.get('summary') or item.get('name')}.")
        else:
            err = item.get("result", {}).get("error") or item.get("error") or "failed"
            lines.append(f"Could not run {item.get('name')}: {err}")
    return " ".join(lines) or "No actions ran."
