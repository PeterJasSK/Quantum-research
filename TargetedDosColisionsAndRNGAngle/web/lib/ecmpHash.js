/**
 * JS mirror of testbed/hash_core.py + testbed/types.py (AC-5). Load-bearing:
 * must reproduce the exact same bytes and `link` as the Python source of
 * truth. One copy, imported unchanged by the P6 demo and by
 * check_parity.py (via Node) -- no drift.
 *
 * Uses SubtleCrypto (crypto.subtle.digest) so it runs unchanged in a
 * browser; Node exposes the same API via the global `crypto`.
 */

function ipToBytes(ip) {
  const parts = ip.split(".").map((p) => parseInt(p, 10));
  if (parts.length !== 4 || parts.some((p) => Number.isNaN(p) || p < 0 || p > 255)) {
    throw new Error(`invalid IPv4 address: ${ip}`);
  }
  return Uint8Array.from(parts);
}

function fiveTupleToBytes(fiveTuple) {
  const { src_ip, dst_ip, src_port, dst_port, proto } = fiveTuple;
  const bytes = new Uint8Array(4 + 4 + 2 + 2 + 1);
  bytes.set(ipToBytes(src_ip), 0);
  bytes.set(ipToBytes(dst_ip), 4);
  const view = new DataView(bytes.buffer);
  view.setUint16(8, src_port, false); // big-endian
  view.setUint16(10, dst_port, false);
  view.setUint8(12, proto);
  return bytes;
}

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return bytes;
}

function concatBytes(...arrays) {
  const total = arrays.reduce((sum, a) => sum + a.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const a of arrays) {
    out.set(a, offset);
    offset += a.length;
  }
  return out;
}

/** First 8 bytes of the digest as a big-endian uint64, via BigInt. */
function first8BytesAsBigUint64BE(digestBytes) {
  let value = 0n;
  for (let i = 0; i < 8; i++) {
    value = (value << 8n) | BigInt(digestBytes[i]);
  }
  return value;
}

/** async: link = hash(5tuple, salt) mod N (AC-1), mirroring hash_core.ecmp_link. */
async function ecmpLink(fiveTuple, saltHex, nLinks) {
  const message = concatBytes(fiveTupleToBytes(fiveTuple), hexToBytes(saltHex));
  const digestBuffer = await crypto.subtle.digest("SHA-256", message);
  const digestBytes = new Uint8Array(digestBuffer);
  const value = first8BytesAsBigUint64BE(digestBytes);
  return Number(value % BigInt(nLinks));
}

const ecmpHash = { fiveTupleToBytes, ecmpLink };

if (typeof module !== "undefined" && module.exports) {
  module.exports = ecmpHash;
}
if (typeof globalThis !== "undefined") {
  globalThis.ecmpHash = ecmpHash;
}
