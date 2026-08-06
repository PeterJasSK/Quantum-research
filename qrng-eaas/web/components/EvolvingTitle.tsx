"use client";

import { useEffect, useRef, useState } from "react";
import { getRandomBytes } from "@/lib/api";
import { evolve, seedFromBytes, Frame, TARGET, SPLIT } from "@/lib/heroEvolution";

const STORAGE_KEY = "qeaas_hero_seed";
const TTL_MS = 15 * 60 * 1000; // replay the same run for 15 minutes
const SEED_BYTES = 8;
const FRAME_MS = 75; // per generation
const SETTLE_MS = 400; // linger between the last shuffles and the lock

interface SeedRecord {
  seedHex: string;
  createdAt: number;
}

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function hexToBytes(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i += 1) {
    out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

// A stored seed that is still inside its 15-minute window, or null.
function readFreshSeed(): Uint8Array | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const rec = JSON.parse(raw) as SeedRecord;
    if (!rec.seedHex || Date.now() - rec.createdAt > TTL_MS) return null;
    return hexToBytes(rec.seedHex);
  } catch {
    return null;
  }
}

function storeSeed(bytes: Uint8Array): void {
  try {
    const rec: SeedRecord = { seedHex: bytesToHex(bytes), createdAt: Date.now() };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(rec));
  } catch {
    // storage disabled -- animation still plays, it just won't be remembered
  }
}

const FINAL_FRAME: Frame = {
  chars: TARGET.split(""),
  correct: TARGET.split("").map(() => true),
  gen: 0,
};

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );
}

function Letters({ chars, correct, accent }: { chars: string[]; correct: boolean[]; accent: boolean }) {
  return (
    <>
      {chars.map((ch, i) => (
        <span
          key={i}
          className="inline-block text-center transition-colors duration-100"
          style={{
            width: "0.72em",
            color: correct[i]
              ? undefined
              : accent
                ? "color-mix(in srgb, var(--color-accent, currentColor) 35%, transparent)"
                : "color-mix(in srgb, currentColor 32%, transparent)",
            textShadow: correct[i] && accent ? "0 0 18px color-mix(in srgb, var(--color-accent, currentColor) 55%, transparent)" : undefined,
          }}
        >
          {ch}
        </span>
      ))}
    </>
  );
}

export default function EvolvingTitle() {
  // Render the final words on the server + first client paint (no hydration
  // mismatch, no layout shift), then take over and animate after mount.
  const [frame, setFrame] = useState<Frame>(FINAL_FRAME);
  const framesRef = useRef<Frame[] | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;

    function play(frames: Frame[]) {
      if (cancelled || frames.length === 0) return;
      framesRef.current = frames;
      let i = 0;
      const tick = () => {
        if (cancelled) return;
        setFrame(frames[i]);
        if (i >= frames.length - 1) return;
        const last = i >= frames.length - 2;
        i += 1;
        timerRef.current = setTimeout(tick, last ? SETTLE_MS : FRAME_MS);
      };
      tick();
    }

    async function start() {
      if (prefersReducedMotion()) {
        setFrame(FINAL_FRAME);
        return;
      }
      let bytes = readFreshSeed();
      if (!bytes) {
        try {
          bytes = await getRandomBytes(SEED_BYTES);
          storeSeed(bytes);
        } catch {
          // API unreachable: leave the final words in place, no animation
          return;
        }
      }
      if (cancelled) return;
      play(evolve(seedFromBytes(bytes)));
    }

    start();
    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const line1 = { chars: frame.chars.slice(0, SPLIT), correct: frame.correct.slice(0, SPLIT) };
  const line2 = { chars: frame.chars.slice(SPLIT), correct: frame.correct.slice(SPLIT) };

  return (
    <span aria-label={`${TARGET.slice(0, SPLIT)} ${TARGET.slice(SPLIT)}`}>
      <span aria-hidden>
        <Letters chars={line1.chars} correct={line1.correct} accent={false} />
        <br />
        <span className="relative inline-block text-accent">
          <span className="relative z-10">
            <Letters chars={line2.chars} correct={line2.correct} accent />
          </span>
          <svg
            className="absolute -bottom-1 left-0 z-0 h-3 w-full text-accent opacity-60"
            viewBox="0 0 100 10"
            preserveAspectRatio="none"
            aria-hidden
          >
            <path d="M0 5 Q 50 10 100 5" stroke="currentColor" strokeWidth="8" fill="none" />
          </svg>
        </span>
      </span>
    </span>
  );
}
