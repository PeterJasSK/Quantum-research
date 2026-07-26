// Thin type declarations for the vendored testbed/vectors/ecmp_hash.js
// (D-parity). Do not add logic here -- types only.

export interface FiveTuple {
  src_ip: string;
  dst_ip: string;
  src_port: number;
  dst_port: number;
  proto: number;
}

export function fiveTupleToBytes(fiveTuple: FiveTuple): Uint8Array;

// ecmpLink is async: it awaits crypto.subtle.digest. Every call site must await it.
export function ecmpLink(fiveTuple: FiveTuple, saltHex: string, nLinks: number): Promise<number>;
