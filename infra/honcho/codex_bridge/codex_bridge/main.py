from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, HTTPException

from codex_bridge.bridge import create_chat_completion, list_available_models
from codex_bridge.config import DEFAULT_EMBEDDING_MODEL, inbound_api_key
from codex_bridge.embeddings import embed_texts

app = FastAPI(title="codex-bridge")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
def models(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _validate_inbound_auth(authorization)
    return {
        "object": "list",
        "data": [
            {
                "id": model,
                "object": "model",
                "created": 0,
                "owned_by": "openai-codex",
            }
            for model in list_available_models()
        ],
    }


@app.post("/v1/embeddings")
def embeddings(body: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _validate_inbound_auth(authorization)
    raw_input = body.get("input", "")
    if isinstance(raw_input, str):
        inputs = [raw_input]
    elif isinstance(raw_input, list) and all(isinstance(item, str) for item in raw_input):
        inputs = raw_input
    else:
        raise HTTPException(status_code=400, detail="input must be a string or list of strings")

    vectors = embed_texts(inputs)
    model = body.get("model") or DEFAULT_EMBEDDING_MODEL
    return {
        "object": "list",
        "data": [
            {"object": "embedding", "index": index, "embedding": vector}
            for index, vector in enumerate(vectors)
        ],
        "model": model,
        "usage": {
            "prompt_tokens": sum(len(item.split()) for item in inputs),
            "total_tokens": sum(len(item.split()) for item in inputs),
        },
    }


@app.post("/v1/chat/completions")
async def chat_completions(body: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _validate_inbound_auth(authorization)
    _validate_chat_request(body)
    if body.get("stream"):
        raise HTTPException(status_code=501, detail="streaming chat completions are not implemented yet")
    return await create_chat_completion(body)


def _validate_chat_request(body: dict[str, Any]) -> None:
    if not isinstance(body.get("model"), str) or not body["model"].strip():
        raise HTTPException(status_code=400, detail="model is required")

    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=400, detail="messages must be a non-empty list")
    for message in messages:
        if not isinstance(message, dict):
            raise HTTPException(status_code=400, detail="each message must be an object")
        role = message.get("role")
        if not isinstance(role, str) or not role.strip():
            raise HTTPException(status_code=400, detail="each message must include a role")

    tools = body.get("tools") or []
    if not isinstance(tools, list):
        raise HTTPException(status_code=400, detail="tools must be a list when provided")
    for tool in tools:
        if not isinstance(tool, dict):
            raise HTTPException(status_code=400, detail="each tool must be an object")
        if tool.get("type") != "function":
            continue
        function = tool.get("function")
        if not isinstance(function, dict) or not isinstance(function.get("name"), str) or not function["name"].strip():
            raise HTTPException(status_code=400, detail="function tools must include a non-empty function.name")


def _validate_inbound_auth(authorization: str | None) -> None:
    expected = inbound_api_key()
    if not expected:
        return
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="invalid API key")
