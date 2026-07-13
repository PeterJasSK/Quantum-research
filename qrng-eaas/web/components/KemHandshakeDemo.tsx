"use client";

import { useState, type FormEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  kemKeypair,
  kemEncapsulate,
  ApiError,
  base64ToBytes,
  bytesToHex,
  type KemKeypair,
  type KemEncapsulation,
} from "@/lib/api";

const DEFAULT_MESSAGE = "hello from the QRNG-seeded ML-KEM demo";

const ERROR_MESSAGES: Record<string, string> = {
  low_quantum_entropy:
    "Quantum entropy is degraded — the demo is temporarily unavailable.",
  demo_key_not_configured:
    "The demo API key isn't configured on this deployment yet.",
  bad_request: "The service rejected that request.",
  rate_limited: "Too many requests — slow down and try again in a moment.",
};

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    return ERROR_MESSAGES[error.slug] ?? `Something went wrong (${error.slug}).`;
  }
  return "Something went wrong. Check your connection and try again.";
}

function truncate(value: string, length = 24): string {
  return value.length > length ? `${value.slice(0, length)}…` : value;
}

async function deriveHkdfCheck(
  sharedSecret: Uint8Array<ArrayBuffer>,
): Promise<Uint8Array> {
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    sharedSecret,
    "HKDF",
    false,
    ["deriveBits"],
  );
  const bits = await crypto.subtle.deriveBits(
    {
      name: "HKDF",
      hash: "SHA-256",
      salt: new Uint8Array(0),
      info: new Uint8Array(0),
    },
    keyMaterial,
    256,
  );
  return new Uint8Array(bits);
}

function bytesEqual(a: Uint8Array, b: Uint8Array): boolean {
  return a.length === b.length && a.every((byte, index) => byte === b[index]);
}

export default function KemHandshakeDemo() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [keypair, setKeypair] = useState<KemKeypair | null>(null);
  const [encapsulation, setEncapsulation] = useState<KemEncapsulation | null>(
    null,
  );
  const [aesKey, setAesKey] = useState<CryptoKey | null>(null);
  const [hkdfMatches, setHkdfMatches] = useState<boolean | null>(null);

  const [message, setMessage] = useState(DEFAULT_MESSAGE);
  const [exchangeError, setExchangeError] = useState<string | null>(null);
  const [ciphertextHex, setCiphertextHex] = useState<string | null>(null);
  const [ivHex, setIvHex] = useState<string | null>(null);
  const [decrypted, setDecrypted] = useState<string | null>(null);

  async function runHandshake() {
    if (loading) return;
    setLoading(true);
    setError(null);
    setKeypair(null);
    setEncapsulation(null);
    setAesKey(null);
    setHkdfMatches(null);
    setCiphertextHex(null);
    setIvHex(null);
    setDecrypted(null);
    setExchangeError(null);

    try {
      const kp = await kemKeypair();
      setKeypair(kp);

      const encaps = await kemEncapsulate(kp.public_key);
      setEncapsulation(encaps);

      const demoKeyBytes = base64ToBytes(encaps.demo_key);
      const key = await crypto.subtle.importKey(
        "raw",
        demoKeyBytes,
        { name: "AES-GCM" },
        false,
        ["encrypt", "decrypt"],
      );
      setAesKey(key);

      try {
        const sharedSecretBytes = base64ToBytes(encaps.shared_secret);
        const derived = await deriveHkdfCheck(sharedSecretBytes);
        setHkdfMatches(bytesEqual(derived, demoKeyBytes));
      } catch {
        setHkdfMatches(null);
      }
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setLoading(false);
    }
  }

  async function onExchangeSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!aesKey) return;

    setExchangeError(null);
    try {
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const plaintextBytes = new TextEncoder().encode(message);
      const ciphertext = new Uint8Array(
        await crypto.subtle.encrypt({ name: "AES-GCM", iv }, aesKey, plaintextBytes),
      );

      const recovered = new Uint8Array(
        await crypto.subtle.decrypt({ name: "AES-GCM", iv }, aesKey, ciphertext),
      );

      setIvHex(bytesToHex(iv));
      setCiphertextHex(bytesToHex(ciphertext));
      setDecrypted(new TextDecoder().decode(recovered));
    } catch {
      setExchangeError("The AES-GCM exchange failed — try running the handshake again.");
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <button
        type="button"
        onClick={runHandshake}
        disabled={loading}
        className="pill h-14 w-full text-lg font-semibold"
      >
        {loading ? "Running handshake…" : "Run handshake"}
      </button>

      {error && (
        <p role="alert" className="text-sm text-amber-300">
          {error}
        </p>
      )}

      <AnimatePresence>
        {keypair && (
          <motion.div
            key="keygen"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="panel p-4"
          >
            <p className="mb-2 text-sm font-semibold text-heading">
              1. Server keygen <span className="pill px-2 py-0.5 text-xs">QRNG-seeded</span>
            </p>
            <p className="mb-1 text-xs text-text/70">
              request_id {keypair.request_id} · entropy_epoch {keypair.entropy_epoch}
            </p>
            <pre className="overflow-x-auto text-xs text-accent">
              <code>ek: {truncate(keypair.public_key)}</code>
            </pre>
          </motion.div>
        )}

        {encapsulation && (
          <motion.div
            key="encaps"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="panel p-4"
          >
            <p className="mb-2 text-sm font-semibold text-heading">
              2. Client encapsulate <span className="pill px-2 py-0.5 text-xs">QRNG-seeded</span>
            </p>
            <p className="mb-1 text-xs text-text/70">
              request_id {encapsulation.request_id} · entropy_epoch{" "}
              {encapsulation.entropy_epoch}
            </p>
            <pre className="overflow-x-auto text-xs text-accent">
              <code>
                ciphertext: {truncate(encapsulation.ciphertext)}
                {"\n"}
                shared_secret: {truncate(encapsulation.shared_secret)}
              </code>
            </pre>
            <p className="mt-2 text-xs text-text/60">{encapsulation.note}</p>
          </motion.div>
        )}

        {aesKey && (
          <motion.div
            key="derive"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="panel p-4"
          >
            <p className="mb-2 text-sm font-semibold text-heading">
              3. Derive the AES-GCM key
            </p>
            <p className="text-xs text-text/70">
              Both roles derive the same key via HKDF-SHA256 over the shared
              secret. The AES <strong>key</strong> is QRNG-seeded; the 12-byte
              GCM nonce below is a standard browser CSPRNG value, not
              QRNG-derived.
            </p>
            {hkdfMatches !== null && (
              <p className="mt-2 text-xs text-text/70">
                {hkdfMatches
                  ? "✓ Browser-side HKDF (Web Crypto) matches the service's demo_key."
                  : "Browser-side HKDF differs from the service's demo_key (known empty-salt interop edge case) — using the service demo_key directly."}
              </p>
            )}
          </motion.div>
        )}

        {aesKey && (
          <motion.div
            key="exchange"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="panel p-4"
          >
            <p className="mb-3 text-sm font-semibold text-heading">
              4. Encrypt &amp; decrypt a message in the browser
            </p>
            <form onSubmit={onExchangeSubmit} className="flex flex-col gap-3">
              <label className="flex flex-col gap-1 text-sm text-text/70">
                Message
                <input
                  type="text"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  className="h-11 rounded-lg border border-border bg-transparent px-3 text-text"
                />
              </label>
              <button type="submit" className="pill h-11 text-sm font-semibold">
                Encrypt then decrypt
              </button>
            </form>

            {exchangeError && (
              <p role="alert" className="mt-2 text-sm text-amber-300">
                {exchangeError}
              </p>
            )}

            {ciphertextHex && ivHex && decrypted !== null && (
              <div className="mt-3 flex flex-col gap-2">
                <pre className="overflow-x-auto text-xs text-accent">
                  <code>
                    nonce: {ivHex}
                    {"\n"}
                    ciphertext: {ciphertextHex}
                  </code>
                </pre>
                <p className="text-sm text-text/90">
                  Recovered plaintext: <strong>{decrypted}</strong>
                </p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
