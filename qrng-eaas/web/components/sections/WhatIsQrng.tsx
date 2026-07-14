export default function WhatIsQrng() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-12 sm:py-16">
      <h2 className="glow mb-4 text-xl font-semibold text-heading sm:text-2xl">
        What is a QRNG?
      </h2>
      <p className="mb-4 text-sm text-text/90 sm:text-base">
        A quantum random number generator measures a genuinely probabilistic
        quantum process — here, superposition and measurement on real quantum
        hardware (IBM Quantum / Amazon Braket) — to produce bits that are
        unbiased by construction, not merely hard to predict.
      </p>
      <p className="text-sm text-text/90 sm:text-base">
        Those raw quantum bits never leave this service directly. Instead they
        periodically reseed a standards-based DRBG (HMAC-DRBG, SP 800-90A),
        which stretches a finite quantum sample into effectively unlimited,
        cryptographically strong output — served free over the API as seeds,
        dice rolls, and key material for anyone who needs it.
      </p>
    </section>
  );
}
