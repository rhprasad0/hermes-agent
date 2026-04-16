from codex_bridge.chat import build_responses_request, normalize_chat_messages


def test_normalize_chat_messages_extracts_instructions_and_input() -> None:
    instructions, input_items = normalize_chat_messages(
        [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": "hello"},
        ]
    )

    assert instructions == "Return JSON only."
    assert input_items == [{"role": "user", "content": "hello"}]


def test_build_responses_request_supplies_default_instructions() -> None:
    payload = build_responses_request(
        body={
            "model": "gpt-5.4-mini",
            "messages": [{"role": "user", "content": "hello"}],
        }
    )

    assert payload["instructions"] == "You are a helpful assistant."
    assert payload["store"] is False


def test_build_responses_request_converts_tools_and_json_schema() -> None:
    payload = build_responses_request(
        body={
            "model": "gpt-5.4-mini",
            "messages": [{"role": "user", "content": "Summarize this."}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup_user",
                        "description": "Lookup a user",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "Answer",
                    "schema": {
                        "type": "object",
                        "properties": {"answer": {"type": "string"}},
                        "required": ["answer"],
                    },
                },
            },
        }
    )

    assert payload["model"] == "gpt-5.4-mini"
    assert payload["tools"][0]["name"] == "lookup_user"
    assert "JSON" in payload["instructions"]
    assert "answer" in payload["instructions"]
