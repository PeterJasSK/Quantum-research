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

// Same-origin Next route-handler proxies (e.g. /api/kem/*) -- never prefixed
// with API_BASE, since that may point directly at FastAPI and would bypass
// the proxy that keeps the API key server-only.
async function requestJsonSameOrigin<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, init);
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

export interface IssueMeta {
  request_id: string;
  entropy_epoch: number;
  timestamp: string;
  receipt: string | null;
}

export interface KemKeypair extends IssueMeta {
  public_key: string;
  algorithm: "ML-KEM-768";
  format: "base64";
}

export interface KemEncapsulation extends IssueMeta {
  ciphertext: string;
  shared_secret: string;
  demo_key: string;
  note: string;
  algorithm: "ML-KEM-768";
  format: "base64";
}

export function base64ToBytes(base64: string): Uint8Array<ArrayBuffer> {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export async function kemKeypair(): Promise<KemKeypair> {
  return requestJsonSameOrigin<KemKeypair>("/api/kem/keypair", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({}),
  });
}

export async function kemEncapsulate(
  publicKey: string,
): Promise<KemEncapsulation> {
  return requestJsonSameOrigin<KemEncapsulation>("/api/kem/encapsulate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      public_key: publicKey,
      include_shared_secret: true,
    }),
  });
}

export interface VerifyResult {
  request_id: string | null;
  verified: boolean;
  provenance: Record<string, unknown> | null;
  note: string;
}

export async function verifyReceipt(input: {
  receipt?: string;
  request_id?: string;
}): Promise<VerifyResult> {
  return requestJson<VerifyResult>("/v1/verify", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(input),
  });
}
