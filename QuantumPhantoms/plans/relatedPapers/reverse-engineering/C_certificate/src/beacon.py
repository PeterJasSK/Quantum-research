"""Public randomness-beacon pulses (target #5; Kavuri C04, NIST Beacon 2.0 format). qiskit-free, offline.

Reads the committed cache repro/data/beacon_pulses.json (written once by repro/fetch_pulses.py) and
verifies every NIST Beacon 2.0 pulse in it:
  signature   RSA PKCS#1 v1.5 / SHA-512 over the serialized fields, NIST certificate from the cache
  output      outputValue = SHA-512(serialized fields ‖ signatureValue)
  prev_link   listValues["previous"] == outputValue of the preceding pulse
  precommit   precommitmentValue of the preceding pulse == SHA-512(localRandomValue)
Serialization: strings and byte fields are 4-byte big-endian length + bytes, cipherSuite/period/
statusCodes are uint32, chainIndex/pulseIndex are uint64 (NIST IR 8213; checked against live pulses).
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

CACHE = Path(__file__).resolve().parents[1] / "repro" / "data" / "beacon_pulses.json"
CHECKS = ("signature", "output", "prev_link", "precommit")


def load_cache(path: str | Path = CACHE) -> dict:
    return json.loads(Path(path).read_text())


def _b(hexstr: str) -> bytes:
    raw = bytes.fromhex(hexstr)
    return struct.pack(">I", len(raw)) + raw


def _s(text: str) -> bytes:
    raw = text.encode("utf-8")
    return struct.pack(">I", len(raw)) + raw


def serialize(p: dict) -> bytes:
    """The signed message of a Beacon 2.0 pulse (every field up to and including statusCode)."""
    ext = p["external"]
    m = (_s(p["uri"]) + _s(p["version"]) + struct.pack(">II", p["cipherSuite"], p["period"])
         + _b(p["certificateId"]) + struct.pack(">QQ", p["chainIndex"], p["pulseIndex"])
         + _s(p["timeStamp"]) + _b(p["localRandomValue"])
         + _b(ext["sourceId"]) + struct.pack(">I", ext["statusCode"]) + _b(ext["value"]))
    for lv in p["listValues"]:
        m += _b(lv["value"])
    return m + _b(p["precommitmentValue"]) + struct.pack(">I", p["statusCode"])


def _previous(p: dict) -> str | None:
    return next((lv["value"] for lv in p["listValues"] if lv["type"] == "previous"), None)


def verify_pulse(p: dict, cert_pem: str) -> dict:
    m = serialize(p)
    try:
        cert = x509.load_pem_x509_certificates(cert_pem.encode())[0]
        cert.public_key().verify(bytes.fromhex(p["signatureValue"]), m, padding.PKCS1v15(), hashes.SHA512())
        sig_ok = True
    except (InvalidSignature, ValueError):
        sig_ok = False
    out_ok = hashlib.sha512(m + bytes.fromhex(p["signatureValue"])).hexdigest().upper() == p["outputValue"].upper()
    return {"signature": sig_ok, "output": out_ok}


def verify_chain(cache: dict) -> list[dict]:
    """One result per cached pulse; prev_link / precommit are None for the first pulse."""
    pulses, certs = cache["pulses"], cache["certificates"]
    results = []
    for i, p in enumerate(pulses):
        r = {"index": i, "pulse_id": pulse_id(p), **verify_pulse(p, certs.get(p["certificateId"], ""))}
        if i == 0:
            r["prev_link"] = r["precommit"] = None
        else:
            q = pulses[i - 1]
            r["prev_link"] = (_previous(p) or "").upper() == q["outputValue"].upper()
            r["precommit"] = (hashlib.sha512(bytes.fromhex(p["localRandomValue"])).hexdigest().upper()
                              == q["precommitmentValue"].upper())
        r["ok"] = all(r[c] is not False for c in CHECKS)
        results.append(r)
    return results


def pulse_id(p: dict) -> str:
    return f"nist:{p['chainIndex']}:{p['pulseIndex']}"


def pulse_output_bytes(p: dict) -> bytes:
    return bytes.fromhex(p["outputValue"])


def pulse_seed_hex(p: dict) -> str:
    """sha256 of the pulse output value: the seed for the hidden test-round mask."""
    return hashlib.sha256(pulse_output_bytes(p)).hexdigest()


def select_verified_pulse(cache: dict, index: int = -1) -> dict:
    """The cached pulse at `index` (Python indexing); refuses a pulse that fails any chain check."""
    results = verify_chain(cache)
    r = results[index]
    if not r["ok"]:
        raise ValueError(f"beacon pulse {r['pulse_id']} fails verification: {r}")
    return cache["pulses"][index]
