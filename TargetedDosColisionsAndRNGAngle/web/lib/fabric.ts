// TS mirror of testbed/topology/fabric.py (plan-8 D8-parity). Tier A only
// needs to *demonstrate* the mechanism, not reproduce Python bit-for-bit
// (same stance as lib/salt.ts) -- but the fat-tree shape (k=4, 20 switches,
// 16 hosts) and the routing algorithm (hashed upward, deterministic downward)
// match testbed/topology/fabric.py exactly, and `ecmpLink` is P2's vendored
// hash unchanged.
import { ecmpLink, type FiveTuple } from "./ecmpHash";

export const FATTREE_K = 6;

// Web-viz-only super-spine: a small WAN-gateway tier above the core, modelling
// the real datacenter north-south egress path (core -> border/WAN routers).
// Not part of the Python fabric.py mirror -- it carries only the egress flow
// set (see wanFlowSet/egressRouteNodes) and adds a fifth vertical tier.
export const GATEWAY_COUNT = 2;

// Hosts per edge switch is decoupled from k here (web-viz only): a real k=6
// fat-tree has k/2=3 hosts/edge (54 hosts), but 2/edge (36 hosts) keeps the
// bottom row readable while leaving the switch fabric full-size.
export const HOSTS_PER_EDGE = 2;

export interface Fabric {
  k: number;
  half: number; // agg_per_pod = edge_per_pod = hosts_per_edge = core_per_group
  edgeSwitches: string[];
  aggSwitches: string[];
  coreSwitches: string[];
  gateways: string[];
  allSwitches: string[];
  hosts: string[];
  ipToHost: Record<string, string>;
  hostToIp: Record<string, string>;
  hostEdge: Record<string, string>;
  edgePod: Record<string, number>;
  aggPod: Record<string, number>;
  aggLocalIndex: Record<string, number>;
  linkIds: string[];
}

function linkId(a: string, b: string): string {
  return [a, b].sort().join("-");
}

export function buildFattree(k: number = FATTREE_K, hostsPerEdge: number = HOSTS_PER_EDGE): Fabric {
  const half = k / 2;
  const edgeSwitches: string[] = [];
  const aggSwitches: string[] = [];
  const coreSwitches: string[] = Array.from({ length: half * half }, (_, c) => `core${c}`);
  const gateways: string[] = Array.from({ length: GATEWAY_COUNT }, (_, g) => `gw${g}`);
  const allSwitches: string[] = [...coreSwitches];
  const hosts: string[] = [];
  const ipToHost: Record<string, string> = {};
  const hostToIp: Record<string, string> = {};
  const hostEdge: Record<string, string> = {};
  const edgePod: Record<string, number> = {};
  const aggPod: Record<string, number> = {};
  const aggLocalIndex: Record<string, number> = {};
  const linkIds: string[] = [];

  for (let pod = 0; pod < k; pod++) {
    for (let agg = 0; agg < half; agg++) {
      const aggId = `pod${pod}agg${agg}`;
      aggSwitches.push(aggId);
      allSwitches.push(aggId);
      aggPod[aggId] = pod;
      aggLocalIndex[aggId] = agg;
    }
    for (let edge = 0; edge < half; edge++) {
      const edgeId = `pod${pod}edge${edge}`;
      edgeSwitches.push(edgeId);
      allSwitches.push(edgeId);
      edgePod[edgeId] = pod;
      for (let agg = 0; agg < half; agg++) {
        linkIds.push(linkId(edgeId, `pod${pod}agg${agg}`));
      }
      for (let host = 0; host < hostsPerEdge; host++) {
        const hostId = `pod${pod}edge${edge}host${host}`;
        const ip = `10.${pod}.${edge}.${host + 1}`;
        hosts.push(hostId);
        ipToHost[ip] = hostId;
        hostToIp[hostId] = ip;
        hostEdge[hostId] = edgeId;
      }
    }
    for (let agg = 0; agg < half; agg++) {
      const aggId = `pod${pod}agg${agg}`;
      const groupStart = agg * half;
      for (let core = groupStart; core < groupStart + half; core++) {
        linkIds.push(linkId(aggId, `core${core}`));
      }
    }
  }

  // Super-spine uplinks: every core connects to every WAN gateway.
  for (const gw of gateways) {
    for (const core of coreSwitches) linkIds.push(linkId(core, gw));
  }

  return {
    k,
    half,
    edgeSwitches,
    aggSwitches,
    coreSwitches,
    gateways,
    allSwitches,
    hosts,
    ipToHost,
    hostToIp,
    hostEdge,
    edgePod,
    aggPod,
    aggLocalIndex,
    linkIds,
  };
}

/** Per-switch salt for every switch AND WAN gateway. `mintSalt` is supplied by
 * the caller (lib/salt.ts) so this module stays salt-source agnostic:
 *   - weak-prng: `mintSalt` cycles a tiny fixed pool (short-period LCG), so many
 *     switches share the same few salts -> correlated hash choices across tiers
 *     -> polarization spread over the whole fabric as hot/cold imbalance.
 *   - csprng/qrng: every call returns an independent draw -> uncorrelated. */
export function fabricSalts(kind: "weak-prng" | "csprng" | "qrng", fabric: Fabric, mintSalt: () => string): Record<string, string> {
  const salts: Record<string, string> = {};
  for (const switchId of [...fabric.allSwitches, ...fabric.gateways]) salts[switchId] = mintSalt();
  return salts;
}

/** Walk src-edge -> (hashed) agg -> [same pod: straight to dst-edge | different
 * pod: (hashed) core -> (deterministic) dst-agg -> (deterministic) dst-edge].
 * Mirrors testbed/topology/fabric.py `route()` exactly. */
export async function route(fabric: Fabric, salts: Record<string, string>, fiveTuple: FiveTuple): Promise<string[]> {
  const srcEdge = fabric.hostEdge[fabric.ipToHost[fiveTuple.src_ip]];
  const dstEdge = fabric.hostEdge[fabric.ipToHost[fiveTuple.dst_ip]];
  if (srcEdge === dstEdge) return [];

  const srcPod = fabric.edgePod[srcEdge];
  const dstPod = fabric.edgePod[dstEdge];

  const aggChoice = await ecmpLink(fiveTuple, salts[srcEdge], fabric.half);
  const srcAgg = `pod${srcPod}agg${aggChoice}`;

  if (srcPod === dstPod) {
    return [linkId(srcEdge, srcAgg), linkId(srcAgg, dstEdge)];
  }

  const coreChoice = await ecmpLink(fiveTuple, salts[srcAgg], fabric.half);
  const coreId = `core${aggChoice * fabric.half + coreChoice}`;
  const dstAgg = `pod${dstPod}agg${aggChoice}`;

  return [linkId(srcEdge, srcAgg), linkId(srcAgg, coreId), linkId(coreId, dstAgg), linkId(dstAgg, dstEdge)];
}

/** Ordered node path host->...->host for one flow, for the live animation.
 * Same routing as `route()` but returns the switch/host id sequence (including
 * both host endpoints) instead of the sorted link ids, so packets can be
 * tweened point-to-point. Empty when src/dst share an edge (no fabric hop). */
export async function routeNodes(
  fabric: Fabric,
  salts: Record<string, string>,
  fiveTuple: FiveTuple,
): Promise<string[]> {
  const srcHost = fabric.ipToHost[fiveTuple.src_ip];
  const dstHost = fabric.ipToHost[fiveTuple.dst_ip];
  const srcEdge = fabric.hostEdge[srcHost];
  const dstEdge = fabric.hostEdge[dstHost];
  if (srcEdge === dstEdge) return [];

  const srcPod = fabric.edgePod[srcEdge];
  const dstPod = fabric.edgePod[dstEdge];

  const aggChoice = await ecmpLink(fiveTuple, salts[srcEdge], fabric.half);
  const srcAgg = `pod${srcPod}agg${aggChoice}`;

  if (srcPod === dstPod) {
    return [srcHost, srcEdge, srcAgg, dstEdge, dstHost];
  }

  const coreChoice = await ecmpLink(fiveTuple, salts[srcAgg], fabric.half);
  const coreId = `core${aggChoice * fabric.half + coreChoice}`;
  const dstAgg = `pod${dstPod}agg${aggChoice}`;

  return [srcHost, srcEdge, srcAgg, coreId, dstAgg, dstEdge, dstHost];
}

/** Sorted link id joining two adjacent node ids (matches `fabric.linkIds`). */
export function segmentLinkId(a: string, b: string): string {
  return linkId(a, b);
}

/** North-south egress path host -> edge -> agg -> core -> WAN gateway, each hop
 * ECMP-hashed under the same salts. Models internet-bound traffic and animates
 * the super-spine tier. Empty if the fabric has no gateways. */
export async function egressRouteNodes(
  fabric: Fabric,
  salts: Record<string, string>,
  fiveTuple: FiveTuple,
): Promise<string[]> {
  if (fabric.gateways.length === 0) return [];
  const srcHost = fabric.ipToHost[fiveTuple.src_ip];
  const srcEdge = fabric.hostEdge[srcHost];
  const srcPod = fabric.edgePod[srcEdge];

  const aggChoice = await ecmpLink(fiveTuple, salts[srcEdge], fabric.half);
  const srcAgg = `pod${srcPod}agg${aggChoice}`;
  const coreChoice = await ecmpLink(fiveTuple, salts[srcAgg], fabric.half);
  const coreId = `core${aggChoice * fabric.half + coreChoice}`;
  const gwChoice = await ecmpLink(fiveTuple, salts[coreId], fabric.gateways.length);
  const gwId = fabric.gateways[gwChoice];

  return [srcHost, srcEdge, srcAgg, coreId, gwId];
}

/** Deterministic seeded PRNG (mulberry32): same seed -> identical stream, so the
 * traffic plan is byte-identical on every run and every salt source. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface TrafficPlan {
  east: FiveTuple[]; // host<->host (some hosts are popular "servers")
  egress: FiveTuple[]; // host->WAN (north-south)
}

/** A realistic *non-uniform* traffic plan, fully deterministic (seeded): random
 * source hosts, destinations biased toward a small set of popular "server"
 * hosts (so a few edges run hot like a real DC), plus a heavy north-south egress
 * share to keep the WAN gateways busy. Fixed counts -> identical total traffic
 * every run; independent of salt source -> fair weak-vs-csprng comparison. */
export function buildTrafficPlan(
  fabric: Fabric,
  { seed = 0x5eed, east = 600, egress = 420, servers = 5 }: Partial<{ seed: number; east: number; egress: number; servers: number }> = {},
): TrafficPlan {
  const rng = mulberry32(seed);
  const hosts = fabric.hosts;
  const pick = () => hosts[Math.floor(rng() * hosts.length)];

  // A handful of popular destination hosts (the "servers" everyone talks to).
  const serverSet: string[] = [];
  while (serverSet.length < Math.min(servers, hosts.length)) {
    const h = pick();
    if (!serverSet.includes(h)) serverSet.push(h);
  }

  const eastFlows: FiveTuple[] = [];
  for (let i = 0; i < east; i++) {
    const src = pick();
    let dst = "";
    for (let tries = 0; tries < 8; tries++) {
      const candidate = rng() < 0.75 ? serverSet[Math.floor(rng() * serverSet.length)] : pick();
      if (fabric.hostEdge[candidate] !== fabric.hostEdge[src]) {
        dst = candidate;
        break;
      }
    }
    if (!dst) continue; // couldn't find a cross-edge dst; skip (deterministic)
    eastFlows.push({
      src_ip: fabric.hostToIp[src],
      dst_ip: fabric.hostToIp[dst],
      src_port: 40000 + (i % 4096),
      dst_port: 80,
      proto: 6,
    });
  }

  const egressFlows: FiveTuple[] = [];
  for (let i = 0; i < egress; i++) {
    egressFlows.push({
      src_ip: fabric.hostToIp[pick()],
      dst_ip: "203.0.113.9",
      src_port: 40000 + (i % 4096),
      dst_port: 443,
      proto: 6,
    });
  }

  return { east: eastFlows, egress: egressFlows };
}

/** Per-link flow counts over `flows`, ordered to match `fabric.linkIds`. */
export async function fabricLinkLoad(
  fabric: Fabric,
  salts: Record<string, string>,
  flows: FiveTuple[],
): Promise<number[]> {
  const counts: Record<string, number> = {};
  for (const id of fabric.linkIds) counts[id] = 0;
  for (const fiveTuple of flows) {
    const links = await route(fabric, salts, fiveTuple);
    for (const id of links) counts[id] += 1;
  }
  return fabric.linkIds.map((id) => counts[id]);
}

// ---------------------------------------------------------------------------
// Precision collision attacker (unified live stage).
//
// ONE compromised host floods a single victim with crafted flows (fixed dst,
// only src_port sweeps). It aims the whole flood at ONE deep fabric link, deep
// enough that ECMP has many equal-cost paths to spread across — the load-
// balancing tier the attack subverts. A first-hop edge uplink would be a poor
// target (only `half` parallel links, and the source's own uplinks congest
// regardless of salt); the interesting target is a core -> victim-agg link,
// where the fabric offers half^2 equal-cost core->agg paths into the victim's
// pod (k=6 -> 9 such paths).
//
// Every cross-pod flow to the victim traverses core -> victim-agg -> victim-edge
// (see route()). The path is fixed by two hashed choices: aggChoice (at the
// attacker's edge) and coreChoice (at its agg). The attacker crafts src_ports so
// both land on a chosen (a, c) => the flow rides core{a*half+c} -> victim-agg{a}
// = targetLink. It solves this against the salt it *believes* the switches use
// (`believedSalts`); packets route under the real salts (`realSalts`):
//   predictable salt (believed==real) => every crafted flow lands on (a,c) =>
//     the whole flood funnels onto the one target link and down to the victim
//     (red cone); the rest of the fabric is untouched. Targeted DoS.
//   unpredictable salt (believed!=real) => the same crafted ports hash to random
//     (aggChoice,coreChoice) => flows spray across all half^2 core->agg links =>
//     each carries ~1/half^2 => the flood dissolves into the background. Defeated.
// CSPRNG already breaks the precomputation; QRNG only adds attestable
// provenance, never extra mitigation (Experiment 4 null result). This is a
// SINGLE-attacker, single-target-link model by design — no botnet — matching
// the study's novelty framing (distinct from Crossfire/Coremelt).
// ---------------------------------------------------------------------------

export interface AttackForce {
  attacker: string; // the single compromised source host
  victim: string; // single target host
}

/** Deterministic attacker/victim pair on opposite ends of the fabric, in
 * different pods, so the crafted flood climbs edge -> agg -> core and back down
 * to the victim — maximally visible and forced through the core tier. */
export function attackForce(fabric: Fabric): AttackForce {
  return { attacker: fabric.hosts[fabric.hosts.length - 1], victim: fabric.hosts[0] };
}

/** The crafted 5-tuple: fixed attacker src, fixed victim dst, only src_port sweeps. */
function attackTuple(fabric: Fabric, attacker: string, victim: string, srcPort: number): FiveTuple {
  return {
    src_ip: fabric.hostToIp[attacker],
    dst_ip: fabric.hostToIp[victim],
    src_port: srcPort,
    dst_port: 80,
    proto: 6,
  };
}

export interface AttackPlan {
  routes: string[][]; // crafted flood paths, routed under the REAL salts
  targetLink: string; // the single deep core->victim-agg link aimed at
  targetAgg: string;
  collisionSetSize: number; // crafted flows in the flood
  scanned: number; // src_ports searched
  // Fraction of the flood that actually traverses targetLink under the REAL
  // salts — the concentration the attacker achieved. ~1.0 when the salt was
  // predictable (attack locks on), ~1/half^2 when it wasn't (scattered). This
  // is exact and background-independent, so it drives the locked/scattered
  // verdict without being fooled by ordinary traffic polarization.
  onTargetFraction: number;
}

/** Build the attacker's crafted flood aimed at one deep core->victim-agg link,
 * chosen by (targetAgg, targetCore). Scans src_port space keeping ports whose
 * (aggChoice, coreChoice) match the target *under the salt it believes*, then
 * routes each kept flow under the real salts so the animation shows where the
 * packets truly go. Predictable salt => believed==real => all converge;
 * unpredictable => they spray across the core tier. */
export async function craftAttackFlows(
  fabric: Fabric,
  realSalts: Record<string, string>,
  believedSalts: Record<string, string>,
  { attacker, victim }: AttackForce,
  {
    count = 200,
    window = 16000,
    targetAgg = 0,
    targetCore = 0,
  }: Partial<{ count: number; window: number; targetAgg: number; targetCore: number }> = {},
): Promise<AttackPlan> {
  const victimPod = fabric.edgePod[fabric.hostEdge[victim]];
  const targetAggId = `pod${victimPod}agg${targetAgg}`;
  const targetCoreId = `core${targetAgg * fabric.half + targetCore}`;
  const targetLink = linkId(targetCoreId, targetAggId);

  const attackerEdge = fabric.hostEdge[attacker];
  const attackerPod = fabric.edgePod[attackerEdge];
  const attackerAgg = `pod${attackerPod}agg${targetAgg}`;

  const routes: string[][] = [];
  let scanned = 0;
  for (let port = 40000; routes.length < count && port < 40000 + window; port++, scanned++) {
    const tuple = attackTuple(fabric, attacker, victim, port);
    const aggChoice = await ecmpLink(tuple, believedSalts[attackerEdge], fabric.half);
    if (aggChoice !== targetAgg) continue;
    const coreChoice = await ecmpLink(tuple, believedSalts[attackerAgg], fabric.half);
    if (coreChoice !== targetCore) continue;
    const nodes = await routeNodes(fabric, realSalts, tuple);
    if (nodes.length > 0) routes.push(nodes);
  }

  let onTarget = 0;
  for (const route of routes) {
    for (let i = 0; i < route.length - 1; i++) {
      if (linkId(route[i], route[i + 1]) === targetLink) {
        onTarget += 1;
        break;
      }
    }
  }

  return {
    routes,
    targetLink,
    targetAgg: targetAggId,
    collisionSetSize: routes.length,
    scanned,
    onTargetFraction: routes.length > 0 ? onTarget / routes.length : 0,
  };
}

/** A uniform background flow set: every distinct host pair, one flow each. */
export function uniformFlowSet(fabric: Fabric): FiveTuple[] {
  const flows: FiveTuple[] = [];
  for (const src of fabric.hosts) {
    for (const dst of fabric.hosts) {
      if (src === dst) continue;
      flows.push({
        src_ip: fabric.hostToIp[src],
        dst_ip: fabric.hostToIp[dst],
        src_port: 40000,
        dst_port: 80,
        proto: 6,
      });
    }
  }
  return flows;
}
