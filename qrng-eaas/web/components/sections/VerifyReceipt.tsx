"use client";

import { useState, type FormEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { verifyReceipt, ApiError, type VerifyResult } from "@/lib/api";

const ERROR_MESSAGES: Record<string, string> = {
  bad_request: "Enter a receipt token or a request ID.",
  rate_limited: "Too many checks — try again in a moment.",
};

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    return ERROR_MESSAGES[error.slug] ?? `Something went wrong (${error.slug}).`;
  }
  return "Something went wrong. Check your connection and try again.";
}

function looksLikeReceipt(input: string): boolean {
  return input.startsWith("qeaas1.") || input.includes(".");
}

function fieldValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ") || "—";
  if (value === null || value === undefined) return "—";
  return String(value);
}

export default function VerifyReceipt() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;

    const trimmed = input.trim();
    setLoading(true);
    setError(null);
    try {
      const verified = looksLikeReceipt(trimmed)
        ? await verifyReceipt({ receipt: trimmed })
        : await verifyReceipt({ request_id: trimmed });
      setResult(verified);
    } catch (err) {
      setResult(null);
      setError(messageFor(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="verify" className="mx-auto max-w-3xl px-4 py-16">
      <h2 className="glow mb-4 text-2xl font-semibold text-heading">
        Verify a receipt
      </h2>
      <p className="mb-6 text-text/90">
        Every developer/KEM issue ships a signed <code>receipt</code>. Paste
        one here — or just its <code>request_id</code> — to check its
        provenance without ever sending the value itself.
      </p>

      <div className="panel flex flex-col gap-6 p-6">
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-2 text-sm text-text/70">
            Paste a receipt or request ID
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="qeaas1.… or a bare request_id"
              className="min-h-24 w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm text-text"
            />
          </label>
          <button
            type="submit"
            disabled={loading || input.trim().length === 0}
            className="pill h-14 w-full text-lg font-semibold"
          >
            {loading ? "Verifying…" : "Verify"}
          </button>
        </form>

        {error && (
          <p role="alert" className="text-sm text-amber-300">
            {error}
          </p>
        )}

        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="panel flex flex-col gap-3 p-4"
            >
              <span
                className={`pill w-fit px-4 py-1 text-sm font-semibold ${
                  result.verified ? "" : "bg-amber-600"
                }`}
              >
                {result.verified ? "✓ verified" : "✗ not verified"}
              </span>

              {result.provenance ? (
                <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 text-sm">
                  <dt className="text-text/60">Request ID</dt>
                  <dd className="break-all">
                    {fieldValue(result.provenance.request_id)}
                  </dd>
                  <dt className="text-text/60">Entropy epoch</dt>
                  <dd>{fieldValue(result.provenance.entropy_epoch)}</dd>
                  <dt className="text-text/60">QRNG batch</dt>
                  <dd>{fieldValue(result.provenance.qrng_source_labels)}</dd>
                  <dt className="text-text/60">Timestamp</dt>
                  <dd>{fieldValue(result.provenance.timestamp)}</dd>
                  <dt className="text-text/60">Size</dt>
                  <dd>{fieldValue(result.provenance.size)} bytes</dd>
                </dl>
              ) : (
                <p className="text-sm text-text/70">{result.note}</p>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
