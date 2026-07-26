// QRNG provenance display (epic §3.2, D-qrng-key). Tier A/replay read a
// recorded provenance record -- a static bundle must never embed the
// Q-EaaS API key. Tier B live receipts would go through the controller
// proxy (not implemented here; see plan §Dependencies P4/OQ-2).
export interface QrngProvenance {
  request_id: string;
  entropy_epoch: number;
  timestamp: string;
  size: number;
  endpoint: string;
  receipt: string;
}

// PLACEHOLDER pending P5 (Draft): P5 has not yet produced a recorded Q-EaaS
// provenance run. This record is a structurally-accurate SAMPLE for the demo
// UI -- it is not a real Q-EaaS receipt. Replace with P5's recorded record
// (public/replay/qrng-provenance.json) once P5 lands; do not present this
// sample as a real attestation.
export const SAMPLE_QRNG_PROVENANCE: QrngProvenance = {
  request_id: "sample-00000000-0000-0000-0000-000000000000",
  entropy_epoch: 0,
  timestamp: "1970-01-01T00:00:00Z",
  size: 32,
  endpoint: "https://api.qeaas.eu/v1/random/bytes",
  receipt: "qeaas1.SAMPLE_PLACEHOLDER_PAYLOAD.SAMPLE_PLACEHOLDER_SIGNATURE",
};

export async function loadRecordedProvenance(): Promise<QrngProvenance> {
  // Tier A/replay source: static JSON, no network, no API key (D-qrng-key).
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/replay/qrng-provenance.json`);
    if (!response.ok) {
      return SAMPLE_QRNG_PROVENANCE;
    }
    return (await response.json()) as QrngProvenance;
  } catch {
    return SAMPLE_QRNG_PROVENANCE;
  }
}
