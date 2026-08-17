from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from ..config import get_settings

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4.1",
}

# Tests assign a callable here to skip the network.
complete_override: Callable[..., "ModelTurn"] | None = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelTurn:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class AssistantError(Exception):
    pass


def resolve_model(provider: str, override: str = "") -> str:
    settings = get_settings()
    return override or settings.assistant_model or DEFAULT_MODELS.get(provider, DEFAULT_MODELS["anthropic"])


def complete_turn(
    *,
    provider: str,
    api_key: str,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> ModelTurn:
    if complete_override is not None:
        return complete_override(provider=provider, api_key=api_key, system=system, messages=messages, tools=tools)
    if provider == "openai":
        return _openai(api_key, system, messages, tools)
    return _anthropic(api_key, system, messages, tools)


def _anthropic(api_key: str, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
    anth_tools = [
        {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
        for t in tools
    ]
    payload: dict[str, Any] = {
        "model": resolve_model("anthropic"),
        "max_tokens": 2048,
        "system": system,
        "messages": _to_anthropic_messages(messages),
    }
    if anth_tools:
        payload["tools"] = anth_tools
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=60.0,
        )
    except httpx.HTTPError as exc:
        raise AssistantError(f"Anthropic request failed: {exc}") from exc
    if resp.status_code >= 400:
        raise AssistantError(_err_text(resp, "Anthropic"))
    data = resp.json()
    text_parts: list[str] = []
    calls: list[ToolCall] = []
    for block in data.get("content") or []:
        if block.get("type") == "text":
            text_parts.append(block.get("text") or "")
        elif block.get("type") == "tool_use":
            calls.append(ToolCall(id=block.get("id") or "", name=block.get("name") or "", arguments=block.get("input") or {}))
    return ModelTurn(text="\n".join(p for p in text_parts if p).strip(), tool_calls=calls)


def _openai(api_key: str, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
    oai_tools = [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]
    oai_messages = [{"role": "system", "content": system}, *_to_openai_messages(messages)]
    payload: dict[str, Any] = {
        "model": resolve_model("openai"),
        "messages": oai_messages,
        "max_tokens": 2048,
    }
    if oai_tools:
        payload["tools"] = oai_tools
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"authorization": f"Bearer {api_key}", "content-type": "application/json"},
            json=payload,
            timeout=60.0,
        )
    except httpx.HTTPError as exc:
        raise AssistantError(f"OpenAI request failed: {exc}") from exc
    if resp.status_code >= 400:
        raise AssistantError(_err_text(resp, "OpenAI"))
    choice = (resp.json().get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    calls: list[ToolCall] = []
    for raw in msg.get("tool_calls") or []:
        fn = raw.get("function") or {}
        try:
            arguments = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        calls.append(ToolCall(id=raw.get("id") or "", name=fn.get("name") or "", arguments=arguments))
    return ModelTurn(text=(msg.get("content") or "").strip(), tool_calls=calls)


def _err_text(resp: httpx.Response, vendor: str) -> str:
    try:
        body = resp.json()
        detail = body.get("error", body)
        if isinstance(detail, dict):
            return f"{vendor} error {resp.status_code}: {detail.get('message') or detail}"
        return f"{vendor} error {resp.status_code}: {detail}"
    except Exception:
        return f"{vendor} error {resp.status_code}: {resp.text[:400]}"


def _to_anthropic_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    pending_tools: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        if role == "tool":
            pending_tools.append(
                {"type": "tool_result", "tool_use_id": msg.get("tool_call_id"), "content": str(msg.get("content") or "")}
            )
            continue
        if pending_tools:
            out.append({"role": "user", "content": pending_tools})
            pending_tools = []
        if role == "assistant" and msg.get("tool_calls"):
            content: list[dict[str, Any]] = []
            if msg.get("content"):
                content.append({"type": "text", "text": msg["content"]})
            for call in msg["tool_calls"]:
                content.append(
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call.get("arguments") or {},
                    }
                )
            out.append({"role": "assistant", "content": content})
        elif role in {"user", "assistant"}:
            out.append({"role": role, "content": msg.get("content") or ""})
    if pending_tools:
        out.append({"role": "user", "content": pending_tools})
    if not out:
        out.append({"role": "user", "content": "Hello"})
    if out[0]["role"] != "user":
        out.insert(0, {"role": "user", "content": "(continue)"})
    return out


def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        if role == "tool":
            out.append({"role": "tool", "tool_call_id": msg.get("tool_call_id"), "content": str(msg.get("content") or "")})
        elif role == "assistant" and msg.get("tool_calls"):
            tool_calls = []
            for call in msg["tool_calls"]:
                tool_calls.append(
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {"name": call["name"], "arguments": json.dumps(call.get("arguments") or {})},
                    }
                )
            out.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls})
        elif role in {"user", "assistant"}:
            out.append({"role": role, "content": msg.get("content") or ""})
    return out
