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

  return (
    <div className="panel mx-auto flex w-full max-w-xl flex-col gap-6 p-4 sm:p-6">
      <form onSubmit={onSubmit} className="flex flex-col gap-6">
        <div>
          <p className="mb-2 text-sm text-text/80">Dice sides</p>
          <div className="flex flex-wrap gap-2">
            {PRESET_SIDES.map((preset) => (
              <button
                key={preset}
                type="button"
                onClick={() => setSides(preset)}
                aria-pressed={sides === preset}
                className={`min-h-11 min-w-11 rounded-full border px-4 py-2 text-sm transition-colors ${
                  sides === preset
                    ? "border-primary bg-primary text-bg-deep glow"
                    : "border-border text-text/80 hover:border-accent"
                }`}
              >
                d{preset}
              </button>
            ))}
          </div>
          <label className="mt-3 flex items-center gap-2 text-sm text-text/70">
            Custom sides
            <input
              type="number"
              min={MIN_SIDES}
              max={MAX_SIDES}
              value={sides}
              onChange={(event) => setSides(Number(event.target.value))}
              className="h-11 w-24 rounded-lg border border-border bg-transparent px-3 text-text"
            />
          </label>
        </div>

        <label className="flex items-center gap-2 text-sm text-text/70">
          Number of dice (1–6)
          <input
            type="number"
            min={MIN_COUNT}
            max={MAX_COUNT}
            value={count}
            onChange={(event) => setCount(Number(event.target.value))}
            className="h-11 w-24 rounded-lg border border-border bg-transparent px-3 text-text"
          />
        </label>

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

      {result && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap justify-center gap-3">
            <AnimatePresence>
              {result.rolls.map((value, index) => (
                <motion.div
                  key={`${rollId}-${index}`}
                  initial={{ opacity: 0, scale: 0.6, y: 8 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  transition={{ delay: index * 0.08 }}
                  className="panel glow flex h-16 w-16 items-center justify-center text-2xl font-semibold text-heading"
                >
                  {value}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          <button
            type="button"
            onClick={() => setShowBytes((v) => !v)}
            className="self-center text-sm text-accent underline-offset-4 hover:underline"
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
        </div>
      )}
    </div>
  );
}
