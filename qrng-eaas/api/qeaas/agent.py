"""EPIC 13: the single endpoint catalog + payload builders for agent-first
discovery.

Decision 1 -- one catalog, many renderings. `ENDPOINTS` is the source of truth;
`well_known_agent`, `ai_plugin`, `tool_descriptors`, and `agent_manifest` all
derive from it, so no hand-maintained duplicate endpoint list can drift.

Decision 2 -- schemas come from Pydantic. Input/output JSON Schema are produced
with `Model.model_json_schema()` on `qeaas.schemas`; endpoints without a body
model advertise their query params explicitly.

Decision 5 -- `?profile=` is one catalog, four projections (http / openai-tools
/ anthropic-tools / mcp).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from qeaas import kem, ratelimit
from qeaas.schemas import (
    DiceRequest,
    DiceResponse,
    HealthResponse,
    KemEncapsulateRequest,
    KemEncapsulateResponse,
    KemKeypairRequest,
    KemKeypairResponse,
    PubkeyResponse,
    RandomResponse,
    V1RandomBytesResponse,
    VerifyRequest,
    VerifyResponse,
)
from qeaas.urls import api_url, web_url

API_VERSION = "1.0.0"
MCP_PROTOCOL_VERSION = "2025-06-18"

SERVICE_NAME = "Quantum Entropy-as-a-Service"

# Honest QRNG framing -- repeated verbatim across every discovery surface
# (Locked decision 2 / build-plan framing).
FRAMING = (
    "Q-EaaS supplies high-quality entropy from a quantum random number generator "
    "(QRNG) that seeds a standards HMAC-DRBG (SP 800-90A). Only DRBG-derived bytes, "
    "seeds, and ML-KEM key material are served -- raw QRNG bits are never exposed. "
    "The quantum part is the entropy source; post-quantum resistance comes from "
    "ML-KEM (FIPS 203), not from the randomness itself."
)

VALID_PROFILES = ("http", "openai-tools", "anthropic-tools", "mcp")

# Flat error envelope every endpoint returns on failure (qeaas/errors.py).
ERROR_ENVELOPE = {"error": "<slug>"}
ERROR_SLUGS = [
    "missing_api_key",
    "invalid_api_key",
    "unauthorized",
    "bad_request",
    "not_found",
    "rate_limited",
    "daily_limit_reached",
    "quota_exceeded",
    "low_quantum_entropy",
    "dice_sampling_failed",
]


@dataclass(frozen=True)
class QueryParam:
    name: str
    schema: dict[str, Any]
    required: bool = False


@dataclass(frozen=True)
class Endpoint:
    """One callable endpoint. `name` is the tool identifier used by the
    function-calling / MCP projections."""

    name: str
    method: str
    path: str
    summary: str
    description: str
    auth: str  # "none" | "api_key" | "admin"
    tags: list[str]
    request_model: type[BaseModel] | None = None
    response_model: type[BaseModel] | None = None
    query_params: list[QueryParam] = field(default_factory=list)
    quota_cost: int | None = None  # per-key bytes charged (fixed-cost endpoints)
    quota_note: str | None = None  # for variable-cost endpoints
    is_tool: bool = True  # exposed as a callable tool (function-calling + MCP)


# --- The single source of truth --------------------------------------------

ENDPOINTS: list[Endpoint] = [
    Endpoint(
        name="health",
        method="GET",
        path="/health",
        summary="Service health & entropy level",
        description=(
            "Liveness plus the current quantum-entropy level (healthy/degraded), "
            "pool bytes remaining, DRBG reseed count, and uptime."
        ),
        auth="none",
        tags=["public"],
        response_model=HealthResponse,
        is_tool=False,
    ),
    Endpoint(
        name="random",
        method="GET",
        path="/random",
        summary="Anonymous quantum-seeded random bytes",
        description=(
            "DRBG-derived random bytes (base64), anonymous and rate-limited. "
            "Capped at 64 bytes/request; powers the public dice player."
        ),
        auth="none",
        tags=["public"],
        response_model=RandomResponse,
        query_params=[
            QueryParam(
                "bytes",
                {"type": "integer", "minimum": 1, "maximum": 64, "default": 32},
            )
        ],
    ),
    Endpoint(
        name="dice",
        method="POST",
        path="/dice",
        summary="Roll dice with quantum-seeded randomness",
        description=(
            "Rejection-sampled dice rolls (no modulo bias), anonymous and "
            "rate-limited. Echoes the DRBG bytes drawn for transparency."
        ),
        auth="none",
        tags=["public"],
        request_model=DiceRequest,
        response_model=DiceResponse,
    ),
    Endpoint(
        name="random_bytes",
        method="GET",
        path="/v1/random/bytes",
        summary="Developer entropy endpoint (API key)",
        description=(
            "Canonical developer endpoint: DRBG-derived bytes in hex or base64 "
            "with a signed provenance receipt. Requires X-API-Key; 32..4096 "
            "bytes; per-key rate limit + daily quota."
        ),
        auth="api_key",
        tags=["developer"],
        response_model=V1RandomBytesResponse,
        query_params=[
            QueryParam(
                "size", {"type": "integer", "minimum": 32, "maximum": 4096}, required=True
            ),
            QueryParam(
                "format",
                {"type": "string", "enum": ["hex", "base64"], "default": "hex"},
            ),
        ],
        quota_note="daily quota charged equals the number of bytes requested (size)",
    ),
    Endpoint(
        name="verify",
        method="POST",
        path="/v1/verify",
        summary="Verify a provenance receipt",
        description=(
            "Verify the provenance of an issued value from its request_id and/or "
            "receipt. Provenance only -- never a value-confirmation oracle. "
            "Anonymous, rate-limited."
        ),
        auth="none",
        tags=["verify"],
        request_model=VerifyRequest,
        response_model=VerifyResponse,
    ),
    Endpoint(
        name="pubkey",
        method="GET",
        path="/v1/pubkey",
        summary="Ed25519 receipt-signing public key",
        description=(
            "The published Ed25519 public key for offline verification of "
            "receipts issued by the service."
        ),
        auth="none",
        tags=["verify"],
        response_model=PubkeyResponse,
        is_tool=False,
    ),
    Endpoint(
        name="kem_keypair",
        method="POST",
        path="/v1/kem/keypair",
        summary="QRNG-seeded ML-KEM-768 keypair",
        description=(
            "Generate an ML-KEM-768 (Kyber, post-quantum) keypair seeded from the "
            "QRNG->DRBG chain. Public key always returned; secret key only for the "
            "demo flow (loud demo-only note). Requires X-API-Key."
        ),
        auth="api_key",
        tags=["kem"],
        request_model=KemKeypairRequest,
        response_model=KemKeypairResponse,
        quota_cost=kem.KEYGEN_QUOTA_COST,
    ),
    Endpoint(
        name="kem_encapsulate",
        method="POST",
        path="/v1/kem/encapsulate",
        summary="QRNG-seeded ML-KEM encapsulation",
        description=(
            "Encapsulate against a supplied ML-KEM-768 public key to produce a "
            "ciphertext (and, for the demo, the shared secret). Requires X-API-Key."
        ),
        auth="api_key",
        tags=["kem"],
        request_model=KemEncapsulateRequest,
        response_model=KemEncapsulateResponse,
        quota_cost=kem.ENCAPS_QUOTA_COST,
    ),
]

_BY_NAME: dict[str, Endpoint] = {ep.name: ep for ep in ENDPOINTS}


def endpoint(name: str) -> Endpoint | None:
    return _BY_NAME.get(name)


def tool_endpoints() -> list[Endpoint]:
    """Callable endpoints exposed as function-calling / MCP tools."""
    return [ep for ep in ENDPOINTS if ep.is_tool]


# --- Schema helpers (Decision 2) -------------------------------------------


def _query_schema(ep: Endpoint) -> dict[str, Any]:
    properties = {p.name: p.schema for p in ep.query_params}
    required = [p.name for p in ep.query_params if p.required]
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def input_schema(ep: Endpoint) -> dict[str, Any]:
    if ep.request_model is not None:
        return ep.request_model.model_json_schema()
    if ep.query_params:
        return _query_schema(ep)
    return {"type": "object", "properties": {}}


def output_schema(ep: Endpoint) -> dict[str, Any]:
    if ep.response_model is not None:
        return ep.response_model.model_json_schema()
    return {"type": "object"}


# --- Auth / quota description ------------------------------------------------


def _auth_summary() -> dict[str, Any]:
    return {
        "type": "api_key",
        "header": "X-API-Key",
        "public_endpoints_need_key": False,
        "how_to_obtain": (
            "API keys are admin-minted. Request one from the operator; keys are "
            "revocable and per-key quota-metered. Public endpoints (health, random, "
            "dice, verify, pubkey) need no key."
        ),
    }


def _quotas() -> dict[str, Any]:
    return {
        "anon_ip_per_min": ratelimit.ANON_IP_PER_MIN,
        "anon_daily_bytes": ratelimit.ANON_DAILY_BYTES,
        "tier_daily_quota_bytes": ratelimit.TIER_QUOTAS,
        "tier_rate_limits_per_min": ratelimit.TIER_RATE_LIMITS,
        "default_tier": ratelimit.DEFAULT_TIER,
    }


# --- Link map ----------------------------------------------------------------


def _links() -> dict[str, str]:
    api = api_url()
    web = web_url()
    return {
        "openapi": f"{api}/openapi.json",
        "docs": f"{api}/docs",
        "agent": f"{api}/.well-known/agent.json",
        "ai_plugin": f"{api}/.well-known/ai-plugin.json",
        "mcp_discovery": f"{api}/.well-known/mcp.json",
        "tools": f"{api}/v1/agent/tools",
        "manifest": f"{api}/v1/agent/manifest",
        "pubkey": f"{api}/v1/pubkey",
        "mcp": f"{api}/mcp",
        "llms_txt": f"{web}/llms.txt",
        "llms_full_txt": f"{web}/llms-full.txt",
        "agents_page": f"{web}/agents",
    }


def _capabilities() -> list[str]:
    return [
        "quantum-seeded random bytes (hex/base64) with signed provenance receipts",
        "cryptographic seeds for downstream key derivation",
        "quantum-seeded ML-KEM-768 (Kyber) keypair generation (post-quantum KEM demo)",
        "ML-KEM-768 encapsulation for a supplied public key",
        "offline receipt verification via a published Ed25519 public key",
        "anonymous, rate-limited dice roller",
        "full MCP server (Streamable-HTTP JSON-RPC 2.0) at POST /mcp",
    ]


# --- Builders ----------------------------------------------------------------


def well_known_agent() -> dict[str, Any]:
    """AC-1: the machine-readable agent manifest served at
    `/.well-known/agent.json`."""
    return {
        "name": SERVICE_NAME,
        "description": (
            "Quantum-seeded randomness, cryptographic seeds, and post-quantum "
            "ML-KEM key material as a small HTTP + MCP service."
        ),
        "framing": FRAMING,
        "version": API_VERSION,
        "web_url": web_url(),
        "api_url": api_url(),
        "auth": _auth_summary(),
        "capabilities": _capabilities(),
        "mcp": {
            "endpoint": _links()["mcp"],
            "transport": "streamable-http",
            "protocol_version": MCP_PROTOCOL_VERSION,
        },
        "links": _links(),
    }


def ai_plugin() -> dict[str, Any]:
    """AC-2: minimal ChatGPT-plugin-style manifest pointing at the enriched
    OpenAPI document."""
    links = _links()
    return {
        "schema_version": "v1",
        "name_for_human": "Q-EaaS",
        "name_for_model": "quantum_entropy_as_a_service",
        "description_for_human": (
            "Quantum-seeded randomness, seeds, and post-quantum ML-KEM key material."
        ),
        "description_for_model": FRAMING,
        "auth": {"type": "user_http", "authorization_type": "custom_header"},
        "api": {"type": "openapi", "url": links["openapi"], "is_user_authenticated": False},
        "logo_url": f"{web_url()}/logo.png",
        "contact_email": "peter.jas@everlution.sk",
        "legal_info_url": web_url(),
    }


def well_known_mcp() -> dict[str, Any]:
    """AC-2: MCP discovery document served at `/.well-known/mcp.json`."""
    return {
        "name": "qeaas-mcp",
        "description": "MCP server for Quantum Entropy-as-a-Service.",
        "endpoint": _links()["mcp"],
        "transport": "streamable-http",
        "protocol_version": MCP_PROTOCOL_VERSION,
        "authentication": {
            "type": "api_key",
            "header": "X-API-Key",
            "note": "Premium tools require X-API-Key passed per call.",
        },
    }


def _tool_descriptor(ep: Endpoint) -> dict[str, Any]:
    descriptor: dict[str, Any] = {
        "name": ep.name,
        "description": ep.description,
        "method": ep.method,
        "path": ep.path,
        "auth": ep.auth,
        "input_schema": input_schema(ep),
        "output_schema": output_schema(ep),
    }
    if ep.quota_cost is not None:
        descriptor["quota_cost"] = ep.quota_cost
    if ep.quota_note is not None:
        descriptor["quota_note"] = ep.quota_note
    return descriptor


def tool_descriptors() -> list[dict[str, Any]]:
    """AC-3: one machine-readable descriptor per callable endpoint, ready to
    register in a function-calling / MCP runtime."""
    return [_tool_descriptor(ep) for ep in tool_endpoints()]


# --- Profile projections (Decision 5) ---------------------------------------


def _curl_example(ep: Endpoint) -> str:
    api = api_url()
    auth = ' -H "X-API-Key: $QEAAS_API_KEY"' if ep.auth == "api_key" else ""
    if ep.method == "GET":
        query = ""
        if ep.query_params:
            pairs = "&".join(
                f"{p.name}={p.schema.get('default', '...')}" for p in ep.query_params
            )
            query = f"?{pairs}"
        return f'curl -s{auth} "{api}{ep.path}{query}"'
    body = "{}"
    if ep.request_model is not None:
        example = {
            name: prop.get("default", prop.get("example", "..."))
            for name, prop in (
                ep.request_model.model_json_schema().get("properties", {}).items()
            )
        }
        body = _compact_json(example)
    return (
        f"curl -s -X POST{auth} -H 'content-type: application/json' "
        f"-d '{body}' \"{api}{ep.path}\""
    )


def _compact_json(obj: Any) -> str:
    import json

    return json.dumps(obj, separators=(",", ":"))


def _http_profile() -> list[dict[str, Any]]:
    return [
        {
            "name": ep.name,
            "method": ep.method,
            "path": ep.path,
            "auth": ep.auth,
            "curl": _curl_example(ep),
        }
        for ep in tool_endpoints()
    ]


def _openai_tools_profile() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": ep.name,
                "description": ep.description,
                "parameters": input_schema(ep),
            },
        }
        for ep in tool_endpoints()
    ]


def _anthropic_tools_profile() -> list[dict[str, Any]]:
    return [
        {
            "name": ep.name,
            "description": ep.description,
            "input_schema": input_schema(ep),
        }
        for ep in tool_endpoints()
    ]


def _mcp_profile() -> list[dict[str, Any]]:
    return [
        {
            "name": ep.name,
            "description": ep.description,
            "inputSchema": input_schema(ep),
        }
        for ep in tool_endpoints()
    ]


_PROFILE_BUILDERS = {
    "http": _http_profile,
    "openai-tools": _openai_tools_profile,
    "anthropic-tools": _anthropic_tools_profile,
    "mcp": _mcp_profile,
}


def _auth_steps() -> list[str]:
    return [
        "Public endpoints (health, random, dice, verify, pubkey) need no key -- call them directly.",
        "For developer endpoints, obtain an admin-minted API key from the operator.",
        "Send the key on every premium request as the HTTP header `X-API-Key: <key>`.",
        "Premium responses carry a signed receipt; verify provenance later via POST /v1/verify or the published Ed25519 public key.",
        "Respect the per-key daily quota and rate limit; over-limit returns 429 with a Retry-After header.",
    ]


def _endpoint_catalog() -> list[dict[str, Any]]:
    return [
        {
            "name": ep.name,
            "method": ep.method,
            "path": ep.path,
            "summary": ep.summary,
            "auth": ep.auth,
            "curl": _curl_example(ep),
        }
        for ep in ENDPOINTS
    ]


def _provenance_summary() -> dict[str, Any]:
    return {
        "model": "verify provenance, not the secret",
        "receipt_format": "qeaas1.<b64url(payload)>.<b64url(ed25519_sig)>",
        "public_key_endpoint": _links()["pubkey"],
        "verify_endpoint": f"{api_url()}/v1/verify",
        "note": (
            "Every premium response ships a signed receipt over its metadata "
            "(request_id, size, entropy_epoch, timestamp). Output bytes are never "
            "stored; /v1/verify resolves provenance only."
        ),
    }


def agent_manifest(profile: str | None) -> dict[str, Any]:
    """AC-5: one onboarding document with everything an agent needs. When
    `profile` names a known framework, return the quickstart tailored to it;
    unknown/absent returns the full document with a `note` listing profiles."""
    full: dict[str, Any] = {
        "service": SERVICE_NAME,
        "version": API_VERSION,
        "framing": FRAMING,
        "web_url": web_url(),
        "api_url": api_url(),
        "auth_steps": _auth_steps(),
        "auth": _auth_summary(),
        "endpoints": _endpoint_catalog(),
        "quotas": _quotas(),
        "error_envelope": ERROR_ENVELOPE,
        "error_slugs": ERROR_SLUGS,
        "provenance": _provenance_summary(),
        "mcp": {
            "endpoint": _links()["mcp"],
            "transport": "streamable-http",
            "protocol_version": MCP_PROTOCOL_VERSION,
        },
        "links": _links(),
    }

    if profile in _PROFILE_BUILDERS:
        return {
            "service": SERVICE_NAME,
            "profile": profile,
            "framing": FRAMING,
            "api_url": api_url(),
            "auth_steps": _auth_steps(),
            "quotas": _quotas(),
            "error_envelope": ERROR_ENVELOPE,
            "tools": _PROFILE_BUILDERS[profile](),
        }

    full["note"] = f"Pass ?profile=<{'|'.join(VALID_PROFILES)}> for a framework-shaped quickstart."
    return full
