"""EPIC 13 Decision 8: stateless Streamable-HTTP MCP server.

`handle(request_body, api_key)` speaks MCP's JSON-RPC 2.0 directly -- no `mcp`
SDK, no long-lived SSE session store (which would fight Vercel's stateless 10s
serverless model). Each call carries its own context; `X-API-Key` is passed
through per call.

tools/call dispatches into the same `qeaas.generation` / `qeaas.dice` /
`qeaas.kem` / `qeaas.receipts` functions the REST routes use -- one
implementation, two surfaces. Premium tools validate the key, respect the
low-entropy gate, enforce the per-key quota, and write the same usage/issue
logs as the REST layer, so MCP cannot be used to bypass anti-abuse controls.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any, Callable

from pydantic import ValidationError

from qeaas import agent, db, dice, generation, kem, ratelimit, receipts
from qeaas.auth import require_api_key
from qeaas.errors import ApiError
from qeaas.gate import entropy_level
from qeaas.schemas import (
    DiceRequest,
    KemEncapsulateRequest,
    KemKeypairRequest,
    VerifyRequest,
)

# JSON-RPC error codes: standard + one application code for ApiError mapping.
_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602
_INTERNAL_ERROR = -32603
_API_ERROR = -32001

_DEMO_SECRET_KEY_NOTE = (
    "demo only -- in production the keypair is generated client-side and the "
    "secret key never leaves the holder"
)
_DEMO_SHARED_SECRET_NOTE = (
    "demo only -- decapsulation happens client-side on the holder of the "
    "secret key; this response is for local round-trip verification"
)


# --- JSON-RPC envelope helpers ----------------------------------------------


def _result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(
    request_id: Any, code: int, message: str, data: Any | None = None
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


class _ToolError(Exception):
    """Raised inside a tool handler; carries a JSON-RPC error code + message."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


# --- Premium gate (mirrors the REST dependency chain) -----------------------


def _require_premium(api_key: str | None, quota_cost: int) -> db.ApiKeyRow:
    if entropy_level() == "degraded":
        raise _ToolError(_API_ERROR, "low_quantum_entropy", {"status": 503})
    try:
        row = require_api_key(api_key)
        ratelimit.enforce_key(row, quota_cost)
    except ApiError as exc:
        raise _ToolError(_API_ERROR, exc.code, {"status": exc.status_code}) from exc
    return row


def _validate(model: type, arguments: dict[str, Any]) -> Any:
    try:
        return model.model_validate(arguments)
    except ValidationError as exc:
        raise _ToolError(_INVALID_PARAMS, "bad_request", {"detail": exc.errors()}) from exc


# --- Tool handlers (return the same payloads as the REST routes) ------------


def _tool_random(arguments: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    n = arguments.get("bytes", 32)
    if not isinstance(n, int) or not (1 <= n <= 64):
        raise _ToolError(_INVALID_PARAMS, "bad_request")
    data = generation.random_bytes(n)
    return {"bytes": n, "format": "base64", "data": base64.b64encode(data).decode("ascii")}


def _tool_dice(arguments: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    body = _validate(DiceRequest, arguments)
    rolls, drawn = dice.roll(body.sides, body.count)
    return {
        "sides": body.sides,
        "count": body.count,
        "rolls": rolls,
        "format": "base64",
        "bytes_used": base64.b64encode(drawn).decode("ascii"),
        "bytes_count": len(drawn),
    }


def _tool_verify(arguments: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    body = _validate(VerifyRequest, arguments)
    verified, provenance, note = receipts.verify(body.request_id, body.receipt)
    return {
        "request_id": body.request_id,
        "verified": verified,
        "provenance": provenance,
        "note": note,
    }


def _tool_random_bytes(arguments: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    size = arguments.get("size")
    fmt = arguments.get("format", "hex")
    if not isinstance(size, int) or not (32 <= size <= 4096):
        raise _ToolError(_INVALID_PARAMS, "bad_request")
    if fmt not in ("hex", "base64"):
        raise _ToolError(_INVALID_PARAMS, "bad_request")
    key = _require_premium(api_key, size)
    response = generation.issue_v1(size, fmt)
    db.insert_usage_log(key.key_hash, "/v1/random/bytes", size)
    db.insert_issue_log(
        str(response["request_id"]),
        key.key_hash,
        "/v1/random/bytes",
        size,
        int(response["entropy_epoch"]),
    )
    return _jsonable(response)


def _tool_kem_keypair(arguments: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    body = _validate(KemKeypairRequest, arguments)
    key = _require_premium(api_key, kem.KEYGEN_QUOTA_COST)
    ek, dk = kem.generate_keypair()
    meta = generation.new_issue_meta(kem.KEYGEN_SEED_BYTES)
    payload = {
        **meta,
        "algorithm": kem.ALGORITHM,
        "format": "base64",
        "public_key": base64.b64encode(ek).decode("ascii"),
        "secret_key": base64.b64encode(dk).decode("ascii")
        if body.include_secret_key
        else None,
        "note": _DEMO_SECRET_KEY_NOTE if body.include_secret_key else None,
    }
    db.insert_usage_log(key.key_hash, "/v1/kem/keypair", kem.KEYGEN_SEED_BYTES)
    db.insert_issue_log(
        str(meta["request_id"]),
        key.key_hash,
        "/v1/kem/keypair",
        kem.KEYGEN_SEED_BYTES,
        int(meta["entropy_epoch"]),
    )
    return _jsonable(payload)


def _tool_kem_encapsulate(
    arguments: dict[str, Any], api_key: str | None
) -> dict[str, Any]:
    body = _validate(KemEncapsulateRequest, arguments)
    key = _require_premium(api_key, kem.ENCAPS_QUOTA_COST)
    try:
        ek = base64.b64decode(body.public_key, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise _ToolError(_INVALID_PARAMS, "bad_request") from exc
    shared_secret, ciphertext = kem.encapsulate(ek)
    meta = generation.new_issue_meta(kem.ENCAPS_SEED_BYTES)
    payload = {
        **meta,
        "algorithm": kem.ALGORITHM,
        "format": "base64",
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        "shared_secret": base64.b64encode(shared_secret).decode("ascii")
        if body.include_shared_secret
        else None,
        "demo_key": base64.b64encode(kem.derive_demo_key(shared_secret)).decode("ascii")
        if body.include_shared_secret
        else None,
        "note": _DEMO_SHARED_SECRET_NOTE if body.include_shared_secret else None,
    }
    db.insert_usage_log(key.key_hash, "/v1/kem/encapsulate", kem.ENCAPS_SEED_BYTES)
    db.insert_issue_log(
        str(meta["request_id"]),
        key.key_hash,
        "/v1/kem/encapsulate",
        kem.ENCAPS_SEED_BYTES,
        int(meta["entropy_epoch"]),
    )
    return _jsonable(payload)


def _jsonable(payload: dict[str, Any]) -> dict[str, Any]:
    """Coerce datetimes etc. to JSON-serialisable values (issue meta carries a
    `timestamp` datetime)."""
    return json.loads(json.dumps(payload, default=str))


_TOOL_HANDLERS: dict[str, Callable[[dict[str, Any], str | None], dict[str, Any]]] = {
    "random": _tool_random,
    "dice": _tool_dice,
    "verify": _tool_verify,
    "random_bytes": _tool_random_bytes,
    "kem_keypair": _tool_kem_keypair,
    "kem_encapsulate": _tool_kem_encapsulate,
}


# --- MCP method implementations ---------------------------------------------


def _tool_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": ep.name,
            "description": ep.description,
            "inputSchema": agent.input_schema(ep),
        }
        for ep in agent.tool_endpoints()
    ]


def _capabilities() -> dict[str, Any]:
    return {"tools": {}, "resources": {}, "prompts": {}}


def _initialize() -> dict[str, Any]:
    return {
        "protocolVersion": agent.MCP_PROTOCOL_VERSION,
        "capabilities": _capabilities(),
        "serverInfo": {"name": "qeaas-mcp", "version": agent.API_VERSION},
        "instructions": agent.FRAMING,
    }


_RESOURCE_PUBKEY = "qeaas://pubkey"
_RESOURCE_PROVENANCE = "qeaas://provenance"
_RESOURCE_LLMS = "qeaas://llms.txt"


def _resources() -> list[dict[str, Any]]:
    return [
        {
            "uri": _RESOURCE_PUBKEY,
            "name": "Receipt signing public key",
            "description": "Ed25519 public key (base64) for offline receipt verification.",
            "mimeType": "application/json",
        },
        {
            "uri": _RESOURCE_PROVENANCE,
            "name": "Provenance model",
            "description": "How receipts and /v1/verify establish provenance.",
            "mimeType": "text/markdown",
        },
        {
            "uri": _RESOURCE_LLMS,
            "name": "llms.txt",
            "description": "Plain-text agent index for Q-EaaS.",
            "mimeType": "text/plain",
        },
    ]


def _llms_text() -> str:
    lines = [
        "# Quantum Entropy-as-a-Service (Q-EaaS)",
        "",
        agent.FRAMING,
        "",
        "## Endpoints",
    ]
    for ep in agent.ENDPOINTS:
        auth = " (X-API-Key)" if ep.auth == "api_key" else ""
        lines.append(f"- {ep.method} {ep.path}{auth} -- {ep.summary}")
    links = agent._links()
    lines += [
        "",
        "## Discovery",
        f"- Agent manifest: {links['agent']}",
        f"- Tool descriptors: {links['tools']}",
        f"- Onboarding manifest: {links['manifest']}",
        f"- OpenAPI: {links['openapi']}",
        f"- MCP endpoint: {links['mcp']}",
    ]
    return "\n".join(lines)


def _provenance_text() -> str:
    p = agent._provenance_summary()
    return (
        "# Provenance model\n\n"
        f"{p['note']}\n\n"
        f"- Model: {p['model']}\n"
        f"- Receipt format: `{p['receipt_format']}`\n"
        f"- Public key: {p['public_key_endpoint']}\n"
        f"- Verify: {p['verify_endpoint']}\n"
    )


def _read_resource(uri: str) -> dict[str, Any]:
    if uri == _RESOURCE_PUBKEY:
        text = json.dumps(
            {"algorithm": "Ed25519", "format": "base64", "public_key": receipts.public_key_b64()}
        )
        mime = "application/json"
    elif uri == _RESOURCE_PROVENANCE:
        text = _provenance_text()
        mime = "text/markdown"
    elif uri == _RESOURCE_LLMS:
        text = _llms_text()
        mime = "text/plain"
    else:
        raise _ToolError(_INVALID_PARAMS, "not_found", {"uri": uri})
    return {"contents": [{"uri": uri, "mimeType": mime, "text": text}]}


_PROMPT_NAME = "integrate_qeaas"


def _prompts() -> list[dict[str, Any]]:
    return [
        {
            "name": _PROMPT_NAME,
            "description": "Step-by-step instructions to integrate Q-EaaS.",
            "arguments": [],
        }
    ]


def _prompt_text() -> str:
    steps = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(agent._auth_steps()))
    tools = "\n".join(
        f"- {ep.name}: {ep.method} {ep.path}" for ep in agent.tool_endpoints()
    )
    return (
        f"You are integrating {agent.SERVICE_NAME}.\n\n"
        f"{agent.FRAMING}\n\n"
        f"Auth:\n{steps}\n\n"
        f"Callable tools:\n{tools}\n\n"
        f"Discovery: {agent._links()['agent']}"
    )


def _get_prompt(name: str) -> dict[str, Any]:
    if name != _PROMPT_NAME:
        raise _ToolError(_INVALID_PARAMS, "not_found", {"prompt": name})
    return {
        "description": "Integrate Q-EaaS into an agent runtime.",
        "messages": [
            {"role": "user", "content": {"type": "text", "text": _prompt_text()}}
        ],
    }


def _call_tool(params: dict[str, Any], api_key: str | None) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    handler = _TOOL_HANDLERS.get(name) if isinstance(name, str) else None
    if handler is None:
        raise _ToolError(_INVALID_PARAMS, "not_found", {"tool": name})
    payload = handler(arguments, api_key)
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


# --- Entry point -------------------------------------------------------------


def handle(request_body: dict[str, Any], api_key: str | None) -> dict[str, Any] | None:
    """Dispatch one JSON-RPC 2.0 request. Returns the response object, or `None`
    for notifications (no `id`), which the transport answers with an empty 202."""
    if not isinstance(request_body, dict):
        return _error(None, _INVALID_REQUEST, "invalid_request")

    request_id = request_body.get("id")
    method = request_body.get("method")
    params = request_body.get("params") or {}

    # Notifications carry no id and expect no response.
    if request_id is None and isinstance(method, str) and method.startswith("notifications/"):
        return None

    if not isinstance(method, str):
        return _error(request_id, _INVALID_REQUEST, "invalid_request")

    try:
        if method == "initialize":
            return _result(request_id, _initialize())
        if method == "ping":
            return _result(request_id, {})
        if method == "tools/list":
            return _result(request_id, {"tools": _tool_specs()})
        if method == "tools/call":
            return _result(request_id, _call_tool(params, api_key))
        if method == "resources/list":
            return _result(request_id, {"resources": _resources()})
        if method == "resources/read":
            uri = params.get("uri")
            if not isinstance(uri, str):
                return _error(request_id, _INVALID_PARAMS, "bad_request")
            return _result(request_id, _read_resource(uri))
        if method == "prompts/list":
            return _result(request_id, {"prompts": _prompts()})
        if method == "prompts/get":
            name = params.get("name")
            if not isinstance(name, str):
                return _error(request_id, _INVALID_PARAMS, "bad_request")
            return _result(request_id, _get_prompt(name))
        return _error(request_id, _METHOD_NOT_FOUND, "method_not_found", {"method": method})
    except _ToolError as exc:
        return _error(request_id, exc.code, exc.message, exc.data)
    except ApiError as exc:
        return _error(request_id, _API_ERROR, exc.code, {"status": exc.status_code})
    except Exception:  # noqa: BLE001 -- never leak a stack trace over JSON-RPC
        return _error(request_id, _INTERNAL_ERROR, "internal_error")
