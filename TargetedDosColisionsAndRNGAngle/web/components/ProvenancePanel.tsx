"use client";

import { useEffect, useState } from "react";
import { loadRecordedProvenance, type QrngProvenance } from "@/lib/qeaas";

export default function ProvenancePanel({ visible }: { visible: boolean }) {
  const [provenance, setProvenance] = useState<QrngProvenance | null>(null);

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    loadRecordedProvenance().then((record) => {
      if (!cancelled) setProvenance(record);
    });
    return () => {
      cancelled = true;
    };
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="panel card-hover flex flex-col gap-2 p-5">
      <span className="eyebrow">
        <span className="eyebrow-rule" />
        QEaaS
      </span>
      <h3 className="text-sm font-semibold text-(--color-heading)">
        Signed entropy provenance receipt
      </h3>
      <p className="text-xs text-(--color-text) opacity-80">
        Every QRNG salt served to the fabric arrives with this attestable receipt — proof of a real quantum source,
        which epoch it came from, and a verifiable signature. This is the deployable product: auditable randomness as
        a service.
      </p>
      {!provenance ? (
        <span className="text-xs text-(--color-text)">loading recorded provenance...</span>
      ) : (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-(--color-text)">
          <dt className="font-semibold">request_id</dt>
          <dd className="break-all">{provenance.request_id}</dd>
          <dt className="font-semibold">entropy_epoch</dt>
          <dd>{provenance.entropy_epoch}</dd>
          <dt className="font-semibold">timestamp</dt>
          <dd>{provenance.timestamp}</dd>
          <dt className="font-semibold">size</dt>
          <dd>{provenance.size} bytes</dd>
          <dt className="font-semibold">endpoint</dt>
          <dd className="break-all">{provenance.endpoint}</dd>
          <dt className="font-semibold">receipt</dt>
          <dd className="break-all font-(family-name:--font-mono)">{provenance.receipt}</dd>
        </dl>
      )}
      <p className="text-xs italic text-(--color-text) opacity-70">
        Footnote: a strong CSPRNG blunts this attack just as well; the signed receipt is what CSPRNG cannot give you.
      </p>
      <a
        href="https://qeaas.eu"
        target="_blank"
        rel="noopener noreferrer"
        className="mt-1 text-xs font-semibold text-(--color-accent) hover:underline"
      >
        Draw your own signed entropy at qeaas.eu ↗
      </a>
    </div>
  );
}
