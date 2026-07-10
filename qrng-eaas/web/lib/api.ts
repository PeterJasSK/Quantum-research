export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

export interface Health {
  status: string;
  quantum_entropy_level: "healthy" | "degraded";
  pool_bytes_remaining: number;
  drbg_reseeds: number;
  uptime: number;
}

export interface DiceRoll {
  sides: number;
  count: number;
  rolls: number[];
  format: "base64";
  bytes_used: string;
  bytes_count: number;
}

export class ApiError extends Error {
  readonly slug: string;

  constructor(slug: string) {
    super(slug);
    this.slug = slug;
  }
}

async function parseErrorSlug(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (
      typeof body === "object" &&
      body !== null &&
      "error" in body &&
      typeof (body as { error: unknown }).error === "string"
    ) {
      return (body as { error: string }).error;
    }
  } catch {
    // fall through to the generic slug below
  }
  return "unknown_error";
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    throw new ApiError(await parseErrorSlug(response));
  }
  return (await response.json()) as T;
}

export async function getHealth(): Promise<Health> {
  return requestJson<Health>("/health");
}

export async function rollDice(
  sides: number,
  count: number,
): Promise<DiceRoll> {
  return requestJson<DiceRoll>("/dice", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sides, count }),
  });
}
