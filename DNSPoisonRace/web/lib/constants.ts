// UI defaults mirroring testbed/config.py -- keep values identical to the Python
// source of truth. NOT read from Python; these are display/animation defaults for
// the browser (plan P6 lib/constants.ts).
export const TXID_BITS = 16;
export const PORT_BITS = 16;
export const RTT_SECONDS = 0.02;
export const RETRANSMIT_SECONDS = 0.5;
export const RTT_JITTER_FRAC = 0.1;
export const ATTACKER_SEND_RATE_PPS = 10000;

// Entropy sweep bounds (epic 8->32) used by the effectiveBits slider.
export const EFF_BITS_MIN = 8;
export const EFF_BITS_MAX = 32;
