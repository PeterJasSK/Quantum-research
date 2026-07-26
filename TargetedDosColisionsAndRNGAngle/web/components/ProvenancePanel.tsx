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
    <div className="panel flex flex-col gap-2 p-4">
      <h3 className="text-sm font-semibold text-(--color-heading)">
        QRNG entropy provenance -- attestable, not attack-mitigating
      </h3>
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
      <p className="text-xs italic text-(--color-text)">
        Honest label: this shows entropy is attestable/provably-sourced, not that QRNG stops the attack better
        than CSPRNG (Experiment 4's null result).
      </p>
    </div>
  );
}
