"use client";

import { useEffect, useRef } from "react";
import type { FloodVector } from "@/lib/raceCore";

const LOGICAL_W = 900;
const LOGICAL_H = 340;
const MAX_MARKS = 280; // forged packets drawn at once are subsampled (display-only)
const ANIM_SECONDS = 5; // wall-clock length of one replay at speed 1

interface RaceOutcome {
  outcome: string;
  t_outcome: number;
  forged_packets: number;
}

function readColor(el: Element, name: string): string {
  return getComputedStyle(el).getPropertyValue(name).trim() || "#888";
}

/** The poison race (AC-6.1). Hand-rolled canvas + rAF (mirrors the twin's
 * LiveFatTree structure: logical coords, DPR setTransform, refs for live
 * running/speed, palette from CSS vars). The attacker sprays forged-answer
 * packets at the resolver on the trace's send_schedule while one authoritative
 * reply races back over rtt; on completion the cache lamp lights red (POISONED)
 * or green (RESOLVED-LEGIT). Replayable per source (re-keyed on the trace). */
export default function PoisonRaceCanvas({
  trace,
  running,
  speed,
  onOutcome,
}: {
  trace: FloodVector;
  running: boolean;
  speed: number;
  onOutcome: (o: RaceOutcome) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const runningRef = useRef(running);
  const speedRef = useRef(speed);
  const onOutcomeRef = useRef(onOutcome);

  useEffect(() => {
    runningRef.current = running;
  }, [running]);
  useEffect(() => {
    speedRef.current = speed;
  }, [speed]);
  useEffect(() => {
    onOutcomeRef.current = onOutcome;
  }, [onOutcome]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const duration = Math.max(1e-6, trace.t_outcome);
    const poisoned = trace.outcome === "poisoned";
    const schedule = trace.send_schedule;
    // Subsample the send schedule for rendering; the real count is shown live.
    const step = Math.max(1, Math.ceil(schedule.length / MAX_MARKS));
    const marks: number[] = [];
    for (let i = 0; i < schedule.length; i += step) marks.push(schedule[i]);
    const flight = Math.max(0.008, duration * 0.12);
    // Authoritative reply arrives at duration when it wins; a touch later (so it
    // visibly loses) when the cache is poisoned.
    const tAuthVisual = poisoned ? duration * 1.18 : duration;

    const attacker = { x: 96, y: 74 };
    const server = { x: LOGICAL_W - 96, y: 74 };
    const resolver = { x: LOGICAL_W / 2, y: 250 };

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

    let simT = 0;
    let completed = false;
    let raf = 0;
    let last = 0;

    const drawNode = (
      p: { x: number; y: number },
      color: string,
      label: string,
      sub: string,
    ) => {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(p.x - 58, p.y - 26, 116, 52, 10);
      ctx.fill();
      ctx.fillStyle = "#ffffff";
      ctx.font = "700 13px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(label, p.x, p.y - 2);
      ctx.font = "500 10px system-ui, sans-serif";
      ctx.globalAlpha = 0.9;
      ctx.fillText(sub, p.x, p.y + 13);
      ctx.globalAlpha = 1;
      ctx.textAlign = "left";
    };

    const frame = (ts: number) => {
      raf = requestAnimationFrame(frame);
      if (last === 0) last = ts;
      const dt = Math.min(0.05, (ts - last) / 1000);
      last = ts;

      const simRate = (duration / ANIM_SECONDS) * speedRef.current;
      if (runningRef.current) {
        simT += dt * simRate;
        if (!completed && simT >= duration) {
          completed = true;
          onOutcomeRef.current({
            outcome: trace.outcome,
            t_outcome: trace.t_outcome,
            forged_packets: trace.forged_packets,
          });
        }
        // hold the terminal state briefly, then replay
        if (simT >= duration * 1.4) {
          simT = 0;
          completed = false;
        }
      }

      const border = readColor(canvas, "--color-border");
      const textCol = readColor(canvas, "--color-text");
      const danger = readColor(canvas, "--color-danger");
      const success = readColor(canvas, "--color-success");
      const primary = readColor(canvas, "--color-primary");

      ctx.clearRect(0, 0, LOGICAL_W, LOGICAL_H);

      // tracks
      ctx.strokeStyle = border;
      ctx.globalAlpha = 0.7;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(attacker.x, attacker.y + 24);
      ctx.lineTo(resolver.x, resolver.y - 26);
      ctx.moveTo(server.x, server.y + 24);
      ctx.lineTo(resolver.x, resolver.y - 26);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;

      // forged flood: attacker -> resolver
      let sent = 0;
      for (const st of schedule) {
        if (st <= simT) sent++;
        else break;
      }
      ctx.fillStyle = danger;
      for (const st of marks) {
        const u = (simT - st) / flight;
        if (u < 0 || u > 1) continue;
        const x = attacker.x + (resolver.x - attacker.x) * u;
        const y = attacker.y + 24 + (resolver.y - 26 - (attacker.y + 24)) * u;
        ctx.globalAlpha = 0.85;
        ctx.beginPath();
        ctx.arc(x, y, 3.6, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      // authoritative reply: server -> resolver
      const av = Math.min(1, simT / tAuthVisual);
      if (av > 0 && av < 1) {
        const x = server.x + (resolver.x - server.x) * av;
        const y = server.y + 24 + (resolver.y - 26 - (server.y + 24)) * av;
        ctx.fillStyle = success;
        ctx.beginPath();
        ctx.arc(x, y, 6.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = success;
        ctx.globalAlpha = 0.4;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, 11, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }

      // nodes
      drawNode(attacker, danger, "ATTACKER", `${trace.forged_packets.toLocaleString()} forged`);
      drawNode(server, success, "AUTHORITATIVE", `reply @ ${trace.rtt}s rtt`);
      drawNode(resolver, primary, "RESOLVER", "cache");

      // cache lamp
      const done = completed || simT >= duration;
      const lampColor = !done ? border : poisoned ? danger : success;
      const lampX = resolver.x + 70;
      const lampY = resolver.y;
      ctx.fillStyle = lampColor;
      ctx.globalAlpha = done ? 1 : 0.5;
      ctx.beginPath();
      ctx.arc(lampX, lampY, 9, 0, Math.PI * 2);
      ctx.fill();
      if (done) {
        ctx.globalAlpha = 0.35;
        ctx.beginPath();
        ctx.arc(lampX, lampY, 16, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      // outcome banner
      if (done) {
        ctx.fillStyle = poisoned ? danger : success;
        ctx.font = "800 20px system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(poisoned ? "CACHE POISONED" : "RESOLVED — LEGIT WINS", resolver.x, LOGICAL_H - 34);
        ctx.textAlign = "left";
      }

      // live progress / counters
      ctx.fillStyle = textCol;
      ctx.globalAlpha = 0.8;
      ctx.font = "600 11px system-ui, sans-serif";
      ctx.fillText(`forged in flight: ${sent.toLocaleString()} / ${trace.forged_packets.toLocaleString()}`, 12, 22);
      ctx.textAlign = "right";
      ctx.fillText(`sim t = ${Math.min(simT, duration).toFixed(3)}s`, LOGICAL_W - 12, 22);
      ctx.textAlign = "left";
      ctx.globalAlpha = 1;
    };

    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [trace]);

  return (
    <div className="panel p-4">
      <canvas
        ref={canvasRef}
        className="w-full"
        style={{ display: "block" }}
        aria-label="Poison race: attacker forged-answer flood versus the authoritative reply into the resolver cache"
      />
      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-(--color-text)">
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded-full" style={{ background: "var(--color-danger)" }} /> forged answer
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded-full" style={{ background: "var(--color-success)" }} /> authoritative reply
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="lamp lamp-red" /> poisoned
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="lamp lamp-green" /> resolved-legit
        </span>
      </div>
    </div>
  );
}
