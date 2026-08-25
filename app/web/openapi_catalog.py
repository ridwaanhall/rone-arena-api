from __future__ import annotations

import json
import html
import re
from copy import deepcopy
from typing import Any

from fastapi import FastAPI

WEB_GROUPS: tuple[str, ...] = ("user", "heroes", "academy", "addon")

GROUP_META: dict[str, dict[str, str]] = {
    "user": {
        "title": "User",
        "description": "Authentication and player profile APIs.",
    },
    "heroes": {
        "title": "Heroes",
        "description": "Hero analytics and gameplay data APIs.",
    },
    "academy": {
        "title": "Academy",
        "description": "Guide, build, emblem, and meta resources.",
    },
    "addon": {
        "title": "Addon",
        "description": "Utility APIs such as calculators and IP tools.",
    },
}


def _resolve_schema(schema: dict[str, Any], component_schemas: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {}

    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return deepcopy(schema)

    prefix = "#/components/schemas/"
    if not ref.startswith(prefix):
        return deepcopy(schema)

    component_name = ref[len(prefix):]
    resolved_component = component_schemas.get(component_name, {})
    if not isinstance(resolved_component, dict):
        return deepcopy(schema)

    resolved = deepcopy(resolved_component)
    for key, value in schema.items():
        if key == "$ref":
            continue
        resolved[key] = deepcopy(value)
    return resolved


def _normalize_default(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _build_parameter(parameter: dict[str, Any], component_schemas: dict[str, Any]) -> dict[str, Any]:
    schema = _resolve_schema(parameter.get("schema", {}), component_schemas)
    item_schema = _resolve_schema(schema.get("items", {}), component_schemas)

    enum_values = schema.get("enum")
    if enum_values is None and schema.get("type") == "array":
        enum_values = item_schema.get("enum")

    if not isinstance(enum_values, list):
        enum_values = []

    default_value = schema.get("default")
    type_name = schema.get("type", "string")
    is_array = type_name == "array"
    option_values: list[str] = []

    if enum_values:
        option_values = [str(value) for value in enum_values]
    elif is_array and isinstance(default_value, list) and all(isinstance(item, str) for item in default_value):
        option_values = [str(item) for item in default_value]

    default_selected: list[str] = []
    if isinstance(default_value, list):
        default_selected = [str(item) for item in default_value]

    description_text = parameter.get("description") or schema.get("description") or ""

    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    min_items = schema.get("minItems")
    max_items = schema.get("maxItems")
    min_length = schema.get("minLength")
    max_length = schema.get("maxLength")

    input_type = "text"
    if type_name in {"integer", "number"}:
        input_type = "number"

    param_name = parameter.get("name", "")
    title = schema.get("title") or ""

    return {
        "name": param_name,
        "title": title,
        "label": title if title else param_name,
        "location": parameter.get("in", "query"),
        "required": bool(parameter.get("required", False)),
        "description": description_text,
        "description_html": _render_inline_markdown(str(description_text)),
        "enum_values": enum_values,
        "option_values": option_values,
        "default": default_value,
        "default_selected": default_selected,
        "default_display": _normalize_default(default_value),
        "type": type_name,
        "item_type": item_schema.get("type", "string"),
        "is_array": is_array,
        "input_type": input_type,
        "minimum": minimum,
        "maximum": maximum,
        "min_items": min_items,
        "max_items": max_items,
        "min_length": min_length,
        "max_length": max_length,
    }


def _build_request_body(operation: dict[str, Any], component_schemas: dict[str, Any]) -> dict[str, Any] | None:
    request_body = operation.get("requestBody", {})
    if not isinstance(request_body, dict):
        return None

    content = request_body.get("content", {})
    if not isinstance(content, dict):
        return None

    app_json = content.get("application/json", {})
    if not isinstance(app_json, dict):
        return None

    schema = _resolve_schema(app_json.get("schema", {}), component_schemas)

    example_data = app_json.get("example")
    if example_data is None:
        examples = app_json.get("examples", {})
        if isinstance(examples, dict) and examples:
            first_example = next(iter(examples.values()))
            if isinstance(first_example, dict):
                example_data = first_example.get("value")

    if example_data is None:
        example_data = schema.get("example")

    if example_data is None:
        properties = schema.get("properties", {})
        if isinstance(properties, dict) and properties:
            generated_example: dict[str, Any] = {}
            for prop_name, prop_schema in properties.items():
                if not isinstance(prop_schema, dict):
                    continue
                if "example" in prop_schema:
                    generated_example[prop_name] = prop_schema["example"]
                    continue
                if "default" in prop_schema:
                    generated_example[prop_name] = prop_schema["default"]
            if generated_example:
                example_data = generated_example

    # Do not render request body input for endpoints that do not define a meaningful body.
    if example_data is None and not request_body.get("required", False):
        return None

    if example_data is None:
        example_data = {}

    try:
        example_json = json.dumps(example_data, indent=2, ensure_ascii=True)
    except (TypeError, ValueError):
        example_json = "{}"

    return {
        "required": bool(request_body.get("required", False)),
        "example_json": example_json,
        "content_type": "application/json",
    }


def _to_web_path(group: str, api_path: str) -> str:
    if group == "heroes":
        suffix = api_path.removeprefix("/api")
    else:
        suffix = api_path.removeprefix(f"/api/{group}")

    if not suffix:
        return f"/web/{group}"

    if not suffix.startswith("/"):
        suffix = f"/{suffix}"
    return f"/web/{group}{suffix}"


def _render_inline_markdown(text: str) -> str:
    escaped = html.escape(text)

    def _bold_replacement(match: re.Match[str]) -> str:
        return f'<strong class="font-semibold text-zinc-100">{match.group(1)}</strong>'

    def _code_replacement(match: re.Match[str]) -> str:
        return (
            f'<code class="border border-zinc-700 px-1 py-0.5 '
            f'font-mono text-[11px] text-zinc-200">{match.group(1)}</code>'
        )

    escaped = re.sub(r"\*\*(.+?)\*\*", _bold_replacement, escaped)
    escaped = re.sub(r"`([^`]+)`", _code_replacement, escaped)
    return escaped


def _render_description_html(text: str) -> str:
    if not text.strip():
        return ""

    lines = text.splitlines()
    blocks: list[str] = []
    list_open_stack: list[bool] = []

    def list_class_for_depth(depth: int) -> str:
        if depth == 1:
            return "my-2 list-disc space-y-1 pl-5 text-zinc-300"
        return "mt-1 list-disc space-y-1 pl-5 text-zinc-300"

    def close_lists(target_depth: int = 0) -> None:
        while len(list_open_stack) > target_depth:
            if list_open_stack[-1]:
                blocks.append("</li>")
            blocks.append("</ul>")
            list_open_stack.pop()

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            close_lists(0)
            continue

        list_match = re.match(r"^(?P<indent>\s*)-\s+(?P<item>.+)$", line)
        if list_match:
            indent = list_match.group("indent").replace("\t", "    ")
            depth = max(1, (len(indent) // 2) + 1)
            item_content = list_match.group("item")

            if depth > len(list_open_stack):
                while len(list_open_stack) < depth:
                    current_depth = len(list_open_stack) + 1
                    blocks.append(f'<ul class="{list_class_for_depth(current_depth)}">')
                    list_open_stack.append(False)
            elif depth < len(list_open_stack):
                close_lists(depth)

            if list_open_stack[depth - 1]:
                blocks.append("</li>")
                list_open_stack[depth - 1] = False

            blocks.append(f"<li>{_render_inline_markdown(item_content)}")
            list_open_stack[depth - 1] = True
            continue

        close_lists(0)
        blocks.append(
            f"<p class=\"my-2 leading-6 text-zinc-300\">{_render_inline_markdown(line)}</p>"
        )

    close_lists(0)
    return "".join(blocks)


def _extract_response_example(operation: dict[str, Any]) -> str | None:
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return None

    for code in ("200", "201"):
        resp = responses.get(code, {})
        if not isinstance(resp, dict):
            continue
        content = resp.get("content", {})
        if not isinstance(content, dict):
            continue
        app_json = content.get("application/json", {})
        if not isinstance(app_json, dict):
            continue
        example = app_json.get("example")
        if example is not None:
            try:
                return json.dumps(example, indent=2, ensure_ascii=True)
            except (TypeError, ValueError):
                return None

    return None


def get_group_operations(app: FastAPI, group: str) -> list[dict[str, Any]]:
    if group not in WEB_GROUPS:
        return []

    spec = app.openapi()
    paths = spec.get("paths", {})
    components = spec.get("components", {})

    if not isinstance(paths, dict) or not isinstance(components, dict):
        return []

    component_schemas = components.get("schemas", {})
    if not isinstance(component_schemas, dict):
        component_schemas = {}

    operations: list[dict[str, Any]] = []

    for api_path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method, operation in path_item.items():
            method_name = str(method).upper()
            if method_name not in {"GET", "POST"}:
                continue
            if not isinstance(operation, dict):
                continue

            tags = operation.get("tags", [])
            if not isinstance(tags, list) or not tags:
                continue
            if tags[0] != group:
                continue

            parameters = operation.get("parameters", [])
            parsed_parameters: list[dict[str, Any]] = []
            if isinstance(parameters, list):
                for parameter in parameters:
                    if not isinstance(parameter, dict):
                        continue
                    location = parameter.get("in")
                    if location not in {"query", "path"}:
                        continue
                    parsed_parameters.append(_build_parameter(parameter, component_schemas))

            request_body = _build_request_body(operation, component_schemas)
            security = operation.get("security", [])
            requires_auth = False
            if isinstance(security, list):
                requires_auth = any(
                    isinstance(item, dict) and "HTTPBearer" in item
                    for item in security
                )

            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                operation_id = f"{method_name.lower()}_{api_path.strip('/').replace('/', '_')}"

            response_example_json = _extract_response_example(operation)

            operations.append(
                {
                    "operation_id": operation_id,
                    "method": method_name,
                    "api_path": api_path,
                    "web_path": _to_web_path(group, api_path),
                    "summary": operation.get("summary") or operation_id,
                    "description": operation.get("description") or "",
                    "description_html": _render_description_html(str(operation.get("description") or "")),
                    "parameters": parsed_parameters,
                    "request_body": request_body,
                    "requires_auth": requires_auth,
                    "deprecated": bool(operation.get("deprecated", False)),
                    "response_example_json": response_example_json,
                }
            )

    # Preserve operation order as produced by OpenAPI generation, which follows router declaration order.
    return operations


def find_group_operation(
    operations: list[dict[str, Any]],
    expected_web_path: str,
    method: str | None = None,
) -> dict[str, Any] | None:
    normalized = expected_web_path.rstrip("/") or "/"
    method_name = method.upper() if method else None

    for operation in operations:
        if operation["web_path"].rstrip("/") != normalized:
            continue
        if method_name and operation["method"] != method_name:
            continue
        return operation
    return None
