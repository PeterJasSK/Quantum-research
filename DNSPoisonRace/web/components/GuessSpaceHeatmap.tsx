"use client";

import { useEffect, useMemo, useRef } from "react";
import type { FloodVector } from "@/lib/raceCore";

const GRID_MAX = 64; // display cap; larger spaces are binned (display-only)
const LOGICAL = 420;
const REVEAL_MS = 6000; // wall-clock to sweep the whole guess sequence at speed 1

function readColor(el: Element, name: string): string {
  return getComputedStyle(el).getPropertyValue(name).trim() || "#888";
}

/** Attacker coverage of the TXID×port guess space (AC-6.4). Cells shade in as
 * each forged packet is sprayed, following the real GuessStream order recorded
 * in the trace's event list; the single correct cell is highlighted and flips
 * red only if a forged guess lands on it. Spaces larger than the grid are binned
 * for display -- the underlying guess order is never changed. */
export default function GuessSpaceHeatmap({
  trace,
  target,
  spaceBits,
  running,
  speed,
}: {
  trace: FloodVector;
  target: number;
  spaceBits: number;
  running: boolean;
  speed: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Ordered forged guesses (effective indices), the real spray order.
  const guesses = useMemo<number[]>(
    () => (trace.events ?? []).filter((e) => e.kind === "forged" && typeof e.guess === "number").map((e) => e.guess as number),
    [trace],
  );

  const layout = useMemo(() => {
    const xbits = Math.ceil(spaceBits / 2);
    const ybits = spaceBits - xbits;
    const cols = Math.min(GRID_MAX, 2 ** xbits);
    const rows = Math.min(GRID_MAX, 2 ** ybits);
    const xspan = 2 ** xbits;
    const yspan = 2 ** ybits;
    const cellOf = (idx: number): [number, number] => {
      const lo = idx % xspan;
      const hi = Math.floor(idx / xspan);
      const col = Math.min(cols - 1, Math.floor((lo / xspan) * cols));
      const row = Math.min(rows - 1, Math.floor((hi / yspan) * rows));
      return [col, row];
    };
    return { cols, rows, cellOf };
  }, [spaceBits]);

  const poisoned = trace.outcome === "poisoned";

  const runningRef = useRef(running);
  const speedRef = useRef(speed);
  useEffect(() => {
    runningRef.current = running;
  }, [running]);
  useEffect(() => {
    speedRef.current = speed;
  }, [speed]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { cols, rows, cellOf } = layout;
    const [tCol, tRow] = cellOf(target);

    const dpr = window.devicePixelRatio || 1;
    let scale = 1;
    const resize = () => {
      const cssW = canvas.clientWidth || LOGICAL;
      scale = cssW / LOGICAL;
      const cssH = LOGICAL * scale;
      canvas.style.height = `${cssH}px`;
      canvas.width = Math.round(cssW * dpr);
      canvas.height = Math.round(cssH * dpr);
      ctx.setTransform(dpr * scale, 0, 0, dpr * scale, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const coverage = new Float32Array(cols * rows);
    let cursor = 0;
    let revealed = 0; // fractional guesses revealed
    let hit = false;
    let raf = 0;
    let last = 0;

    const total = Math.max(1, guesses.length);

    const frame = (ts: number) => {
      raf = requestAnimationFrame(frame);
      if (last === 0) last = ts;
      const dt = Math.min(0.05, (ts - last) / 1000);
      last = ts;

      if (runningRef.current) {
        revealed += (dt * 1000 * speedRef.current * total) / REVEAL_MS;
        if (revealed >= total) {
          // brief hold at full coverage, then loop
          if (revealed >= total * 1.25) {
            coverage.fill(0);
            cursor = 0;
            revealed = 0;
            hit = false;
          }
        }
        const upto = Math.min(total, Math.floor(revealed));
        while (cursor < upto) {
          const g = guesses[cursor];
          const [c, r] = cellOf(g);
          coverage[r * cols + c] = Math.min(1, coverage[r * cols + c] + 0.34);
          if (g === target) hit = true;
          cursor++;
        }
      }

      const border = readColor(canvas, "--color-border");
      const textCol = readColor(canvas, "--color-text");
      const accent = readColor(canvas, "--color-accent");
      const danger = readColor(canvas, "--color-danger");
      const success = readColor(canvas, "--color-success");

      ctx.clearRect(0, 0, LOGICAL, LOGICAL);
      const cw = LOGICAL / cols;
      const ch = LOGICAL / rows;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const v = coverage[r * cols + c];
          if (v > 0) {
            ctx.globalAlpha = 0.15 + v * 0.7;
            ctx.fillStyle = accent;
            ctx.fillRect(c * cw, r * ch, cw + 0.5, ch + 0.5);
          }
        }
      }
      ctx.globalAlpha = 1;

      // grid lines only when cells are big enough to read
      if (cw > 6) {
        ctx.strokeStyle = border;
        ctx.globalAlpha = 0.35;
        ctx.lineWidth = 0.5;
        for (let c = 0; c <= cols; c++) {
          ctx.beginPath();
          ctx.moveTo(c * cw, 0);
          ctx.lineTo(c * cw, LOGICAL);
          ctx.stroke();
        }
        for (let r = 0; r <= rows; r++) {
          ctx.beginPath();
          ctx.moveTo(0, r * ch);
          ctx.lineTo(LOGICAL, r * ch);
          ctx.stroke();
        }
        ctx.globalAlpha = 1;
      }

      // the single correct cell
      const hitLanded = hit && poisoned;
      ctx.fillStyle = hitLanded ? danger : success;
      ctx.globalAlpha = hitLanded ? 1 : 0.9;
      ctx.fillRect(tCol * cw, tRow * ch, Math.max(3, cw), Math.max(3, ch));
      ctx.globalAlpha = 1;
      ctx.strokeStyle = hitLanded ? danger : success;
      ctx.lineWidth = 2;
      const rx = tCol * cw - 3;
      const ry = tRow * ch - 3;
      ctx.strokeRect(rx, ry, Math.max(3, cw) + 6, Math.max(3, ch) + 6);

      // frame border
      ctx.strokeStyle = border;
      ctx.globalAlpha = 0.7;
      ctx.lineWidth = 1;
      ctx.strokeRect(0.5, 0.5, LOGICAL - 1, LOGICAL - 1);
      ctx.globalAlpha = 1;

      // caption
      ctx.fillStyle = textCol;
      ctx.font = "600 11px system-ui, sans-serif";
      ctx.globalAlpha = 0.8;
      const pct = ((Math.min(total, cursor) / total) * 100).toFixed(0);
      ctx.fillText(`${cols}×${rows} bins · ${pct}% sprayed${hitLanded ? " · CACHE POISONED" : ""}`, 8, LOGICAL - 8);
      ctx.globalAlpha = 1;
    };

    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [layout, guesses, target, poisoned]);

  return (
    <div className="panel p-4">
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-sm font-semibold text-(--color-heading)">Guess-space coverage</span>
        <span className="text-xs text-(--color-text) opacity-70 font-(family-name:--font-mono)">
          2^{spaceBits} cells
        </span>
      </div>
      <canvas
        ref={canvasRef}
        className="mx-auto w-full max-w-[420px]"
        style={{ display: "block", aspectRatio: "1 / 1" }}
        aria-label="TXID by port guess-space grid with attacker coverage filling over time"
      />
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-(--color-text)">
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded-sm" style={{ background: "var(--color-accent)" }} /> attacker guesses
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded-sm" style={{ background: "var(--color-success)" }} /> correct cell
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-3 w-3 rounded-sm" style={{ background: "var(--color-danger)" }} /> poisoned
        </span>
      </div>
    </div>
  );
}
