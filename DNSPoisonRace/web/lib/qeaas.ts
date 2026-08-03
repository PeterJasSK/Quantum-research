// QRNG provenance display (epic §3.2, Appendix A.4). The static bundle only ever
// reads this pre-recorded JSON; the QEAAS_API_KEY never reaches the browser.
//
// Shape matches P5's qrng-provenance.json -- the receipt fields are NESTED under
// `detail` (unlike the twin's flat record):
//   { kind: "qrng", detail: { request_id, entropy_epoch, timestamp, receipt, endpoint } }
export interface QrngProvenance {
  kind: string;
  detail: {
    request_id: string;
    entropy_epoch: string | number;
    timestamp: string;
    receipt: string;
    endpoint: string;
  };
}

// SAMPLE placeholder -- a structurally-accurate stand-in for the demo UI. It is
// NOT a real Q-EaaS receipt. Rendered honestly (labelled a sample) whenever P5's
// recorded record is missing or has not yet frozen a real, .env-authenticated
// receipt. Never present this as a real attestation.
export const SAMPLE_QRNG_PROVENANCE: QrngProvenance = {
  kind: "qrng",
  detail: {
    request_id: "sample-placeholder",
    entropy_epoch: "0",
    timestamp: "1970-01-01T00:00:00Z",
    receipt: "",
    endpoint: "sample-placeholder",
  },
};

export async function loadRecordedProvenance(): Promise<QrngProvenance> {
  // Tier A/replay source: static JSON, no network, no API key.
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

// A recorded receipt whose detail values are all "sample-placeholder" (or an empty
// receipt) is the P5 placeholder -- render it as clearly-not-real.
export function isPlaceholderProvenance(p: QrngProvenance): boolean {
  return (
    p.detail.receipt.trim() === "" ||
    p.detail.request_id === "sample-placeholder" ||
    p.detail.endpoint === "sample-placeholder"
  );
}
