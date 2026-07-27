"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Fabric } from "@/lib/fabric";
import { segmentLinkId } from "@/lib/fabric";

const LOGICAL_W = 1240;
const ROW_HEIGHT = 150;
const TOP_MARGIN = 54;
const N_ROWS = 5; // gateway, core, agg, edge, host
const NODE_R = 13;
const GW_R = 18;
const HOST_R = 6;
const PACKET_R = 3.4;
const BASE_SPEED = 230; // logical px/sec at speed multiplier 1
const TARGET_INFLIGHT = 300; // concurrent packets kept alive

interface Packet {
  route: string[];
  seg: number;
  t: number;
  jitter: number;
}

type Rgb = { r: number; g: number; b: number };

function parseColor(el: Element, name: string): Rgb {
  const raw = getComputedStyle(el).getPropertyValue(name).trim();
  if (raw.startsWith("#")) {
    const hex = raw.slice(1);
    const full = hex.length === 3 ? hex.split("").map((c) => c + c).join("") : hex;
    return { r: parseInt(full.slice(0, 2), 16), g: parseInt(full.slice(2, 4), 16), b: parseInt(full.slice(4, 6), 16) };
  }
  const m = raw.match(/rgba?\(([^)]+)\)/);
  if (m) {
    const [r, g, b] = m[1].split(",").map((x) => parseFloat(x));
    return { r, g, b };
  }
  return { r: 128, g: 128, b: 128 };
}

function lerp(a: Rgb, b: Rgb, u: number): string {
  const c = Math.max(0, Math.min(1, u));
  return `rgb(${Math.round(a.r + (b.r - a.r) * c)},${Math.round(a.g + (b.g - a.g) * c)},${Math.round(a.b + (b.b - a.b) * c)})`;
}

const rgba = (c: Rgb, a: number) => `rgba(${c.r},${c.g},${c.b},${a})`;

/** Live, animated k=4 fat-tree rendered on a canvas: real packets tween
 * host->edge->agg->core and back down along the *actual* ECMP-hashed routes
 * (precomputed in `routes`). Links tint by cumulative traffic (the balancing
 * story) and pulse-widen by live occupancy. Reports cumulative per-link counts
 * up via `onSample`. Canvas (not SVG) so 160 particles animate at 60fps and we
 * never touch refs during React render. */
export default function LiveFatTree({
  fabric,
  routes,
  running,
  speed,
  onSample,
}: {
  fabric: Fabric;
  routes: string[][];
  running: boolean;
  speed: number;
  onSample: (cumulative: number[]) => void;
}) {
  const logicalH = TOP_MARGIN * 2 + ROW_HEIGHT * (N_ROWS - 1);
  const gwY = TOP_MARGIN;
  const coreY = TOP_MARGIN + ROW_HEIGHT;
  const aggY = TOP_MARGIN + ROW_HEIGHT * 2;
  const edgeY = TOP_MARGIN + ROW_HEIGHT * 3;
  const hostY = TOP_MARGIN + ROW_HEIGHT * 4;

  const pos = useMemo(() => {
    const m = new Map<string, { x: number; y: number }>();
    const place = (ids: string[], y: number) =>
      ids.forEach((id, i) => m.set(id, { x: ((i + 0.5) * LOGICAL_W) / ids.length, y }));
    place(fabric.gateways, gwY);
    place(fabric.coreSwitches, coreY);
    place(fabric.aggSwitches, aggY);
    place(fabric.edgeSwitches, edgeY);
    place(fabric.hosts, hostY);
    return m;
  }, [fabric, gwY, coreY, aggY, edgeY, hostY]);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const runningRef = useRef(running);
  const speedRef = useRef(speed);
  const [stats, setStats] = useState({ inflight: 0, delivered: 0 });

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

    let packets: Packet[] = [];
    const cumulative: Record<string, number> = {};
    for (const id of fabric.linkIds) cumulative[id] = 0;
    let delivered = 0;
    let spawnCursor = 0;

    // Palette (resolved from CSS custom properties; refreshed periodically for
    // theme toggles).
    let pal = resolvePalette(canvas);
    let palAge = 0;

    // Responsive sizing.
    let scale = 1;
    const dpr = window.devicePixelRatio || 1;
    const resize = () => {
      const cssW = canvas.clientWidth || LOGICAL_W;
      scale = cssW / LOGICAL_W;
      const cssH = logicalH * scale;
      canvas.style.height = `${cssH}px`;
      canvas.width = Math.round(cssW * dpr);
      canvas.height = Math.round(cssH * dpr);
      ctx.setTransform(dpr * scale, 0, 0, dpr * scale, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const segLen = (route: string[], seg: number): number => {
      const a = pos.get(route[seg]);
      const b = pos.get(route[seg + 1]);
      if (!a || !b) return 1;
      return Math.hypot(b.x - a.x, b.y - a.y);
    };

    let raf = 0;
    let last = 0;
    let sampleAccum = 0;
    let statsAccum = 0;

    const frame = (ts: number) => {
      raf = requestAnimationFrame(frame);
      if (last === 0) last = ts;
      const dt = Math.min(0.05, (ts - last) / 1000);
      last = ts;

      if (++palAge > 60) {
        pal = resolvePalette(canvas);
        palAge = 0;
      }

      if (runningRef.current && routes.length > 0) {
        while (packets.length < TARGET_INFLIGHT) {
          spawnCursor = (spawnCursor + 1) % routes.length;
          packets.push({ route: routes[spawnCursor], seg: 0, t: 0, jitter: 0.8 + ((spawnCursor % 7) / 7) * 0.4 });
        }
        const v = BASE_SPEED * speedRef.current;
        const survivors: Packet[] = [];
        for (const p of packets) {
          p.t += (v * p.jitter * dt) / segLen(p.route, p.seg);
          while (p.t >= 1) {
            const link = segmentLinkId(p.route[p.seg], p.route[p.seg + 1]);
            cumulative[link] = (cumulative[link] ?? 0) + 1;
            p.seg += 1;
            p.t -= 1;
            if (p.seg >= p.route.length - 1) {
              delivered += 1;
              break;
            }
          }
          if (p.seg < p.route.length - 1) survivors.push(p);
        }
        packets = survivors;

        sampleAccum += dt;
        if (sampleAccum >= 0.4) {
          sampleAccum = 0;
          onSample(fabric.linkIds.map((id) => cumulative[id] ?? 0));
        }
        statsAccum += dt;
        if (statsAccum >= 0.25) {
          statsAccum = 0;
          setStats({ inflight: packets.length, delivered });
        }
      }

      // ---- draw ----
      const liveOcc: Record<string, number> = {};
      for (const p of packets) {
        const link = segmentLinkId(p.route[p.seg], p.route[p.seg + 1]);
        liveOcc[link] = (liveOcc[link] ?? 0) + 1;
      }
      const maxOcc = Math.max(1, ...Object.values(liveOcc));
      const maxCum = Math.max(1, ...fabric.linkIds.map((id) => cumulative[id] ?? 0));

      ctx.clearRect(0, 0, LOGICAL_W, logicalH);

      // host uplinks
      ctx.strokeStyle = rgba(pal.border, 0.5);
      ctx.lineWidth = 1;
      for (const hostId of fabric.hosts) {
        const a = pos.get(hostId);
        const b = pos.get(fabric.hostEdge[hostId]);
        if (!a || !b) continue;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }

      // fabric links
      ctx.lineCap = "round";
      for (const id of fabric.linkIds) {
        const [na, nb] = id.split("-");
        const pa = pos.get(na);
        const pb = pos.get(nb);
        if (!pa || !pb) continue;
        const cum = cumulative[id] ?? 0;
        const share = cum / maxCum;
        const live = (liveOcc[id] ?? 0) / maxOcc;
        if (cum > 0) {
          ctx.strokeStyle =
            share < 0.5 ? lerp(pal.success, pal.warning, share * 2) : lerp(pal.warning, pal.danger, (share - 0.5) * 2);
          ctx.globalAlpha = 0.9;
        } else {
          ctx.strokeStyle = rgba(pal.border, 1);
          ctx.globalAlpha = 0.4;
        }
        ctx.lineWidth = 1.5 + live * 5;
        ctx.beginPath();
        ctx.moveTo(pa.x, pa.y);
        ctx.lineTo(pb.x, pb.y);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // packets
      for (const p of packets) {
        const a = pos.get(p.route[p.seg]);
        const b = pos.get(p.route[p.seg + 1]);
        if (!a || !b) continue;
        const x = a.x + (b.x - a.x) * p.t;
        const y = a.y + (b.y - a.y) * p.t;
        const link = segmentLinkId(p.route[p.seg], p.route[p.seg + 1]);
        const hot = (liveOcc[link] ?? 0) / maxOcc > 0.6;
        ctx.fillStyle = hot ? rgba(pal.danger, 0.95) : rgba(pal.accent, 0.95);
        ctx.beginPath();
        ctx.arc(x, y, PACKET_R, 0, Math.PI * 2);
        ctx.fill();
      }

      // nodes
      const drawNodes = (ids: string[], color: Rgb, r: number, alpha = 1) => {
        ctx.fillStyle = rgba(color, alpha);
        for (const id of ids) {
          const p = pos.get(id);
          if (!p) continue;
          ctx.beginPath();
          ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
          ctx.fill();
        }
      };
      // gateways drawn as rounded squares to read as border routers
      ctx.fillStyle = rgba(pal.primary, 1);
      for (const id of fabric.gateways) {
        const p = pos.get(id);
        if (!p) continue;
        ctx.beginPath();
        ctx.roundRect(p.x - GW_R, p.y - GW_R * 0.7, GW_R * 2, GW_R * 1.4, 5);
        ctx.fill();
      }
      drawNodes(fabric.coreSwitches, pal.primary, NODE_R);
      drawNodes(fabric.aggSwitches, pal.info, NODE_R);
      drawNodes(fabric.edgeSwitches, pal.warning, NODE_R);
      drawNodes(fabric.hosts, pal.text, HOST_R, 0.55);

      // tier labels
      ctx.fillStyle = rgba(pal.text, 0.85);
      ctx.font = "600 13px system-ui, sans-serif";
      ctx.fillText(`WAN gateway (${fabric.gateways.length}) — north-south egress`, 10, gwY - 28);
      ctx.fillText(`core (${fabric.coreSwitches.length}) — inter-pod spine`, 10, coreY - 28);
      ctx.fillText(`aggregation (${fabric.aggSwitches.length}) — per-pod uplink`, 10, aggY - 28);
      ctx.fillText(`edge (${fabric.edgeSwitches.length}) — top-of-rack`, 10, edgeY - 28);
      ctx.fillText(`hosts (${fabric.hosts.length})`, 10, hostY - 24);
    };

    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [routes, fabric, pos, logicalH, onSample, gwY, coreY, aggY, edgeY, hostY]);

  return (
    <div className="panel p-4">
      <canvas ref={canvasRef} className="w-full" style={{ display: "block" }} aria-label="Live k=4 fat-tree with packets flowing along ECMP routes" />
      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-(--color-text)">
        <span className="font-(family-name:--font-mono)">in-flight: {stats.inflight}</span>
        <span className="font-(family-name:--font-mono)">delivered: {stats.delivered.toLocaleString()}</span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded-full" style={{ background: "var(--color-accent)" }} /> packet
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded-full" style={{ background: "var(--color-success)" }} /> light link
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded-full" style={{ background: "var(--color-warning)" }} /> busy
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded-full" style={{ background: "var(--color-danger)" }} /> saturated
        </span>
      </div>
    </div>
  );
}

function resolvePalette(el: Element) {
  return {
    primary: parseColor(el, "--color-primary"),
    info: parseColor(el, "--color-info"),
    warning: parseColor(el, "--color-warning"),
    success: parseColor(el, "--color-success"),
    danger: parseColor(el, "--color-danger"),
    accent: parseColor(el, "--color-accent"),
    text: parseColor(el, "--color-text"),
    border: parseColor(el, "--color-border"),
  };
}
