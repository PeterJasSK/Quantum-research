"use client";

import { useEffect, useMemo, useRef } from "react";
import type { CliffData, CollapseData, SourceKind } from "@/lib/replay";
import { PORT_BITS, TXID_BITS } from "@/lib/constants";

const SOURCE_COLOR: Record<SourceKind, string> = {
  fixed: "--color-danger",
  prng: "--color-warning",
  csprng: "--color-info",
  qrng: "--color-accent",
};

const LOGICAL_W = 900;
const LOGICAL_H = 360;
const PAD_L = 54;
const PAD_R = 20;
const PAD_T = 24;
const PAD_B = 44;

interface Curve {
  source: SourceKind;
  points: { bits: number; rate: number }[];
}

function readColor(el: Element, name: string): string {
  return getComputedStyle(el).getPropertyValue(name).trim() || "#888";
}

// Average duplicate effective_bits into one point per bit, sorted ascending.
function aggregate(points: { effective_bits: number; poison_rate: number }[]): { bits: number; rate: number }[] {
  const byBits = new Map<number, number[]>();
  for (const p of points) {
    const arr = byBits.get(p.effective_bits) ?? [];
    arr.push(p.poison_rate);
    byBits.set(p.effective_bits, arr);
  }
  return [...byBits.entries()]
    .map(([bits, rates]) => ({ bits, rate: rates.reduce((a, b) => a + b, 0) / rates.length }))
    .sort((a, b) => a.bits - b.bits);
}

function rateAt(points: { bits: number; rate: number }[], bits: number): number | null {
  if (points.length === 0) return null;
  if (bits <= points[0].bits) return points[0].rate;
  if (bits >= points[points.length - 1].bits) return points[points.length - 1].rate;
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    if (bits >= a.bits && bits <= b.bits) {
      const u = (bits - a.bits) / (b.bits - a.bits || 1);
      return a.rate + (b.rate - a.rate) * u;
    }
  }
  return points[points.length - 1].rate;
}

/** Self-drawing entropy cliff (AC-6.2) with the SAD-DNS collapse overlay
 * (AC-6.3). Poison rate (y) vs effective bits (x), one line per source, drawn
 * from cliff.json. A live marker tracks the effectiveBits slider; when SAD-DNS
 * is on, collapse.json's csprng series is overlaid at x = TXID_BITS + (PORT_BITS
 * - k), sweeping left as k rises. Hand-rolled canvas + rAF, no chart library. */
export default function EntropyCliff({
  cliff,
  collapse,
  source,
  effectiveBits,
  sadDnsK,
  sadDnsOn,
}: {
  cliff: CliffData;
  collapse: CollapseData;
  source: SourceKind;
  effectiveBits: number;
  sadDnsK: number;
  sadDnsOn: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const curves = useMemo<Curve[]>(() => {
    return (Object.keys(cliff.sources) as SourceKind[])
      .map((s) => ({ source: s, points: aggregate(cliff.sources[s] ?? []) }))
      .filter((c) => c.points.length > 0);
  }, [cliff]);

  const domain = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    for (const c of curves) {
      for (const p of c.points) {
        if (p.bits < min) min = p.bits;
        if (p.bits > max) max = p.bits;
      }
    }
    if (!isFinite(min)) {
      min = TXID_BITS;
      max = TXID_BITS + PORT_BITS;
    }
    return { min, max };
  }, [curves]);

  const collapseCurve = useMemo(
    () => collapse.series.map((p) => ({ bits: TXID_BITS + Math.max(0, PORT_BITS - p.k), rate: p.poison_rate, k: p.k })),
    [collapse],
  );

  // Live-prop refs so the animation loop reads current values without resubscribing.
  const propsRef = useRef({ source, effectiveBits, sadDnsK, sadDnsOn });
  useEffect(() => {
    propsRef.current = { source, effectiveBits, sadDnsK, sadDnsOn };
  }, [source, effectiveBits, sadDnsK, sadDnsOn]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    let scale = 1;
    const resize = () => {
      const cssW = canvas.clientWidth || LOGICAL_W;
      scale = cssW / LOGICAL_W;
      const cssH = LOGICAL_H * scale;
      canvas.style.height = `${cssH}px`;
      canvas.width = Math.round(cssW * dpr);
      canvas.height = Math.round(cssH * dpr);
      ctx.setTransform(dpr * scale, 0, 0, dpr * scale, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const { min: bMin, max: bMax } = domain;
    const xOf = (bits: number) => PAD_L + ((bits - bMin) / (bMax - bMin || 1)) * (LOGICAL_W - PAD_L - PAD_R);
    const yOf = (rate: number) => PAD_T + (1 - Math.max(0, Math.min(1, rate))) * (LOGICAL_H - PAD_T - PAD_B);

    let raf = 0;
    let start = 0;
    const DRAW_MS = 900;

    const frame = (ts: number) => {
      raf = requestAnimationFrame(frame);
      if (start === 0) start = ts;
      const progress = Math.min(1, (ts - start) / DRAW_MS);
      const { source: src, effectiveBits: eff, sadDnsK: kLeak, sadDnsOn: sadOn } = propsRef.current;

      const border = readColor(canvas, "--color-border");
      const textCol = readColor(canvas, "--color-text");
      const accent = readColor(canvas, "--color-accent");
      const danger = readColor(canvas, "--color-danger");

      ctx.clearRect(0, 0, LOGICAL_W, LOGICAL_H);

      // axes + gridlines
      ctx.strokeStyle = border;
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.6;
      ctx.beginPath();
      ctx.moveTo(PAD_L, PAD_T);
      ctx.lineTo(PAD_L, LOGICAL_H - PAD_B);
      ctx.lineTo(LOGICAL_W - PAD_R, LOGICAL_H - PAD_B);
      ctx.stroke();
      ctx.globalAlpha = 1;

      ctx.fillStyle = textCol;
      ctx.font = "11px system-ui, sans-serif";
      ctx.textAlign = "right";
      for (let r = 0; r <= 1; r += 0.25) {
        const y = yOf(r);
        ctx.globalAlpha = 0.5;
        ctx.strokeStyle = border;
        ctx.beginPath();
        ctx.moveTo(PAD_L, y);
        ctx.lineTo(LOGICAL_W - PAD_R, y);
        ctx.stroke();
        ctx.globalAlpha = 0.8;
        ctx.fillText(r.toFixed(2), PAD_L - 8, y + 3);
      }
      ctx.textAlign = "center";
      for (let b = bMin; b <= bMax; b += 2) {
        ctx.globalAlpha = 0.8;
        ctx.fillText(String(b), xOf(b), LOGICAL_H - PAD_B + 16);
      }
      ctx.globalAlpha = 1;

      // axis labels
      ctx.fillStyle = textCol;
      ctx.globalAlpha = 0.75;
      ctx.font = "600 11px system-ui, sans-serif";
      ctx.fillText("effective entropy bits →", (PAD_L + LOGICAL_W - PAD_R) / 2, LOGICAL_H - 8);
      ctx.save();
      ctx.translate(14, (PAD_T + LOGICAL_H - PAD_B) / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText("poison rate", 0, 0);
      ctx.restore();
      ctx.globalAlpha = 1;

      // one line per source (animated draw left->right)
      for (const c of curves) {
        const col = readColor(canvas, SOURCE_COLOR[c.source]);
        const active = c.source === src;
        ctx.strokeStyle = col;
        ctx.globalAlpha = active ? 1 : 0.35;
        ctx.lineWidth = active ? 2.6 : 1.4;
        ctx.beginPath();
        const cutoff = bMin + (bMax - bMin) * progress;
        let started = false;
        for (const p of c.points) {
          if (p.bits > cutoff) break;
          const x = xOf(p.bits);
          const y = yOf(p.rate);
          if (!started) {
            ctx.moveTo(x, y);
            started = true;
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // SAD-DNS collapse overlay
      if (sadOn && collapseCurve.length > 0) {
        ctx.strokeStyle = danger;
        ctx.globalAlpha = 0.85;
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 5]);
        ctx.beginPath();
        collapseCurve.forEach((p, i) => {
          const x = xOf(p.bits);
          const y = yOf(p.rate);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.setLineDash([]);
        // collapse marker at current k
        const collapseBits = TXID_BITS + Math.max(0, PORT_BITS - kLeak);
        const cx = xOf(collapseBits);
        ctx.fillStyle = danger;
        ctx.beginPath();
        ctx.arc(cx, yOf(rateAt(collapseCurve, collapseBits) ?? 0), 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      // live marker at the effectiveBits slider
      const mx = xOf(Math.max(bMin, Math.min(bMax, eff)));
      ctx.strokeStyle = accent;
      ctx.globalAlpha = 0.9;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(mx, PAD_T);
      ctx.lineTo(mx, LOGICAL_H - PAD_B);
      ctx.stroke();
      ctx.setLineDash([]);

      const activeCurve = curves.find((c) => c.source === src);
      const activeRate = activeCurve ? rateAt(activeCurve.points, eff) : null;
      if (activeRate !== null) {
        const my = yOf(activeRate);
        ctx.fillStyle = accent;
        ctx.beginPath();
        ctx.arc(mx, my, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = textCol;
        ctx.font = "600 12px system-ui, sans-serif";
        ctx.textAlign = mx > LOGICAL_W - 120 ? "right" : "left";
        const label = `${eff} bits · ${(activeRate * 100).toFixed(1)}% poison`;
        ctx.fillText(label, mx + (mx > LOGICAL_W - 120 ? -10 : 10), Math.max(PAD_T + 12, my - 10));
        ctx.textAlign = "left";
      }
      ctx.globalAlpha = 1;
    };

    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [curves, domain, collapseCurve]);

  return (
    <div className="panel p-4">
      <canvas
        ref={canvasRef}
        className="w-full"
        style={{ display: "block" }}
        aria-label="Entropy cliff: poison rate versus effective entropy bits, per source"
      />
      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-(--color-text)">
        {(Object.keys(SOURCE_COLOR) as SourceKind[])
          .filter((s) => curves.some((c) => c.source === s))
          .map((s) => (
            <span key={s} className="inline-flex items-center gap-1">
              <span className="inline-block h-2 w-4 rounded-full" style={{ background: `var(${SOURCE_COLOR[s]})` }} /> {s}
            </span>
          ))}
        {sadDnsOn && (
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-0.5 w-4" style={{ background: "var(--color-danger)" }} /> SAD-DNS collapse (k={sadDnsK})
          </span>
        )}
      </div>
    </div>
  );
}
