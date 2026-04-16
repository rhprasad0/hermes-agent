from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any, Mapping

import httpx
from openai import OpenAI

from codex_bridge.auth import resolve_runtime_credentials
from codex_bridge.chat import build_responses_request
from codex_bridge.config import DEFAULT_CODEX_CLIENT_VERSION, DEFAULT_MODELS


def list_available_models() -> list[str]:
    creds = resolve_runtime_credentials()
    url = f"{creds.base_url.rstrip('/')}/models?client_version={DEFAULT_CODEX_CLIENT_VERSION}"
    response = httpx.get(url, headers={"Authorization": f"Bearer {creds.access_token}"}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    models = []
    for item in payload.get("models", []):
        if not isinstance(item, Mapping):
            continue
        slug = item.get("slug")
        if not isinstance(slug, str) or not slug:
            continue
        if item.get("supported_in_api") is False:
            continue
        visibility = item.get("visibility")
        if isinstance(visibility, str) and visibility.lower() in {"hidden", "hide"}:
            continue
        if slug not in models:
            models.append(slug)
    for model in DEFAULT_MODELS:
        if model not in models:
            models.append(model)
    return models


async def create_chat_completion(body: Mapping[str, Any]) -> dict[str, Any]:
    request_payload = build_responses_request(body)
    response = await _call_codex_responses(request_payload, force_refresh=False)
    return _responses_to_chat_completion(response=response, requested_model=str(body["model"]))


async def _call_codex_responses(request_payload: Mapping[str, Any], *, force_refresh: bool) -> Any:
    creds = resolve_runtime_credentials(force_refresh=force_refresh)
    try:
        return await asyncio.to_thread(_call_codex_responses_sync, dict(request_payload), creds.access_token, creds.base_url)
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        if status_code == 401 and not force_refresh:
            return await _call_codex_responses(request_payload, force_refresh=True)
        raise


def _call_codex_responses_sync(request_payload: dict[str, Any], access_token: str, base_url: str) -> Any:
    client = OpenAI(api_key=access_token, base_url=base_url)
    try:
        collected_output_items: list[Any] = []
        collected_text_deltas: list[str] = []
        has_function_calls = False
        with client.responses.stream(**request_payload) as stream:
            for event in stream:
                event_type = getattr(event, "type", "")
                if event_type == "response.output_item.done":
                    done_item = getattr(event, "item", None)
                    if done_item is not None:
                        collected_output_items.append(done_item)
                elif event_type in {"response.output_text.delta", "output_text.delta"}:
                    delta = getattr(event, "delta", "")
                    if delta:
                        collected_text_deltas.append(delta)
                elif "function_call" in event_type:
                    has_function_calls = True
            final_response = stream.get_final_response()

        output_items = getattr(final_response, "output", None)
        if isinstance(output_items, list) and not output_items:
            if collected_output_items:
                final_response.output = list(collected_output_items)
            elif collected_text_deltas and not has_function_calls:
                assembled = "".join(collected_text_deltas)
                final_response.output = [
                    SimpleNamespace(
                        type="message",
                        role="assistant",
                        status="completed",
                        content=[SimpleNamespace(type="output_text", text=assembled)],
                    )
                ]
        return final_response
    finally:
        client.close()


def _responses_to_chat_completion(*, response: Any, requested_model: str) -> dict[str, Any]:
    response_status = getattr(response, "status", None)
    if response_status in {"incomplete", "failed"}:
        raise ValueError(f"Codex response did not complete successfully: {response_status}")

    text_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []

    for item in getattr(response, "output", []) or []:
        item_type = _item_get(item, "type")
        if item_type == "message":
            for part in _item_get(item, "content", []) or []:
                if _item_get(part, "type") in {"output_text", "text"}:
                    text = _item_get(part, "text", "")
                    if text:
                        text_parts.append(text)
        elif item_type == "function_call":
            tool_calls.append(
                {
                    "id": _item_get(item, "call_id", ""),
                    "type": "function",
                    "function": {
                        "name": _item_get(item, "name", ""),
                        "arguments": _item_get(item, "arguments", "{}"),
                    },
                }
            )

    message: dict[str, Any] = {"role": "assistant", "content": "".join(text_parts) or None}
    if tool_calls:
        message["tool_calls"] = tool_calls

    usage_obj = getattr(response, "usage", None)
    prompt_tokens = int(getattr(usage_obj, "input_tokens", 0) or 0)
    completion_tokens = int(getattr(usage_obj, "output_tokens", 0) or 0)
    total_tokens = int(getattr(usage_obj, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens))

    return {
        "id": getattr(response, "id", "chatcmpl-codex-bridge"),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": requested_model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": "tool_calls" if tool_calls else "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
    }


def _item_get(obj: Any, key: str, default: Any = None) -> Any:
    value = getattr(obj, key, None)
    if value is None and isinstance(obj, Mapping):
        value = obj.get(key, default)
    return default if value is None else value
