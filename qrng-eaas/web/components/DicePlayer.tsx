"use client";

import { useState, type FormEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { rollDice, ApiError, type DiceRoll } from "@/lib/api";

const PRESET_SIDES = [4, 6, 8, 10, 12, 20, 50, 100];
const MIN_SIDES = 2;
const MAX_SIDES = 100;
const MIN_COUNT = 1;
const MAX_COUNT = 6;

const ERROR_MESSAGES: Record<string, string> = {
  bad_request: "Sides must be 2–100 and count must be 1–6.",
  rate_limited: "Too many rolls — slow down and try again in a moment.",
  dice_sampling_failed: "The roll couldn't be sampled — try again.",
};

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    return ERROR_MESSAGES[error.slug] ?? `Something went wrong (${error.slug}).`;
  }
  return "Something went wrong. Check your connection and try again.";
}

export default function DicePlayer() {
  const [sides, setSides] = useState(6);
  const [count, setCount] = useState(1);
  const [result, setResult] = useState<DiceRoll | null>(null);
  const [rollId, setRollId] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showBytes, setShowBytes] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;

    setLoading(true);
    setError(null);
    try {
      const roll = await rollDice(sides, count);
      setResult(roll);
      setRollId((id) => id + 1);
      setShowBytes(false);
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setLoading(false);
    }
  }

  const sum = result?.rolls.reduce((total, value) => total + value, 0) ?? 0;
  const avg = result ? sum / result.rolls.length : 0;

  return (
    <div className="mx-auto grid w-full max-w-4xl gap-6 lg:grid-cols-[360px_1fr] lg:items-start">
      <div className="panel flex flex-col gap-6 p-5 sm:p-6">
        <form onSubmit={onSubmit} className="flex flex-col gap-6">
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-widest text-text/60">
              Dice sides
            </p>
            <div className="flex flex-wrap gap-2">
              {PRESET_SIDES.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setSides(preset)}
                  aria-pressed={sides === preset}
                  className={`min-h-11 min-w-11 rounded-full border px-4 py-2 text-sm font-semibold transition-colors ${
                    sides === preset
                      ? "border-primary bg-primary text-bg-deep glow"
                      : "border-border text-text/80 hover:border-accent"
                  }`}
                >
                  d{preset}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label
              htmlFor="custom-sides"
              className="mb-2 block text-xs font-bold uppercase tracking-widest text-text/60"
            >
              Custom sides
            </label>
            <div className="flex items-center justify-between rounded-2xl border border-border bg-bg-deep/5 px-4 py-3">
              <input
                id="custom-sides"
                type="number"
                min={MIN_SIDES}
                max={MAX_SIDES}
                value={sides}
                onChange={(event) => setSides(Number(event.target.value))}
                className="w-full bg-transparent text-2xl font-black text-heading outline-none"
              />
              <span className="text-sm font-bold text-text/40">sides</span>
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-widest text-text/60">
              Number of dice
            </p>
            <div className="flex items-center justify-between rounded-2xl border border-border px-3 py-2">
              <button
                type="button"
                onClick={() => setCount((c) => Math.max(MIN_COUNT, c - 1))}
                disabled={count <= MIN_COUNT}
                aria-label="Fewer dice"
                className="flex h-9 w-9 items-center justify-center rounded-full border border-border text-lg font-bold text-text/80 transition-colors hover:border-accent disabled:opacity-40"
              >
                −
              </button>
              <span className="text-xl font-black text-heading">{count}</span>
              <button
                type="button"
                onClick={() => setCount((c) => Math.min(MAX_COUNT, c + 1))}
                disabled={count >= MAX_COUNT}
                aria-label="More dice"
                className="flex h-9 w-9 items-center justify-center rounded-full border border-border text-lg font-bold text-text/80 transition-colors hover:border-accent disabled:opacity-40"
              >
                +
              </button>
            </div>
            <p className="mt-2 text-xs text-text/50">1–6 dice per roll</p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="pill h-14 w-full text-lg font-semibold"
          >
            {loading ? "Rolling…" : "Roll"}
          </button>
        </form>

        {error && (
          <p role="alert" className="text-sm text-warning">
            {error}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-6">
        {result ? (
          <>
            <div className="panel border-2 border-accent/50 p-6 sm:p-8">
              <p className="text-xs font-bold uppercase tracking-widest text-accent">
                Total
              </p>
              <p className="glow mt-1 text-5xl font-black text-heading sm:text-6xl">
                {sum}
              </p>
              <p className="mt-2 text-sm text-text/60">
                {result.count}× d{result.sides}
                {result.rolls.length > 1 && <> · average {avg.toFixed(2)}</>}
              </p>
            </div>

            <div className="panel p-5 sm:p-6">
              <p className="mb-4 text-xs font-bold uppercase tracking-widest text-text/60">
                Individual rolls
              </p>
              <div className="flex flex-wrap gap-3">
                <AnimatePresence>
                  {result.rolls.map((value, index) => (
                    <motion.div
                      key={`${rollId}-${index}`}
                      initial={{ opacity: 0, scale: 0.6, y: 8 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      transition={{ delay: index * 0.08 }}
                      className="flex h-16 w-16 items-center justify-center rounded-2xl border border-border bg-bg-deep/5 text-2xl font-semibold text-heading"
                    >
                      {value}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowBytes((v) => !v)}
              className="self-start text-sm text-accent underline-offset-4 hover:underline"
            >
              {showBytes ? "Hide" : "Show"} the quantum bytes behind this roll
            </button>

            {showBytes && (
              <div className="panel break-all p-4 text-xs text-text/80">
                <p className="mb-2 text-text/60">
                  the quantum-seeded DRBG bytes drawn for this roll (
                  {result.bytes_count} bytes; some may have been rejected to
                  avoid bias)
                </p>
                {result.bytes_used}
              </div>
            )}
          </>
        ) : (
          <div className="panel flex min-h-[220px] items-center justify-center p-8 text-center text-sm text-text/50">
            Configure your roll on the left and press Roll to draw
            quantum-seeded randomness.
          </div>
        )}
      </div>
    </div>
  );
}
