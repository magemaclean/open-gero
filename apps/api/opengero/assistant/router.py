from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import current_user
from ..models import AssistantSettings, User
from ..schemas import (
    AssistantChatIn,
    AssistantChatOut,
    AssistantConfirmIn,
    AssistantDownloadOut,
    AssistantSettingsIn,
    AssistantStatusOut,
    PendingActionOut,
)
from ..assistant.crypto import encrypt_secret
from ..assistant.loop import run_chat, run_confirmed, status_payload
from ..assistant.pending import get_download, pop_pending
from ..assistant.providers import AssistantError

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

ALLOWED_PROVIDERS = {"anthropic", "openai"}


@router.get("/status", response_model=AssistantStatusOut)
def assistant_status(user: User = Depends(current_user), db: Session = Depends(get_db)) -> AssistantStatusOut:
    return AssistantStatusOut(**status_payload(user, db))


@router.put("/settings", response_model=AssistantStatusOut)
def save_settings(
    body: AssistantSettingsIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AssistantStatusOut:
    settings = get_settings()
    row = db.get(AssistantSettings, user.id)
    if body.clear:
        if row:
            db.delete(row)
            db.commit()
        return AssistantStatusOut(**status_payload(user, db))
    provider = (body.provider or "").lower().strip()
    if provider and provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provider must be anthropic or openai")
    if row is None:
        row = AssistantSettings(user_id=user.id, provider=provider or settings.assistant_provider, api_key_enc="")
        db.add(row)
    if provider:
        row.provider = provider
    if body.api_key.strip():
        row.api_key_enc = encrypt_secret(settings.secret_key, body.api_key.strip())
    if not row.api_key_enc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "API key is required")
    db.commit()
    return AssistantStatusOut(**status_payload(user, db))


@router.post("/chat", response_model=AssistantChatOut)
def chat(
    body: AssistantChatIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AssistantChatOut:
    try:
        result = run_chat(
            db=db,
            user=user,
            messages=[m.model_dump() for m in body.messages],
            project_id=body.project_id,
        )
    except AssistantError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return _to_out(result)


@router.post("/confirm", response_model=AssistantChatOut)
def confirm(
    body: AssistantConfirmIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AssistantChatOut:
    payload = pop_pending(user.id, body.confirm_id)
    if payload is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nothing to confirm, or the proposal expired")
    try:
        result = run_confirmed(db=db, user=user, payload=payload)
    except AssistantError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return _to_out(result)


@router.post("/reject")
def reject(
    body: AssistantConfirmIn,
    user: User = Depends(current_user),
) -> Response:
    pop_pending(user.id, body.confirm_id)
    return Response(status_code=204)


@router.get("/downloads/{download_id}")
def download(download_id: str, user: User = Depends(current_user)):
    item = get_download(user.id, download_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Download expired")
    return Response(
        content=item["content"],
        media_type=item.get("media_type") or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{item["filename"]}"'},
    )


def _to_out(result: dict) -> AssistantChatOut:
    return AssistantChatOut(
        reply=result.get("reply") or "",
        pending_actions=[PendingActionOut(**p) for p in result.get("pending_actions") or []],
        confirm_id=result.get("confirm_id"),
        downloads=[AssistantDownloadOut(**d) for d in result.get("downloads") or []],
        configured=bool(result.get("configured", True)),
    )
