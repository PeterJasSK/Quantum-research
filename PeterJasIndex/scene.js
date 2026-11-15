// peterjas.sk — background scene: a wireframe quantum computer (dilution-fridge
// "chandelier" with signal pulses running down to a qubit chip, ringed by
// orbits) floating in a slowly drifting qubit lattice.
// Points + line segments only (four draw calls). Colours come from the
// --scene-* CSS custom properties, so the scene follows the page theme.
// Classic script, lazy-loaded by main.js; the page never depends on it.
const THREE_URL = "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.min.js";

const MAX_NODES = 320;
const MAX_LINKS = 1400;
const FOV = 50;
const CAMERA_Z = 14;
const DEPTH = 3;            // half-thickness of the lattice slab (world units)
const DRIFT = 0.35;         // how far a node wanders from its lattice site
const OVERSCAN = 1.35;      // lattice extends past the viewport edges
const SPRITE_PX = 22;       // on-screen size of a node sprite (core + halo)
const SCROLL_SHIFT = 0.0015; // world units of lattice travel per scrolled px
const FLASH_SECONDS = 1.8;  // one "measurement": flash, collapse, re-emerge
const TAU = Math.PI * 2;

// sculpture (local units, y up)
const STAGES = [[4.2, 2.6], [2.9, 2.3], [1.7, 2.0], [0.7, 1.7], [-0.2, 1.4], [-1.0, 1.1]]; // plate [y, radius]
const PLATE_THICKNESS = 0.09;
const CABLES = 24;          // coax lines running top plate -> chip
const CABLE_STEPS = 12;     // samples per stage
const CHIP_Y = -2.5;
const CHIP_GRID = 5;        // qubits per side
const CHIP_PITCH = 0.32;
const ORBITS = [[3.5, 0.5, 0.25], [4.0, -0.35, 0.9], [4.6, 1.1, -0.4]]; // [radius, tiltZ, tiltX]
const QUBITS = CHIP_GRID * CHIP_GRID;
const MAX_PULSES = 96;
const BASE_PULSES = 40;
const ELECTRONS = ORBITS.length * 2;

// swarm (left side): points that fly between formations, drone-show style
const SWARM = 96;           // few, clearly separate dots — drones, not a drawing
const SWARM_HOLD = 6;       // seconds a formation is held
const SWARM_MORPH = 6;      // seconds to fly to the next one

const POINT_VERT = /* glsl */ `
  attribute float aSize;
  attribute float aAlpha;
  attribute float aFlash;
  uniform float uScale;
  varying float vAlpha;
  varying float vFlash;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = aSize * uScale / -mv.z;
    vAlpha = aAlpha;
    vFlash = aFlash;
  }`;

const POINT_FRAG = /* glsl */ `
  uniform vec3 uColor;
  uniform vec3 uFlash;
  uniform float uHalo;
  uniform float uOpacity;
  varying float vAlpha;
  varying float vFlash;
  void main() {
    float d = length(gl_PointCoord - 0.5) * 2.0;            // 0 centre, 1 edge
    float core = 1.0 - smoothstep(0.16, 0.26, d);
    float halo = pow(max(0.0, 1.0 - d), 2.2) * (uHalo + vFlash * 0.7);
    float a = clamp(core + halo, 0.0, 1.0) * vAlpha * uOpacity;
    if (a < 0.004) discard;
    gl_FragColor = vec4(mix(uColor, uFlash, vFlash), a);
  }`;

const LINE_VERT = /* glsl */ `
  attribute float aAlpha;
  attribute float aFlash;
  varying float vAlpha;
  varying float vFlash;
  void main() {
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    vAlpha = aAlpha;
    vFlash = aFlash;
  }`;

const LINE_FRAG = /* glsl */ `
  uniform vec3 uColor;
  uniform vec3 uFlash;
  uniform float uOpacity;
  varying float vAlpha;
  varying float vFlash;
  void main() {
    gl_FragColor = vec4(mix(uColor, uFlash, vFlash), vAlpha * uOpacity);
  }`;

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const smooth = (t) => t * t * (3 - 2 * t);

// "#rgb" / "#rrggbb" -> [r, g, b] in 0..1 (kept in sRGB; shaders output as-is)
function parseHex(hex) {
  let h = hex.trim().replace("#", "");
  if (h.length === 3) h = [...h].map((c) => c + c).join("");
  const n = parseInt(h, 16);
  return Number.isNaN(n) ? [0.5, 0.8, 0.9] : [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255];
}

/** Starts the scene on `canvas`. Returns false if WebGL could not start. */
function initScene(THREE, canvas) {
  const root = document.documentElement;
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: "low-power" });
  } catch {
    return false;
  }
  renderer.setClearColor(0x000000, 0);
  renderer.sortObjects = false;                          // nothing depth-tested, draw in scene order

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 60);

  // ---- per-node state (flat typed arrays, no per-frame allocation) ----
  const home = new Float32Array(MAX_NODES * 3);    // lattice site, normalised -1..1
  const phase = new Float32Array(MAX_NODES * 3);
  const speed = new Float32Array(MAX_NODES * 3);
  const pos = new Float32Array(MAX_NODES * 3);
  const size = new Float32Array(MAX_NODES);
  const alpha = new Float32Array(MAX_NODES);
  const flash = new Float32Array(MAX_NODES);
  const presence = new Float32Array(MAX_NODES);    // 0..1 fade for nodes joining/leaving
  const flashClock = new Float32Array(MAX_NODES).fill(-1); // -1 = idle

  const pointGeo = new THREE.BufferGeometry();
  const posAttr = new THREE.BufferAttribute(pos, 3).setUsage(THREE.DynamicDrawUsage);
  const alphaAttr = new THREE.BufferAttribute(alpha, 1).setUsage(THREE.DynamicDrawUsage);
  const flashAttr = new THREE.BufferAttribute(flash, 1).setUsage(THREE.DynamicDrawUsage);
  pointGeo.setAttribute("position", posAttr);
  pointGeo.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
  pointGeo.setAttribute("aAlpha", alphaAttr);
  pointGeo.setAttribute("aFlash", flashAttr);

  const uniforms = {
    uColor: { value: new THREE.Vector3() },
    uFlash: { value: new THREE.Vector3() },
    uLink: { value: new THREE.Vector3() },
    uHalo: { value: 0 },
    uScale: { value: 1 },
    uNodeOpacity: { value: 0 },
    uLinkOpacity: { value: 0 },
  };
  const materialBase = { transparent: true, depthTest: false, depthWrite: false };
  const points = new THREE.Points(pointGeo, new THREE.ShaderMaterial({
    ...materialBase,
    vertexShader: POINT_VERT,
    fragmentShader: POINT_FRAG,
    uniforms: {
      uColor: uniforms.uColor, uFlash: uniforms.uFlash, uHalo: uniforms.uHalo,
      uScale: uniforms.uScale, uOpacity: uniforms.uNodeOpacity,
    },
  }));

  const linkPos = new Float32Array(MAX_LINKS * 6);
  const linkAlpha = new Float32Array(MAX_LINKS * 2);
  const linkFlash = new Float32Array(MAX_LINKS * 2);
  const linkGeo = new THREE.BufferGeometry();
  const linkPosAttr = new THREE.BufferAttribute(linkPos, 3).setUsage(THREE.DynamicDrawUsage);
  const linkAlphaAttr = new THREE.BufferAttribute(linkAlpha, 1).setUsage(THREE.DynamicDrawUsage);
  const linkFlashAttr = new THREE.BufferAttribute(linkFlash, 1).setUsage(THREE.DynamicDrawUsage);
  linkGeo.setAttribute("position", linkPosAttr);
  linkGeo.setAttribute("aAlpha", linkAlphaAttr);
  linkGeo.setAttribute("aFlash", linkFlashAttr);
  const links = new THREE.LineSegments(linkGeo, new THREE.ShaderMaterial({
    ...materialBase,
    vertexShader: LINE_VERT,
    fragmentShader: LINE_FRAG,
    uniforms: { uColor: uniforms.uLink, uFlash: uniforms.uFlash, uOpacity: uniforms.uLinkOpacity },
  }));

  points.frustumCulled = links.frustumCulled = false;
  scene.add(links, points);

  // ---- sculpture: static wireframe + a small set of moving points ----
  const sculpture = new THREE.Group();
  const wire = [], wireAlpha = [];
  const seg = (ax, ay, az, bx, by, bz, a) => { wire.push(ax, ay, az, bx, by, bz); wireAlpha.push(a, a); };
  const ring = (y, r, a, n = 72) => {
    for (let k = 0; k < n; k++) {
      const a0 = (k / n) * TAU, a1 = ((k + 1) / n) * TAU;
      seg(Math.cos(a0) * r, y, Math.sin(a0) * r, Math.cos(a1) * r, y, Math.sin(a1) * r, a);
    }
  };

  // plates: rim (top + bottom edge), inner rings, spokes, support rods to the next stage
  STAGES.forEach(([y, r], i) => {
    ring(y, r, 0.9);
    ring(y - PLATE_THICKNESS, r, 0.5);
    ring(y, r * 0.55, 0.32);
    ring(y, r * 0.2, 0.3, 24);
    for (let k = 0; k < 12; k++) {
      const c = Math.cos((k / 12) * TAU), s = Math.sin((k / 12) * TAU);
      seg(c * r * 0.2, y, s * r * 0.2, c * r, y, s * r, 0.2);
      seg(c * r, y, s * r, c * r, y - PLATE_THICKNESS, s * r, 0.5);
    }
    const next = STAGES[i + 1];
    if (next) {
      for (let k = 0; k < 6; k++) {
        const a = ((k + 0.5) / 6) * TAU, rr = next[1] * 0.92;
        seg(Math.cos(a) * rr, y - PLATE_THICKNESS, Math.sin(a) * rr, Math.cos(a) * rr, next[0], Math.sin(a) * rr, 0.45);
      }
    }
  });
  ring(5.0, 1.0, 0.45, 48);                              // top mount
  for (let k = 0; k < 6; k++) {
    const a = (k / 6) * TAU;
    seg(Math.cos(a), 5.0, Math.sin(a), Math.cos(a), STAGES[0][0], Math.sin(a), 0.4);
  }

  // cables: one polyline each, kinked between stages like real coax loops;
  // kept as arrays so pulses can travel along them
  const cablePoints = (STAGES.length * CABLE_STEPS) + 1;
  const cables = [];
  for (let c = 0; c < CABLES; c++) {
    const theta = ((c + 0.5) / CABLES) * TAU;
    const kink = c % 3 === 0 ? 0.22 : 0.09;
    const path = new Float32Array(cablePoints * 3);
    let p = 0;
    for (let i = 0; i < STAGES.length; i++) {
      const [y0, r0] = STAGES[i];
      const last = i === STAGES.length - 1;
      const y1 = last ? CHIP_Y : STAGES[i + 1][0];
      const r1 = last ? 0.55 : STAGES[i + 1][1] * 0.78;
      for (let k = (i === 0 ? 0 : 1); k <= CABLE_STEPS; k++) {
        const u = k / CABLE_STEPS;
        const r = r0 * 0.78 + (r1 - r0 * 0.78) * u + Math.sin(Math.PI * u) * kink;
        const a = theta + Math.sin(TAU * u) * 0.1;
        path[p++] = Math.cos(a) * r;
        path[p++] = y0 + (y1 - y0) * u;
        path[p++] = Math.sin(a) * r;
      }
    }
    for (let k = 0; k < cablePoints - 1; k++) {
      const o = k * 3;
      seg(path[o], path[o + 1], path[o + 2], path[o + 3], path[o + 4], path[o + 5], 0.3);
    }
    cables.push(path);
  }

  // chip: frame, stems up to the last plate, qubit grid with couplers
  const chipHalf = 0.75;
  for (const dy of [0, -0.06]) {
    seg(-chipHalf, CHIP_Y + dy, -chipHalf, chipHalf, CHIP_Y + dy, -chipHalf, 0.8);
    seg(chipHalf, CHIP_Y + dy, -chipHalf, chipHalf, CHIP_Y + dy, chipHalf, 0.8);
    seg(chipHalf, CHIP_Y + dy, chipHalf, -chipHalf, CHIP_Y + dy, chipHalf, 0.8);
    seg(-chipHalf, CHIP_Y + dy, chipHalf, -chipHalf, CHIP_Y + dy, -chipHalf, 0.8);
  }
  const lastPlateY = STAGES[STAGES.length - 1][0] - PLATE_THICKNESS;
  for (const [sx, sz] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
    seg(sx * chipHalf, CHIP_Y, sz * chipHalf, sx * chipHalf, lastPlateY, sz * chipHalf, 0.4);
  }
  const qubitXZ = (k) => [
    (k % CHIP_GRID - (CHIP_GRID - 1) / 2) * CHIP_PITCH,
    (Math.floor(k / CHIP_GRID) - (CHIP_GRID - 1) / 2) * CHIP_PITCH,
  ];
  for (let k = 0; k < QUBITS; k++) {
    const [x, z] = qubitXZ(k);
    if (k % CHIP_GRID < CHIP_GRID - 1) seg(x, CHIP_Y, z, x + CHIP_PITCH, CHIP_Y, z, 0.55);
    if (k < QUBITS - CHIP_GRID) seg(x, CHIP_Y, z, x, CHIP_Y, z + CHIP_PITCH, 0.55);
  }

  // orbits around the whole machine
  const orbitPoint = (i, angle, out, o) => {
    const [r, tiltZ, tiltX] = ORBITS[i];
    const x = Math.cos(angle) * r, z = Math.sin(angle) * r;
    const x1 = x * Math.cos(tiltZ), y1 = x * Math.sin(tiltZ);            // rotate about z
    out[o] = x1;
    out[o + 1] = y1 * Math.cos(tiltX) - z * Math.sin(tiltX) + 0.8;       // rotate about x, centre on the stack
    out[o + 2] = y1 * Math.sin(tiltX) + z * Math.cos(tiltX);
  };
  const tmpA = [0, 0, 0], tmpB = [0, 0, 0];
  ORBITS.forEach((_, i) => {
    for (let k = 0; k < 120; k++) {
      orbitPoint(i, (k / 120) * TAU, tmpA, 0);
      orbitPoint(i, ((k + 1) / 120) * TAU, tmpB, 0);
      seg(tmpA[0], tmpA[1], tmpA[2], tmpB[0], tmpB[1], tmpB[2], 0.28);
    }
  });

  const wireGeo = new THREE.BufferGeometry();
  wireGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(wire), 3));
  wireGeo.setAttribute("aAlpha", new THREE.BufferAttribute(new Float32Array(wireAlpha), 1));
  wireGeo.setAttribute("aFlash", new THREE.BufferAttribute(new Float32Array(wireAlpha.length), 1));
  uniforms.uWireOpacity = { value: 0 };
  uniforms.uDotOpacity = { value: 0 };
  const wireMesh = new THREE.LineSegments(wireGeo, new THREE.ShaderMaterial({
    ...materialBase,
    vertexShader: LINE_VERT,
    fragmentShader: LINE_FRAG,
    uniforms: { uColor: uniforms.uLink, uFlash: uniforms.uFlash, uOpacity: uniforms.uWireOpacity },
  }));

  // moving points: [qubits | pulses | electrons]
  const DOTS = QUBITS + MAX_PULSES + ELECTRONS;
  const PULSE_0 = QUBITS, ELECTRON_0 = QUBITS + MAX_PULSES;
  const dotPos = new Float32Array(DOTS * 3);
  const dotSize = new Float32Array(DOTS);
  const dotAlpha = new Float32Array(DOTS);
  const dotFlash = new Float32Array(DOTS);
  const qubitGlow = new Float32Array(QUBITS);
  const pulseCable = new Uint8Array(MAX_PULSES);
  const pulseT = new Float32Array(MAX_PULSES);
  const pulseSpeed = new Float32Array(MAX_PULSES);
  const pulsePresence = new Float32Array(MAX_PULSES);
  for (let k = 0; k < QUBITS; k++) {
    const [x, z] = qubitXZ(k);
    dotPos.set([x, CHIP_Y, z], k * 3);
    dotSize[k] = 0.75;
  }
  for (let p = 0; p < MAX_PULSES; p++) {
    pulseCable[p] = Math.floor(Math.random() * CABLES);
    pulseT[p] = Math.random();
    pulseSpeed[p] = 0.07 + Math.random() * 0.11;
    dotSize[PULSE_0 + p] = 0.5 + Math.random() * 0.3;
  }
  for (let e = 0; e < ELECTRONS; e++) dotSize[ELECTRON_0 + e] = 0.9;

  const dotGeo = new THREE.BufferGeometry();
  const dotPosAttr = new THREE.BufferAttribute(dotPos, 3).setUsage(THREE.DynamicDrawUsage);
  const dotAlphaAttr = new THREE.BufferAttribute(dotAlpha, 1).setUsage(THREE.DynamicDrawUsage);
  const dotFlashAttr = new THREE.BufferAttribute(dotFlash, 1).setUsage(THREE.DynamicDrawUsage);
  dotGeo.setAttribute("position", dotPosAttr);
  dotGeo.setAttribute("aSize", new THREE.BufferAttribute(dotSize, 1));
  dotGeo.setAttribute("aAlpha", dotAlphaAttr);
  dotGeo.setAttribute("aFlash", dotFlashAttr);
  const dots = new THREE.Points(dotGeo, new THREE.ShaderMaterial({
    ...materialBase,
    vertexShader: POINT_VERT,
    fragmentShader: POINT_FRAG,
    uniforms: {
      uColor: uniforms.uColor, uFlash: uniforms.uFlash, uHalo: uniforms.uHalo,
      uScale: uniforms.uScale, uOpacity: uniforms.uDotOpacity,
    },
  }));
  wireMesh.frustumCulled = dots.frustumCulled = false;
  sculpture.add(wireMesh, dots);
  sculpture.rotation.x = 0.2;                            // seen slightly from above
  scene.add(sculpture);
  let sculptureDim = 1, spin = 0;

  // ---- swarm: formations are just point lists; the frame loop flies between them ----
  const formations = [];
  const formation = (fn) => {
    const out = new Float32Array(SWARM * 3);
    for (let i = 0; i < SWARM; i++) out.set(fn(i / SWARM, i), i * 3);
    formations.push(out);
  };
  const lerp2 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

  formation((u) => {                                     // smile
    if (u < 0.5) { const a = (u / 0.5) * TAU; return [Math.cos(a) * 2, Math.sin(a) * 2, 0]; }
    if (u < 0.74) {                                      // eyes
      const left = u < 0.62, a = ((u - (left ? 0.5 : 0.62)) / 0.12) * TAU;
      return [(left ? -0.7 : 0.7) + Math.cos(a) * 0.22, 0.6 + Math.sin(a) * 0.3, 0];
    }
    const a = Math.PI * (1.15 + 0.7 * ((u - 0.74) / 0.26));
    return [Math.cos(a) * 1.2, Math.sin(a) * 1.2 + 0.15, 0];
  });
  formation((u) => {                                     // flower
    if (u < 0.82) {
      const a = (u / 0.82) * TAU, r = 0.65 + 1.45 * Math.abs(Math.cos(3 * a));
      return [Math.cos(a) * r, Math.sin(a) * r, 0];
    }
    const a = ((u - 0.82) / 0.18) * TAU;
    return [Math.cos(a) * 0.42, Math.sin(a) * 0.42, 0.25];
  });
  formation((u, i) => {                                  // sphere (fibonacci)
    const y = 1 - 2 * u, r = Math.sqrt(1 - y * y), a = i * 2.39996;
    return [Math.cos(a) * r * 1.9, y * 1.9, Math.sin(a) * r * 1.9];
  });
  formation((u) => {                                     // heart
    const a = u * TAU, k = 0.125;
    return [
      16 * Math.sin(a) ** 3 * k,
      (13 * Math.cos(a) - 5 * Math.cos(2 * a) - 2 * Math.cos(3 * a) - Math.cos(4 * a)) * k + 0.2,
      0,
    ];
  });
  const CUBE_EDGES = [];
  for (let a = 0; a < 8; a++) {
    for (let b = a + 1; b < 8; b++) {
      if ([1, 2, 4].includes(a ^ b)) CUBE_EDGES.push([a, b]);   // corners differing in one axis
    }
  }
  const corner = (n) => [(n & 1 ? 1 : -1) * 1.4, (n & 2 ? 1 : -1) * 1.4, (n & 4 ? 1 : -1) * 1.4];
  formation((u) => {                                     // cube
    const f = u * CUBE_EDGES.length, e = Math.min(CUBE_EDGES.length - 1, Math.floor(f));
    return lerp2(corner(CUBE_EDGES[e][0]), corner(CUBE_EDGES[e][1]), f - e);
  });
  formation((u) => {                                     // atom
    if (u >= 0.9) { const a = ((u - 0.9) / 0.1) * TAU; return [Math.cos(a) * 0.25, Math.sin(a) * 0.25, 0]; }
    const j = Math.floor(u / 0.3), a = ((u - j * 0.3) / 0.3) * TAU, tilt = (j * Math.PI) / 3;
    const x = Math.cos(a) * 2.1, y = Math.sin(a) * 0.75;
    return [x * Math.cos(tilt) - y * Math.sin(tilt), x * Math.sin(tilt) + y * Math.cos(tilt), Math.sin(a) * 0.4];
  });
  const starPoint = (n) => {
    const a = Math.PI / 2 + (n / 10) * TAU, r = n % 2 ? 0.85 : 2.1;
    return [Math.cos(a) * r, Math.sin(a) * r, 0];
  };
  formation((u) => {                                     // star
    const f = u * 10, e = Math.min(9, Math.floor(f));
    return lerp2(starPoint(e), starPoint((e + 1) % 10), f - e);
  });

  const swarm = new THREE.Group();
  const swarmPos = new Float32Array(SWARM * 3);
  const swarmSize = new Float32Array(SWARM);
  const swarmAlpha = new Float32Array(SWARM).fill(1);
  const swarmFlash = new Float32Array(SWARM);
  const swarmDelay = new Float32Array(SWARM);            // staggers take-off per point
  for (let i = 0; i < SWARM; i++) {
    swarmSize[i] = 0.8 + Math.random() * 0.2;
    swarmDelay[i] = Math.random();
  }
  const swarmGeo = new THREE.BufferGeometry();
  const swarmPosAttr = new THREE.BufferAttribute(swarmPos, 3).setUsage(THREE.DynamicDrawUsage);
  const swarmFlashAttr = new THREE.BufferAttribute(swarmFlash, 1).setUsage(THREE.DynamicDrawUsage);
  swarmGeo.setAttribute("position", swarmPosAttr);
  swarmGeo.setAttribute("aSize", new THREE.BufferAttribute(swarmSize, 1));
  swarmGeo.setAttribute("aAlpha", new THREE.BufferAttribute(swarmAlpha, 1));
  swarmGeo.setAttribute("aFlash", swarmFlashAttr);
  uniforms.uSwarmOpacity = { value: 0 };
  const swarmDots = new THREE.Points(swarmGeo, new THREE.ShaderMaterial({
    ...materialBase,
    vertexShader: POINT_VERT,
    fragmentShader: POINT_FRAG,
    uniforms: {
      uColor: uniforms.uColor, uFlash: uniforms.uFlash, uHalo: uniforms.uHalo,
      uScale: uniforms.uScale, uOpacity: uniforms.uSwarmOpacity,
    },
  }));
  swarmDots.frustumCulled = false;
  swarm.add(swarmDots);

  scene.add(swarm);
  let swarmDim = 1, wideLayout = true, maxScroll = 0;

  // ---- layout: a jittered grid, filled in random order ----
  // The base themes light up the first `baseCount` sites; quantum fills the rest.
  let width = 0, height = 0;
  let spreadX = 1, spreadY = 1;
  let baseCount = 0, quantumCount = 0;

  function measure() {
    // canvas box, not the window: its CSS height (100lvh) ignores the mobile URL bar
    width = canvas.clientWidth || window.innerWidth;
    height = canvas.clientHeight || window.innerHeight;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    const halfH = Math.tan(THREE.MathUtils.degToRad(FOV / 2)) * CAMERA_Z;
    spreadY = halfH * OVERSCAN;
    spreadX = halfH * camera.aspect * OVERSCAN;
    // sculpture: big and off to the right on wide screens, centred and dimmer on narrow ones
    const wide = camera.aspect > 1.1;
    sculpture.position.x = wide ? halfH * camera.aspect * 0.5 : 0;
    sculpture.scale.setScalar(wide ? 1.25 : clamp((halfH * camera.aspect) / 3.2, 0.6, 1));
    sculptureDim = wide ? 1 : 0.5;
    // swarm: lower-left on wide screens; on narrow ones it is centred and
    // cross-fades with the sculpture as the page scrolls (see frame loop)
    wideLayout = wide;
    swarm.position.x = wide ? -halfH * camera.aspect * 0.52 : 0;
    swarm.scale.setScalar(wide ? 1.2 : clamp((halfH * camera.aspect) / 2.5, 0.7, 1.3));
    swarmDim = wide ? 1 : 0;
    maxScroll = Math.max(0, root.scrollHeight - height);
    uniforms.uScale.value = SPRITE_PX * CAMERA_Z * renderer.getPixelRatio();
  }

  function buildLattice() {
    baseCount = clamp(Math.round((width * height) / 18000), 24, 100);
    quantumCount = Math.min(MAX_NODES, Math.round(baseCount * 1.8));
    const cols = Math.max(2, Math.round(Math.sqrt(quantumCount * spreadX / spreadY)));
    const rows = Math.ceil(quantumCount / cols);
    const cells = Array.from({ length: cols * rows }, (_, i) => i);
    for (let i = cells.length - 1; i > 0; i--) {           // Fisher-Yates
      const j = Math.floor(Math.random() * (i + 1));
      [cells[i], cells[j]] = [cells[j], cells[i]];
    }
    for (let i = 0; i < quantumCount; i++) {
      const cx = cells[i] % cols, cy = Math.floor(cells[i] / cols);
      const jitter = () => (Math.random() - 0.5) * 0.76;
      home[i * 3] = ((cx + 0.5 + jitter()) / cols) * 2 - 1;
      home[i * 3 + 1] = ((cy + 0.5 + jitter()) / rows) * 2 - 1;
      home[i * 3 + 2] = Math.random() * 2 - 1;
      for (let k = 0; k < 3; k++) {
        phase[i * 3 + k] = Math.random() * Math.PI * 2;
        speed[i * 3 + k] = 0.12 + Math.random() * 0.22;
      }
      size[i] = 0.7 + Math.random() * 0.8;
      flashClock[i] = -1;
    }
    pointGeo.attributes.aSize.needsUpdate = true;
    pointGeo.setDrawRange(0, quantumCount);
  }

  // ---- theme: targets are read from CSS, current values ease towards them ----
  const look = { node: [0, 0, 0], link: [0, 0, 0], flash: [0, 0, 0], nodeAlpha: 0, linkAlpha: 0, halo: 0 };
  const target = { ...look };
  let quantum = false;

  function readTheme() {
    const css = getComputedStyle(root);
    const num = (name, fallback) => parseFloat(css.getPropertyValue(name)) || fallback;
    target.node = parseHex(css.getPropertyValue("--scene-node"));
    target.link = parseHex(css.getPropertyValue("--scene-link"));
    target.flash = parseHex(css.getPropertyValue("--scene-flash"));
    target.nodeAlpha = num("--scene-node-alpha", 0.8);
    target.linkAlpha = num("--scene-link-alpha", 0.25);
    target.halo = num("--scene-halo", 0.4);
    quantum = root.dataset.theme === "quantum";
  }

  function easeLook(k) {
    for (const key of ["node", "link", "flash"]) {
      for (let c = 0; c < 3; c++) look[key][c] += (target[key][c] - look[key][c]) * k;
    }
    look.nodeAlpha += (target.nodeAlpha - look.nodeAlpha) * k;
    look.linkAlpha += (target.linkAlpha - look.linkAlpha) * k;
    look.halo += (target.halo - look.halo) * k;
    uniforms.uColor.value.fromArray(look.node);
    uniforms.uLink.value.fromArray(look.link);
    uniforms.uFlash.value.fromArray(look.flash);
    uniforms.uHalo.value = look.halo;
  }

  // ---- input ----
  const pointer = { x: 0, y: 0 };
  let camX = 0, camY = 0;
  let scrollEased = window.scrollY;
  window.addEventListener("pointermove", (e) => {
    if (e.pointerType !== "mouse") return;
    pointer.x = (e.clientX / width) * 2 - 1;
    pointer.y = (e.clientY / height) * 2 - 1;
  }, { passive: true });

  // ---- frame ----
  let time = 0, last = 0, raf = 0;
  let linkRadius = 0;
  let nextFlash = 1;

  function frame(now) {
    raf = requestAnimationFrame(frame);
    const dt = clamp((now - last) / 1000, 0, 0.05);   // rAF time can trail performance.now()
    last = now;
    time += dt;
    const ease = 1 - Math.exp(-dt * 3.5);

    easeLook(ease);

    // scroll: lattice drifts up, camera pulls back a little, scene dims below the hero
    scrollEased += (window.scrollY - scrollEased) * (1 - Math.exp(-dt * 3));
    const scrolled = clamp(scrollEased / height, 0, 1);
    const shiftY = scrollEased * SCROLL_SHIFT;
    uniforms.uNodeOpacity.value = look.nodeAlpha * (1 - 0.4 * scrolled);
    uniforms.uLinkOpacity.value = look.linkAlpha * (1 - 0.4 * scrolled);

    // mouse parallax
    camX += (pointer.x * 0.9 - camX) * ease;
    camY += (-pointer.y * 0.6 - camY) * ease;
    camera.position.set(camX, camY, CAMERA_Z + scrolled * 0.6);
    camera.lookAt(0, 0, 0);

    // narrow screens: the machine owns the top of the page, the drone show the bottom
    if (!wideLayout) {
      const progress = maxScroll > 0 ? clamp(scrollEased / maxScroll, 0, 1) : 0;
      sculptureDim = 0.5 * (1 - smooth(clamp(progress / 0.7, 0, 1)));
      swarmDim = smooth(clamp((progress - 0.3) / 0.65, 0, 1));
    }

    // sculpture: slow spin (scroll turns it further), pulses run down the cables
    spin += dt * (quantum ? 0.11 : 0.06);
    sculpture.rotation.y = spin + scrollEased * 0.0004 + camX * 0.08;
    sculpture.position.y = 0.3 + Math.min(shiftY * 0.4, 2.5);
    uniforms.uWireOpacity.value = Math.min(1, look.linkAlpha * 1.6) * sculptureDim * (1 - 0.4 * scrolled);
    uniforms.uDotOpacity.value = look.nodeAlpha * sculptureDim * (1 - 0.4 * scrolled);

    const pulses = quantum ? MAX_PULSES : BASE_PULSES;
    for (let p = 0; p < MAX_PULSES; p++) {
      pulsePresence[p] += ((p < pulses ? 1 : 0) - pulsePresence[p]) * (1 - Math.exp(-dt * 2));
      pulseT[p] += dt * pulseSpeed[p] * (quantum ? 1.6 : 1);
      if (pulseT[p] >= 1) {                              // reached the chip: a qubit lights up
        if (pulsePresence[p] > 0.5) qubitGlow[Math.floor(Math.random() * QUBITS)] = 1;
        pulseT[p] = 0;
        pulseCable[p] = Math.floor(Math.random() * CABLES);
      }
      const path = cables[pulseCable[p]];
      const f = pulseT[p] * (cablePoints - 1);
      const k = Math.min(cablePoints - 2, Math.floor(f)), u = f - k;
      const a = k * 3, d = (PULSE_0 + p) * 3;
      dotPos[d] = path[a] + (path[a + 3] - path[a]) * u;
      dotPos[d + 1] = path[a + 1] + (path[a + 4] - path[a + 1]) * u;
      dotPos[d + 2] = path[a + 2] + (path[a + 5] - path[a + 2]) * u;
      dotAlpha[PULSE_0 + p] = pulsePresence[p] * Math.sin(Math.PI * pulseT[p]);
      dotFlash[PULSE_0 + p] = quantum && p % 3 === 0 ? 1 : 0;
    }
    for (let k = 0; k < QUBITS; k++) {
      qubitGlow[k] *= Math.exp(-dt * 2.2);
      dotAlpha[k] = Math.min(1, 0.4 + 0.15 * Math.sin(time * 1.3 + k * 1.7) + qubitGlow[k]);
      dotFlash[k] = qubitGlow[k] * 0.9;
    }
    for (let e = 0; e < ELECTRONS; e++) {
      const i = e % ORBITS.length;
      const angle = time * (0.22 + i * 0.07) * (e < ORBITS.length ? 1 : -0.7) + e * 2.1;
      orbitPoint(i, angle, dotPos, (ELECTRON_0 + e) * 3);
      dotAlpha[ELECTRON_0 + e] = 0.9;
      dotFlash[ELECTRON_0 + e] = e % 2;
    }
    dotPosAttr.needsUpdate = dotAlphaAttr.needsUpdate = dotFlashAttr.needsUpdate = true;

    // swarm: hold a formation, then every point flies to its slot in the next one
    if (swarmDim > 0) {
      const cycle = SWARM_HOLD + SWARM_MORPH;
      const step = Math.floor(time / cycle);
      const from = formations[step % formations.length];
      const to = formations[(step + 1) % formations.length];
      const morph = clamp((time - step * cycle - SWARM_HOLD) / SWARM_MORPH, 0, 1);
      for (let i = 0; i < SWARM; i++) {
        const o = i * 3;
        const m = smooth(clamp(morph * 1.6 - swarmDelay[i] * 0.6, 0, 1));
        const lift = Math.sin(Math.PI * m);              // arc out of the plane mid-flight
        swarmPos[o] = from[o] + (to[o] - from[o]) * m + Math.sin(time * 1.1 + i) * 0.025;
        swarmPos[o + 1] = from[o + 1] + (to[o + 1] - from[o + 1]) * m + Math.cos(time * 0.9 + i * 1.7) * 0.025;
        swarmPos[o + 2] = from[o + 2] + (to[o + 2] - from[o + 2]) * m + lift * (swarmDelay[i] - 0.5) * 1.6;
        swarmFlash[i] = lift * (quantum ? 0.9 : 0.5);
      }
      swarmPosAttr.needsUpdate = swarmFlashAttr.needsUpdate = true;
      swarm.rotation.y = Math.sin(time * 0.25) * 0.4 + camX * 0.1;   // sway, so flat shapes stay readable
      swarm.rotation.x = Math.sin(time * 0.17) * 0.12;
      swarm.position.y = wideLayout ? -2.6 + Math.min(shiftY * 0.4, 2.5) : 0;
    }
    uniforms.uSwarmOpacity.value = wideLayout
      ? look.nodeAlpha * 0.85 * (1 - 0.4 * scrolled)
      : Math.min(1, look.nodeAlpha * 1.3) * swarmDim;

    // quantum: occasionally "measure" a node
    const active = quantum ? quantumCount : baseCount;
    if (quantum) {
      nextFlash -= dt;
      if (nextFlash <= 0) {
        const i = Math.floor(Math.random() * active);
        if (flashClock[i] < 0 && presence[i] > 0.9) flashClock[i] = 0;
        nextFlash = 0.3 + Math.random() * 0.9;
      }
    }

    // nodes
    const spanY = spreadY * 2;
    for (let i = 0; i < quantumCount; i++) {
      const o = i * 3;
      presence[i] += ((i < active ? 1 : 0) - presence[i]) * (1 - Math.exp(-dt * 2));

      pos[o] = home[o] * spreadX + Math.sin(time * speed[o] + phase[o]) * DRIFT;
      const y = home[o + 1] * spreadY + Math.cos(time * speed[o + 1] + phase[o + 1]) * DRIFT + shiftY;
      pos[o + 1] = ((y + spreadY) % spanY + spanY) % spanY - spreadY;   // wrap around
      pos[o + 2] = home[o + 2] * DEPTH + Math.sin(time * speed[o + 2] + phase[o + 2]) * DRIFT;

      // measurement envelope: flash up -> collapse to nothing -> re-emerge
      let scale = 1, glow = 0;
      if (flashClock[i] >= 0) {
        const p = (flashClock[i] += dt / FLASH_SECONDS);
        if (p >= 1) flashClock[i] = -1;
        else if (p < 0.12) { scale = 1 + 1.4 * (p / 0.12); glow = 1; }
        else if (p < 0.28) { scale = 2.4 * (1 - (p - 0.12) / 0.16); glow = 1; }
        else if (p < 0.5) { scale = 0; glow = 1; }
        else { scale = smooth((p - 0.5) / 0.5); glow = 1 - scale; }
      }
      alpha[i] = presence[i] * Math.min(1, scale);
      flash[i] = glow;
    }

    // links between near neighbours; radius tracks node density
    const targetRadius = 1.35 * Math.sqrt((spreadX * 2 * spanY) / Math.max(1, active));
    linkRadius += (targetRadius - linkRadius) * ease;
    const r2 = linkRadius * linkRadius;
    let n = 0;
    for (let i = 0; i < quantumCount && n < MAX_LINKS; i++) {
      if (alpha[i] < 0.02) continue;
      const a = i * 3;
      for (let j = i + 1; j < quantumCount && n < MAX_LINKS; j++) {
        if (alpha[j] < 0.02) continue;
        const b = j * 3;
        const dx = pos[a] - pos[b], dy = pos[a + 1] - pos[b + 1], dz = pos[a + 2] - pos[b + 2];
        const d2 = dx * dx + dy * dy + dz * dz;
        if (d2 > r2) continue;
        const fade = 1 - Math.sqrt(d2) / linkRadius;
        const v = n * 6;
        linkPos[v] = pos[a]; linkPos[v + 1] = pos[a + 1]; linkPos[v + 2] = pos[a + 2];
        linkPos[v + 3] = pos[b]; linkPos[v + 4] = pos[b + 1]; linkPos[v + 5] = pos[b + 2];
        linkAlpha[n * 2] = linkAlpha[n * 2 + 1] = fade * Math.min(alpha[i], alpha[j]);
        linkFlash[n * 2] = flash[i];
        linkFlash[n * 2 + 1] = flash[j];
        n++;
      }
    }
    linkGeo.setDrawRange(0, n * 2);

    posAttr.needsUpdate = alphaAttr.needsUpdate = flashAttr.needsUpdate = true;
    linkPosAttr.needsUpdate = linkAlphaAttr.needsUpdate = linkFlashAttr.needsUpdate = true;
    renderer.render(scene, camera);
  }

  // ---- run only while visible, on-screen and motion is welcome ----
  let onScreen = true, contextLost = false;
  function sync() {
    const run = !document.hidden && onScreen && !contextLost && !reduceMotion.matches;
    if (run && !raf) {
      last = performance.now();
      raf = requestAnimationFrame(frame);
    } else if (!run && raf) {
      cancelAnimationFrame(raf);
      raf = 0;
    }
    root.classList.toggle("scene-on", !reduceMotion.matches && !contextLost);
  }
  document.addEventListener("visibilitychange", sync);
  reduceMotion.addEventListener("change", sync);
  new IntersectionObserver(([entry]) => { onScreen = entry.isIntersecting; sync(); }).observe(canvas);
  canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); contextLost = true; sync(); });
  canvas.addEventListener("webglcontextrestored", () => { contextLost = false; sync(); });

  // page height changes (fonts, cards, resize) -> refresh the scroll range
  if ("ResizeObserver" in window) {
    new ResizeObserver(() => { maxScroll = Math.max(0, root.scrollHeight - height); }).observe(document.body);
  }

  // follow theme switches without any coupling to main.js
  new MutationObserver(readTheme).observe(root, { attributes: true, attributeFilter: ["data-theme"] });

  // resize: always re-fit; rebuild the lattice only when the shape really changed
  // (mobile URL-bar show/hide just changes height a little)
  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      const prevW = width, prevH = height;
      // URL-bar resizes leave the canvas box alone -> nothing to re-fit (setSize would clear the buffer)
      if (canvas.clientWidth === prevW && canvas.clientHeight === prevH) return;
      measure();
      if (width !== prevW || Math.abs(height - prevH) / prevH > 0.2) buildLattice();
    }, 150);
  }, { passive: true });

  measure();
  buildLattice();
  readTheme();
  for (const key of ["node", "link", "flash"]) look[key] = [...target[key]];
  look.nodeAlpha = target.nodeAlpha;
  look.linkAlpha = target.linkAlpha;
  look.halo = target.halo;
  sync();
  return true;
}

// three.js comes from the CDN as an ES module; any failure leaves the static backdrop
import(THREE_URL)
  .then((THREE) => initScene(THREE, document.getElementById("bg-canvas")))
  .catch(() => { /* CDN blocked or offline */ });
