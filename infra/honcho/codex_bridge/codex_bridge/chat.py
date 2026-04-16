from __future__ import annotations

import json
from typing import Any, Mapping, Sequence


def normalize_chat_messages(messages: Sequence[Mapping[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    instructions_parts: list[str] = []
    input_items: list[dict[str, Any]] = []

    for message in messages:
        role = message.get("role")
        if role in {"system", "developer"}:
            instruction = _extract_text_content(message.get("content"))
            if instruction:
                instructions_parts.append(instruction)
            continue

        if role == "assistant" and isinstance(message.get("tool_calls"), list):
            content = _extract_text_content(message.get("content"))
            if content:
                input_items.append({"role": "assistant", "content": content})
            for tool_call in message.get("tool_calls", []):
                converted = _convert_assistant_tool_call(tool_call)
                if converted is not None:
                    input_items.append(converted)
            continue

        if role == "tool":
            converted = _convert_tool_result_message(message)
            if converted is not None:
                input_items.append(converted)
            continue

        input_items.append(_copy_message(message))

    return "\n\n".join(instructions_parts), input_items


def build_responses_request(body: Mapping[str, Any]) -> dict[str, Any]:
    instructions, input_items = normalize_chat_messages(body.get("messages", []))
    payload: dict[str, Any] = {
        "model": body["model"],
        "input": input_items,
        "store": False,
    }

    json_instruction = _json_instruction(body.get("response_format"))
    if json_instruction:
        instructions = _combine_instructions(instructions, json_instruction)
    instructions = instructions or "You are a helpful assistant."
    if instructions:
        payload["instructions"] = instructions

    tools = [_convert_tool(tool) for tool in body.get("tools", [])]
    tools = [tool for tool in tools if tool is not None]
    if tools:
        payload["tools"] = tools

    tool_choice = _convert_tool_choice(body.get("tool_choice"))
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice

    return payload


def _copy_message(message: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in message.items() if value is not None and key != "reasoning_details"}


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if not isinstance(item, Mapping):
                continue
            if item.get("type") in {"text", "output_text", "input_text"}:
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())
        return "\n".join(text_parts)
    return ""


def _combine_instructions(existing: str, extra: str) -> str:
    if existing and extra:
        return f"{existing}\n\n{extra}"
    return existing or extra


def _convert_tool(tool: Any) -> dict[str, Any] | None:
    if not isinstance(tool, Mapping):
        return None

    if tool.get("type") != "function":
        return dict(tool)

    function = tool.get("function")
    if not isinstance(function, Mapping):
        return None

    converted = {
        "type": "function",
        "name": function["name"],
        "parameters": function.get("parameters") or {"type": "object", "properties": {}},
    }
    if function.get("description"):
        converted["description"] = function["description"]
    return converted


def _convert_tool_choice(tool_choice: Any) -> Any:
    if tool_choice in {None, "auto", "none", "required"}:
        return tool_choice
    if isinstance(tool_choice, Mapping) and tool_choice.get("type") == "function":
        function = tool_choice.get("function")
        if isinstance(function, Mapping) and function.get("name"):
            return {"type": "function", "name": function["name"]}
    return tool_choice


def _json_instruction(response_format: Any) -> str:
    if not isinstance(response_format, Mapping):
        return ""

    response_type = response_format.get("type")
    if response_type == "json_object":
        return (
            "Return a single valid JSON object. Do not include markdown fences or extra explanatory text."
        )

    if response_type != "json_schema":
        return ""

    json_schema = response_format.get("json_schema")
    if not isinstance(json_schema, Mapping):
        return ""

    name = json_schema.get("name") or "response"
    schema = json_schema.get("schema") or {}
    schema_json = json.dumps(schema, sort_keys=True)
    return (
        f"Return JSON only and make sure it matches the JSON schema named {name}. "
        "Do not include markdown fences or extra explanatory text.\n"
        f"Schema: {schema_json}"
    )


def _convert_assistant_tool_call(tool_call: Any) -> dict[str, Any] | None:
    if not isinstance(tool_call, Mapping):
        return None
    function = tool_call.get("function")
    if not isinstance(function, Mapping):
        return None
    name = function.get("name")
    arguments = function.get("arguments")
    call_id = tool_call.get("id")
    if not isinstance(name, str) or not name or not isinstance(call_id, str) or not call_id:
        return None
    return {
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments or {}),
    }


def _convert_tool_result_message(message: Mapping[str, Any]) -> dict[str, Any] | None:
    tool_call_id = message.get("tool_call_id")
    if not isinstance(tool_call_id, str) or not tool_call_id:
        return None
    content = _extract_text_content(message.get("content"))
    if not content and message.get("content") is not None:
        content = str(message.get("content"))
    return {
        "type": "function_call_output",
        "call_id": tool_call_id,
        "output": content,
    }
