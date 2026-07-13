# Networking demonstration (EPIC 8)

Where quantum entropy plugs into networking, made concrete with a running handshake
and mapped honestly to real networking use cases.

## What the demo shows

Two roles drive the live `/v1/kem/*` endpoints:

1. **Server keygen** — `POST /v1/kem/keypair` returns a QRNG-seeded ML-KEM-768 keypair.
   Keygen randomness is `generation.random_bytes(64)` (QRNG → DRBG), never raw pool
   bits, fed into `ML_KEM_768.key_derive(seed)` (`api/qeaas/kem.py:47-51`).
2. **Client encapsulate** — `POST /v1/kem/encapsulate` takes the Server's public key
   `ek` and returns a ciphertext + shared secret. Encapsulation randomness is
   `generation.random_bytes(32)`, also QRNG → DRBG, fed into
   `ML_KEM_768._encaps_internal(ek, m)` (`api/qeaas/kem.py:54-67`).
3. **Key derivation** — both roles derive the same 32-byte AES-256-GCM key via
   `HKDF(shared_secret, 32, b"", SHA256)` (`api/qeaas/kem.py:70-76`).
4. **AES-GCM message exchange** — the Server encrypts one message with the derived
   key; the Client decrypts and authenticates it, proving both parties hold the same
   key.
5. **Independent agreement proof** — the Server locally decapsulates
   `ML_KEM_768.decaps(dk, ciphertext)` and asserts the result equals the shared
   secret the Client received — the two parties agree on the secret without either
   ever transmitting it.

Every step logs its QRNG provenance (`request_id`, `entropy_epoch`) from the
service's issue metadata (`api/qeaas/generation.py:new_issue_meta`).

**Run the CLI demo** (the rigorous, reproducible artifact — it locally decapsulates
and asserts agreement, AC-4):

```bash
cd qrng-eaas/api
API_KEY=<key> python -m scripts.kem_handshake --base-url http://localhost:8000
```

**Run the interactive web demo** at `/demo` — the same handshake, visualized live in
the browser with no page reload. The web demo does not decapsulate in the browser
(no JS ML-KEM library); the CLI script is what proves independent agreement.

## Honest framing — entropy, not quantum-resistance

QRNG entropy does not "defeat quantum attackers." It supplies entropy that seeds a
standards DRBG (`generation.random_bytes`, never raw pool bits), which in turn seeds
ML-KEM. The quantum part is the *entropy source*; the quantum *resistance* comes from
ML-KEM (FIPS 203) itself.

`kyber-py` is a pure-Python, educational implementation and is **not
constant-time** — correct for this demo, not for production (production would swap to
`liboqs` on a persistent host).

The AES-GCM **key** in this demo is QRNG-seeded (via the ML-KEM shared secret); the
12-byte GCM **nonce** is a standard CSPRNG value (`os.urandom(12)` in the CLI,
`crypto.getRandomValues` in the browser) — nonce uniqueness matters for GCM safety,
not QRNG provenance.

## Mapping to networking

Five places this entropy chain plugs into real networking, each with one honest
sentence on what QRNG entropy contributes and its scope:

- **Ephemeral TLS/VPN keys (forward secrecy).** QRNG-seeded entropy strengthens the
  randomness behind ephemeral session keys, supporting forward secrecy — it does not
  make the handshake protocol itself quantum-resistant.
- **WireGuard ephemeral keys.** The same QRNG → DRBG entropy chain could seed
  WireGuard's ephemeral X25519 keypairs; this demo shows the entropy path with
  ML-KEM, not a WireGuard integration.
- **SDN control-plane seeding / moving-target defence.** Centralized quantum entropy
  can seed the randomized re-keying or address/path rotation SDN controllers use for
  moving-target defence — again, entropy quality, not a new protocol.
- **ECMP hash salt.** A quantum-seeded random salt for ECMP hashing reduces
  predictable flow-collision patterns across load-balanced paths — it improves salt
  unpredictability, not the hashing algorithm.
- **IoT seed distribution.** Central quantum entropy, distributed to weak-RNG edge
  devices via API-key tiers, upgrades the entropy those devices seed their own local
  RNGs with — the devices still do the RNG work.

The demo above (QRNG-seeded ML-KEM → AES-GCM channel) is the concrete mechanism
behind all five: quantum-sourced entropy feeds a DRBG, the DRBG seeds a
standards-based cryptographic primitive, and the primitive does the actual
networking-relevant work.
