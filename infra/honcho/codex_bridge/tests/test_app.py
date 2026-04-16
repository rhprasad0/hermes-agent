from fastapi.testclient import TestClient

from codex_bridge.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_models_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        "codex_bridge.main.list_available_models",
        lambda: ["gpt-5.4-mini", "gpt-5.4"],
    )

    response = client.get("/v1/models")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["data"]] == ["gpt-5.4-mini", "gpt-5.4"]


def test_embeddings_endpoint() -> None:
    response = client.post(
        "/v1/embeddings",
        json={"model": "text-embedding-3-small", "input": ["alpha", "beta"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert len(payload["data"]) == 2
    assert len(payload["data"][0]["embedding"]) == 1536


def test_chat_completions_endpoint(monkeypatch) -> None:
    async def fake_create_chat_completion(body):
        assert body["model"] == "gpt-5.4-mini"
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 123,
            "model": body["model"],
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hello from codex bridge"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        }

    monkeypatch.setattr("codex_bridge.main.create_chat_completion", fake_create_chat_completion)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-5.4-mini",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["choices"][0]["message"]["content"] == "hello from codex bridge"


def test_chat_completions_rejects_malformed_messages() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={"model": "gpt-5.4-mini", "messages": ["oops"]},
    )

    assert response.status_code == 400


def test_chat_completions_rejects_tools_without_function_name() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-5.4-mini",
            "messages": [{"role": "user", "content": "hi"}],
            "tools": [{"type": "function", "function": {}}],
        },
    )

    assert response.status_code == 400
