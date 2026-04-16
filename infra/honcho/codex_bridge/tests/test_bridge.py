from types import SimpleNamespace

import pytest

from codex_bridge.bridge import _responses_to_chat_completion


class DummyResponse:
    def __init__(self, *, status: str = "completed") -> None:
        self.id = "resp_123"
        self.status = status
        self.output = [
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="output_text", text='{"answer":"ok"}')],
            )
        ]
        self.usage = SimpleNamespace(input_tokens=1, output_tokens=2, total_tokens=3)


def test_responses_to_chat_completion_raises_on_incomplete_response() -> None:
    with pytest.raises(ValueError):
        _responses_to_chat_completion(response=DummyResponse(status="incomplete"), requested_model="gpt-5.4-mini")
