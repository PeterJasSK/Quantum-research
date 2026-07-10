export default function WhatIsQrng() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-16">
      <h2 className="glow mb-4 text-2xl font-semibold text-heading">
        What is a QRNG?
      </h2>
      <p className="mb-4 text-text/90">
        A quantum random number generator measures a genuinely probabilistic
        quantum process — here, superposition and measurement on real quantum
        hardware (IBM Quantum / Amazon Braket) — to produce bits that are
        unbiased by construction, not merely hard to predict.
      </p>
      <p className="text-text/90">
        Those raw quantum bits never leave this service directly. Instead they
        periodically reseed a standards-based DRBG (HMAC-DRBG, SP 800-90A),
        which stretches a finite quantum sample into effectively unlimited,
        cryptographically strong output — the seeds, dice rolls, and key
        material every endpoint on this site serves.
      </p>
    </section>
  );
}
