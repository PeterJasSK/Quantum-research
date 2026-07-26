// Weak-PRNG vs CSPRNG salt sources for the demo (mirrors testbed/salt_engine
// prng/csprng distinction from P1, EPIC1-P2 -- landed 6adb4d2). Tier A only
// needs to *demonstrate* predictability, not reproduce the exact Python PRNG
// bit-for-bit: a simple LCG seeded from a fixed, small counter is enough to
// show "the attacker could predict this offline."

const SALT_BYTES = 36; // matches hash_vectors.json salt_hex length (72 hex chars)

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Weak PRNG: LCG seeded by a small counter -- an attacker who knows the
 * seed/counter can predict every future salt offline (Scene 2's premise). */
export function weakPrngSaltHex(counter: number): string {
  let state = (counter * 1103515245 + 12345) >>> 0;
  const bytes = new Uint8Array(SALT_BYTES);
  for (let i = 0; i < SALT_BYTES; i++) {
    state = (state * 1103515245 + 12345) >>> 0;
    bytes[i] = (state >>> 16) & 0xff;
  }
  return bytesToHex(bytes);
}

/** CSPRNG: crypto.getRandomValues -- unpredictable, matches Scene 1/3's premise. */
export function csprngSaltHex(): string {
  const bytes = new Uint8Array(SALT_BYTES);
  crypto.getRandomValues(bytes);
  return bytesToHex(bytes);
}
