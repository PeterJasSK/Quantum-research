"use client";

import { useEffect, useState } from "react";
import { getHealth, type Health } from "@/lib/api";

type Status = "loading" | "healthy" | "degraded" | "error";

function statusFor(health: Health | null, failed: boolean): Status {
  if (failed) return "error";
  if (!health) return "loading";
  return health.quantum_entropy_level;
}

const STYLES: Record<Status, string> = {
  loading: "bg-border/20 text-text",
  healthy: "bg-success/20 text-success ring-1 ring-success/40",
  degraded: "bg-warning/20 text-warning ring-1 ring-warning/40",
  error: "bg-danger/10 text-text/60",
};

const LABELS: Record<Status, string> = {
  loading: "Q.E. : checking…",
  healthy: "Q.E. : healthy",
  degraded: "Q.E. : degraded",
  error: "Q.E. : status unavailable",
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
    window.addEventListener("focus", poll);

    return () => {
      cancelled = true;
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
