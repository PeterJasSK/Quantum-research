"use client";

import { useEffect, useState } from "react";
import { getHealth, type Health } from "@/lib/api";

const POLL_MS = 20_000;

type Status = "loading" | "healthy" | "degraded" | "error";

function statusFor(health: Health | null, failed: boolean): Status {
  if (failed) return "error";
  if (!health) return "loading";
  return health.quantum_entropy_level;
}

const STYLES: Record<Status, string> = {
  loading: "bg-white/10 text-text",
  healthy: "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-400/40",
  degraded: "bg-amber-500/20 text-amber-300 ring-1 ring-amber-400/40",
  error: "bg-white/5 text-text/60",
};

const LABELS: Record<Status, string> = {
  loading: "Quantum entropy: checking…",
  healthy: "Quantum entropy: healthy",
  degraded: "Quantum entropy: degraded",
  error: "Quantum entropy: status unavailable",
};

export default function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const result = await getHealth();
        if (!cancelled) {
          setHealth(result);
          setFailed(false);
        }
      } catch {
        if (!cancelled) setFailed(true);
      }
    }

    poll();
    const interval = setInterval(poll, POLL_MS);
    window.addEventListener("focus", poll);

    return () => {
      cancelled = true;
      clearInterval(interval);
      window.removeEventListener("focus", poll);
    };
  }, []);

  const status = statusFor(health, failed);

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${STYLES[status]}`}
    >
      {LABELS[status]}
    </span>
  );
}
