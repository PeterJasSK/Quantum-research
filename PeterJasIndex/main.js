// peterjas.sk — page behaviour. Vanilla JS, no dependencies.
// (The initial theme is set by a tiny inline script in <head> to avoid a flash.)

const root = document.documentElement;
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
const prefersLight = matchMedia("(prefers-color-scheme: light)");

// localStorage can throw (private mode, blocked site data) — never let it break the page
const store = {
  get(key) { try { return localStorage.getItem(key); } catch { return null; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch { /* ignore */ } },
};

// ---- projects data ----
const REPO = "https://github.com/PeterJasSK/Quantum-research/tree/main/";
const PROJECTS = [
  {
    title: "Q-EaaS — Quantum Entropy as a Service",
    status: "Live", cls: "live", featured: true, color: "#7ad9ff",
    desc: "A free API turning real QRNG bits into served randomness, dice rolls, cryptographic seeds and post-quantum ML-KEM key material — each issue carrying a signed, offline-verifiable provenance receipt. FastAPI service + Next.js explainer.",
    tags: ["FastAPI", "Next.js", "Postgres", "ML-KEM", "NIST SP 800-90A"],
    links: [
      { label: "Live site ↗", href: "https://qrng.peterjas.sk/" },
      { label: "Repo ↗", href: REPO + "qrng-eaas" }
    ]
  },
  {
    title: "Quantum Phantoms",
    status: "IN PROGRESS", cls: "progress", color: "#009999",
    desc: "A training-free pipeline that puts virtual lung nodules into real CT scans for testing detection AI. Nodules are placed by anatomy, grown by published tumour models and rendered with the host scanner's blur and noise. A quantum processor supplies the randomness: every run starts with a Bell test on IBM hardware, and its measured bits draw the nodules.",
    tags: [ "IBM Quantum", "Siemens"],
    links: [{ label: "Live site ↗", href: "https://phantom.peterjas.sk/" }]
  },
  {
    title: "Quantum Tree",
    status: "Live", cls: "live", color: "#9df3b0",
    desc: "A living tree grown on a real IBM Heron r2 quantum computer. Every growth step is one circuit; measured bits decide how it branches. Includes a falsifiable fork testing whether hardware entanglement imprints spatial correlation a classical surrogate can't reproduce.",
    tags: ["Qiskit", "IBM Quantum", "Generative art"],
    links: [
      { label: "Live site ↗", href: "https://tree.peterjas.sk/" },
    ]
  },
  {
    title: "Taxi taxi",
    status: "Live", cls: "live", color: "#ffde00",
    desc: "Congrats you went through all of the really interesting project. This is game I dreamed up in class on unity then rewrote with claude to treeJS and put on web enjoy",
    tags: ["FUN"],
    links: [
      { label: "Live site ↗", href: "https://taxi.peterjas.sk/" },
    ]
  },
  // {
  //   title: "artificial-life project",
  //   status: "IN PROGRESS", cls: "progress", color: "#12ddcb",
  //   desc: "Based on best definition and best source ever WIKI Quantum_artificial_life. I replicated results from 2018. I improved the archaic design and certified their result. Created enclosed one dimensional space, and put 2 living organism in the space and see what they do when they meet. :)",
  //   tags: ["Qiskit", "Education", "IBM Quantum"],
  //   links: [{ label: "Live site ↗", href: "https://quantum-artificial-life.vercel.app/" },{ label: "Repo ↗", href: REPO + "artificial-life" },{ label: "Wiki ↗", href: "https://en.wikipedia.org/wiki/Quantum_artificial_life" }]
  // },
  // {
  //   title: "The Attacker in the Gap — ECMP Salt-Collision DoS",
  //   status: "Live", cls: "live",  color: "#ff9db1",
  //   desc: "Guess an ECMP (Equal-Cost Multi-Path) load balancer's hash salt and one host no botnet can craft flows that all land on a single link, starving a victim. The fix: rotate the salt faster than it can be reconstructed. Live fat-tree lab, backed by QEaaS quantum entropy.",
  //   tags: ["ECMP", "Network security", "DoS", "Moving-target defence", "Next.js", "QEaaS"],
  //   links: [
  //     { label: "Live site ↗", href: "https://ecmp.peterjas.sk/" },
  //   ]
  // },
  // {
  //   title: "Progresso — Remote Personal Training",
  //   status: "Live", cls: "live",  color: "#a5f3c0",
  //   desc: "A platform that lets a trainer watch a trainee's progress and set goals to keep them on track. Each week the trainee logs body measurements and a progress photo; the trainer reviews the trends, compares photos over time, and adjusts the plan together with them. Django backend with a React/TypeScript Tailwind PWA that installs and works offline.",
  //   tags: ["Django", "React", "TypeScript", "Tailwind", "PWA", "Postgres"],
  //   links: [
  //     { label: "Live site ↗", href: "https://progresso.peterjas.sk/" },
  //   ]
  // },
  // {
  //   title: "Quantum Algorithms",
  //   status: "Complete", cls: "done", color: "#c4b5ff",
  //   desc: "A hands-on tour of 15 standard quantum algorithms — coin flip and Bell states up to Grover, QFT, phase estimation and Simon's. Self-contained lessons, all reproducible on Qiskit's local simulator.",
  //   tags: ["Qiskit", "Education", "Simulator"],
  //   links: [{ label: "Repo ↗", href: REPO + "QuantumAlgorithmsExplained" }]
  // },
  {
    title: "Bachelor Thesis — Bell-Pair QRNG",
    status: "Complete", cls: "done", color: "#ffcf9a",
    desc: "Design and implementation of a Bell-Pair quantum random number generator. The foundation the later QRNG projects grew from.",
    tags: ["Thesis", "QRNG", "TUKE"],
    links: [{ label: "Repo ↗", href: REPO + "BC" }]
  }
];

// ---- projects grid ----
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const projectCard = (p) => `
  <article class="card panel${p.featured ? " featured" : ""}" style="--card-color:${p.color}" data-reveal>
    <div class="top">
      <h3>${p.links.length ? `<a href="${p.links[0].href}" target="_blank" rel="noopener">${esc(p.title)}</a>` : esc(p.title)}</h3>
      <span class="status ${p.cls}">${esc(p.status)}</span>
    </div>
    <p>${esc(p.desc)}</p>
    <div class="chips">${p.tags.map((t) => `<span class="chip">${esc(t)}</span>`).join("")}</div>
    ${p.links.length ? `<div class="card-links">${p.links.map((l) => `<a href="${l.href}" target="_blank" rel="noopener">${esc(l.label)}</a>`).join("")}</div>` : ""}
  </article>`;

document.getElementById("grid").innerHTML = PROJECTS.length
  ? PROJECTS.map(projectCard).join("")
  : `<p class="empty">// nothing here yet</p>`;

// ---- theme ----
const THEME_KEY = "pj-theme", UNLOCK_KEY = "pj-quantum";
const themeButtons = [...document.querySelectorAll("[data-theme-btn]")];
const quantumButton = document.querySelector('[data-theme-btn="quantum"]');
const quantumBadge = document.getElementById("quantum-badge");
const systemTheme = () => (prefersLight.matches ? "light" : "dark");

// last light/dark theme, so the easter egg can switch back to it
let baseTheme = root.dataset.theme === "quantum" ? systemTheme() : root.dataset.theme;

function applyTheme(theme) {
  root.dataset.theme = theme;
  if (theme !== "quantum") baseTheme = theme;
  themeButtons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.themeBtn === theme)));
  quantumBadge.setAttribute("aria-pressed", String(theme === "quantum"));
}

function setTheme(theme, { persist = true } = {}) {
  if (persist) store.set(THEME_KEY, theme);
  if (theme === root.dataset.theme) return;
  if (reduceMotion.matches) {
    applyTheme(theme);
  } else if (document.startViewTransition) {
    document.startViewTransition(() => applyTheme(theme));   // native crossfade
  } else {
    root.classList.add("theme-fade");
    applyTheme(theme);
    setTimeout(() => root.classList.remove("theme-fade"), 450);
  }
}

function unlockQuantum() {
  store.set(UNLOCK_KEY, "1");
  quantumButton.hidden = false;
}

applyTheme(root.dataset.theme);                    // sync buttons with the inline head script
if (store.get(UNLOCK_KEY) === "1") quantumButton.hidden = false;

themeButtons.forEach((b) => b.addEventListener("click", () => setTheme(b.dataset.themeBtn)));

// no saved choice yet -> keep following the OS setting
prefersLight.addEventListener("change", () => {
  if (!store.get(THEME_KEY)) setTheme(systemTheme(), { persist: false });
});

// easter egg 1: the footer badge toggles the quantum theme
quantumBadge.addEventListener("click", () => {
  if (root.dataset.theme === "quantum") return setTheme(baseTheme);
  unlockQuantum();
  setTheme("quantum");
});

// easter egg 2: tap brand 5x within 3s -> unlock quantum
let taps = [];
document.getElementById("brand").addEventListener("click", () => {
  const now = Date.now();
  taps = [...taps, now].filter((t) => now - t <= 3000);
  if (taps.length >= 5) {
    taps = [];
    unlockQuantum();
    setTheme("quantum");
  }
});

// easter egg 3: `?` or the Konami code toggles the layout grid overlay
const KONAMI = ["ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown", "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight", "b", "a"];
let konamiStep = 0;
window.addEventListener("keydown", (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key === "?") return root.classList.toggle("show-grid");
  konamiStep = e.key === KONAMI[konamiStep] ? konamiStep + 1 : Number(e.key === KONAMI[0]);
  if (konamiStep === KONAMI.length) {
    konamiStep = 0;
    root.classList.toggle("show-grid");
  }
});

// ---- header: shrink + glass once the page is scrolled ----
const header = document.querySelector(".site-header");
const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 16);
window.addEventListener("scroll", onScroll, { passive: true });
onScroll();

// ---- fade-and-rise on scroll ----
// CSS only hides [data-reveal] when motion is allowed, so nothing to do otherwise.
const revealTargets = [...document.querySelectorAll("[data-reveal]")];
if ("IntersectionObserver" in window && !reduceMotion.matches) {
  const revealer = new IntersectionObserver((entries) => {
    entries.filter((e) => e.isIntersecting).forEach((entry, i) => {
      const el = entry.target;
      el.style.setProperty("--reveal-delay", `${i * 80}ms`);   // stagger siblings entering together
      el.classList.add("is-in");
      revealer.unobserve(el);
      // drop the reveal hooks afterwards so hover transitions are not delayed
      setTimeout(() => {
        el.removeAttribute("data-reveal");
        el.classList.remove("is-in");
        el.style.removeProperty("--reveal-delay");
      }, 900 + i * 80);
    });
  }, { threshold: 0.1, rootMargin: "0px 0px -6% 0px" });
  revealTargets.forEach((el) => revealer.observe(el));
} else {
  revealTargets.forEach((el) => el.removeAttribute("data-reveal"));
}

// ---- magnetic buttons (mouse only) ----
if (matchMedia("(hover: hover) and (pointer: fine)").matches) {
  document.querySelectorAll(".btn").forEach((btn) => {
    btn.addEventListener("pointermove", (e) => {
      if (reduceMotion.matches) return;
      const r = btn.getBoundingClientRect();
      btn.style.setProperty("--mx", `${((e.clientX - r.left - r.width / 2) * 0.18).toFixed(1)}px`);
      btn.style.setProperty("--my", `${((e.clientY - r.top - r.height / 2) * 0.3).toFixed(1)}px`);
    });
    btn.addEventListener("pointerleave", () => {
      btn.style.removeProperty("--mx");
      btn.style.removeProperty("--my");
    });
  });
}

// ---- 3D background: lazy-loaded after first paint, never required ----
function loadScene() {
  if (reduceMotion.matches) return;                // static backdrop stays
  const probe = document.createElement("canvas");
  if (!probe.getContext("webgl2")) return;         // no WebGL -> static backdrop stays
  const script = document.createElement("script");  // classic script: also works from file://
  script.src = "scene.js";
  document.head.append(script);
}
const whenIdle = window.requestIdleCallback || ((fn) => setTimeout(fn, 200));
if (document.readyState === "complete") whenIdle(loadScene);
else window.addEventListener("load", () => whenIdle(loadScene), { once: true });
