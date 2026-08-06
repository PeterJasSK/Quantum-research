// Deterministic genetic-algorithm evolution of the hero title.
//
// A single quantum seed (fetched once from /random) drives a seeded PRNG that
// expands into the whole evolution -- so we never "eat" quantum bytes to
// infinity, and the exact same animation replays for anyone holding the same
// seed. Record the seed + timestamp and you have reproduced the run.

// Two 7-letter words, evolved as one 14-letter genome, split for display.
export const TARGET = "QUANTUMENTROPY";
export const SPLIT = 7; // chars [0,SPLIT) = line 1, [SPLIT,end) = line 2
const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const POP = 16; // 16 candidate strings compete each generation
const MAX_GEN = 600; // hard stop; convergence is typically far sooner

// mulberry32 -- tiny, fast, fully deterministic from a 32-bit seed.
function makePrng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// FNV-1a fold of the quantum bytes into a 32-bit PRNG seed.
export function seedFromBytes(bytes: Uint8Array): number {
  let h = 0x811c9dc5;
  for (const b of bytes) {
    h ^= b;
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function randChar(rng: () => number): string {
  return ALPHABET[Math.floor(rng() * ALPHABET.length)];
}

function randGenome(rng: () => number): string {
  let s = "";
  for (let i = 0; i < TARGET.length; i += 1) s += randChar(rng);
  return s;
}

function fitness(s: string): number {
  let f = 0;
  for (let i = 0; i < TARGET.length; i += 1) if (s[i] === TARGET[i]) f += 1;
  return f;
}

function crossover(a: string, b: string, rng: () => number): string {
  let child = "";
  for (let i = 0; i < TARGET.length; i += 1) {
    child += rng() < 0.5 ? a[i] : b[i];
  }
  return child;
}

// Correct letters "want to live": keep them almost always, scramble the rest.
function mutate(s: string, rng: () => number): string {
  let out = "";
  for (let i = 0; i < TARGET.length; i += 1) {
    const correct = s[i] === TARGET[i];
    const p = correct ? 0.01 : 0.28;
    out += rng() < p ? randChar(rng) : s[i];
  }
  return out;
}

export interface Frame {
  chars: string[];
  correct: boolean[];
  gen: number;
}

function toFrame(s: string, gen: number): Frame {
  const chars = s.split("");
  return { chars, correct: chars.map((c, i) => c === TARGET[i]), gen };
}

// Display churn: every wrong position gets a fresh random letter each frame so
// no incorrect slot sits visually frozen while the GA quietly locks the rest.
// Correct letters stay put. Uses the seeded PRNG, so it stays reproducible.
function displayFrame(s: string, gen: number, rng: () => number): Frame {
  const chars: string[] = [];
  const correct: boolean[] = [];
  for (let i = 0; i < TARGET.length; i += 1) {
    const ok = s[i] === TARGET[i];
    correct.push(ok);
    chars.push(ok ? TARGET[i] : randChar(rng));
  }
  return { chars, correct, gen };
}

// Run the full GA and return one frame per generation until the target is hit.
export function evolve(seed: number): Frame[] {
  const rng = makePrng(seed);
  let pop = Array.from({ length: POP }, () => randGenome(rng));
  const frames: Frame[] = [];

  for (let gen = 0; gen < MAX_GEN; gen += 1) {
    const scored = pop
      .map((s) => ({ s, f: fitness(s) }))
      .sort((x, y) => y.f - x.f);

    const best = scored[0].s;
    if (best === TARGET) {
      frames.push(toFrame(best, gen));
      break;
    }
    frames.push(displayFrame(best, gen, rng));

    // Elitism: the two fittest survive untouched ("higher chance to live"),
    // then breed the rest by crossing the two most-similar-to-ideal parents.
    const next: string[] = [scored[0].s, scored[1].s];
    while (next.length < POP) {
      const a = scored[Math.floor(rng() * rng() * scored.length)].s;
      const b = scored[Math.floor(rng() * rng() * scored.length)].s;
      next.push(mutate(crossover(a, b, rng), rng));
    }
    pop = next;
  }

  // Guarantee the last frame is the exact target even if MAX_GEN was hit.
  const last = frames[frames.length - 1];
  if (!last || last.chars.join("") !== TARGET) {
    frames.push(toFrame(TARGET, last ? last.gen + 1 : 0));
  }
  return frames;
}
