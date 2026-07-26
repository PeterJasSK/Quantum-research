// Collision-set / bucket-spread demo logic (AC-3/4). Awaits the vendored,
// async ecmpLink (D-parity) -- never re-implements the hash.
import { ecmpLink, type FiveTuple } from "./ecmpHash.js";
import { N_LINKS } from "./constants";

export type { FiveTuple };

/** One crafted flow the attacker sends; src_port varies to search for a colliding link. */
export function craftedFiveTuple(srcPort: number): FiveTuple {
  return {
    src_ip: "10.0.0.1",
    dst_ip: "10.0.0.2",
    src_port: srcPort,
    dst_port: 80,
    proto: 6,
  };
}

/**
 * Buckets `count` crafted flows (src_port = basePort..basePort+count-1) into
 * their ECMP link under `saltHex`. Returns per-link flow counts, length N_LINKS.
 */
export async function bucketSpread(
  saltHex: string,
  count: number,
  nLinks: number = N_LINKS,
  basePort = 40000,
): Promise<number[]> {
  const counts = new Array<number>(nLinks).fill(0);
  for (let i = 0; i < count; i++) {
    const fiveTuple = craftedFiveTuple(basePort + i);
    // eslint-disable-next-line no-await-in-loop
    const link = await ecmpLink(fiveTuple, saltHex, nLinks);
    counts[link] += 1;
  }
  return counts;
}

/**
 * Precision mode (Scene 2): searches src_port..src_port+searchWindow for the
 * first 5-tuple that lands on `targetLink` under `saltHex` -- this is what a
 * knowledgeable attacker with a predictable salt can do offline.
 */
export async function findColliding5Tuple(
  saltHex: string,
  targetLink: number,
  nLinks: number = N_LINKS,
  basePort = 40000,
  searchWindow = 2000,
): Promise<FiveTuple | null> {
  for (let i = 0; i < searchWindow; i++) {
    const fiveTuple = craftedFiveTuple(basePort + i);
    // eslint-disable-next-line no-await-in-loop
    const link = await ecmpLink(fiveTuple, saltHex, nLinks);
    if (link === targetLink) {
      return fiveTuple;
    }
  }
  return null;
}
