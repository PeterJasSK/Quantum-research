// Tier B replay data source (AC-5). Loads a recorded sweep subset from
// public/replay/ -- not populated yet, P5 is Draft (see plan §Dependencies).
import type { PortStatsMessage } from "./ws";

export async function loadReplaySweep(name: string): Promise<PortStatsMessage[]> {
  const response = await fetch(`${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/replay/${name}.json`);
  if (!response.ok) {
    throw new Error(`replay sweep not found: ${name} (P5 has not landed this recording yet)`);
  }
  return (await response.json()) as PortStatsMessage[];
}
