const STAGES = [
  { label: "Quantum bits", detail: "IBM Quantum / Braket measurement" },
  { label: "Encrypted pool", detail: "AES-256-GCM at rest" },
  { label: "HMAC-DRBG", detail: "root key + atomic counter" },
  { label: "Seeds · dice · ML-KEM keys", detail: "everything served here" },
];

export default function PipelineDiagram() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-16">
      <h2 className="glow mb-8 text-2xl font-semibold text-heading">
        The pipeline
      </h2>
      <div className="flex flex-col items-stretch gap-2 md:flex-row md:items-center md:gap-0">
        {STAGES.map((stage, index) => (
          <div key={stage.label} className="contents">
            <div className="panel w-full p-4 text-center md:flex-1">
              <p className="font-semibold text-heading">{stage.label}</p>
              <p className="mt-1 text-xs text-text/70">{stage.detail}</p>
            </div>
            {index < STAGES.length - 1 && (
              <span
                className="flex shrink-0 items-center justify-center py-1 text-accent md:px-3 md:py-0"
                aria-hidden
              >
                <span className="md:hidden">↓</span>
                <span className="hidden md:inline">→</span>
              </span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
