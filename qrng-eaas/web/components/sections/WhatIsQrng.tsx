export default function WhatIsQrng() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-12 sm:py-16">
       <div className="panel p-4 sm:p-6">
          <h2 className="glow mb-4 text-xl font-semibold text-heading sm:text-2xl">
            What is a QRNG?
          </h2>
          <p className="mb-4 text-sm text-text/90 sm:text-base">
            A quantum random number generator measures a genuinely probabilistic
            quantum process — here, superposition and measurement on real quantum
            hardware (IBM Quantum / Amazon Braket) — to produce bits that are
            unbiased by construction, not merely hard to predict.

            Those raw quantum bits never leave this service directly. Instead they
            periodically reseed a standards-based DRBG (HMAC-DRBG, SP 800-90A),
            which stretches a finite quantum sample into effectively unlimited,
            cryptographically strong output — served free over the API as seeds,
            dice rolls, and key material for anyone who needs it.
          </p>
      </div>
      <div className="panel p-4 sm:p-6">
        <h3 className="mb-3 text-lg font-semibold text-heading">
          How the pool actually gets used
        </h3>
        <p className="mb-3 text-sm text-text/90 sm:text-base">
          Every <strong>15 minutes</strong> (or sooner under sustained heavy
          traffic), the service pulls a fresh{" "}
          <strong>32 bytes</strong> of raw quantum entropy from the pool and
          uses it as the DRBG&rsquo;s <code>root_key</code>. That one 32-byte
          key is expanded by HMAC-DRBG into as much pseudorandom output as
          requests demand for that window — a monotonic counter mixed into
          each call keeps every response distinct, even under concurrent
          requests.
        </p>
        <p className="text-sm text-text/70">
          32 bytes in → unlimited served bytes out. Request volume alone
          can&rsquo;t drain the pool faster than wall-clock time; only the
          15-minute rotation (or a sustained flood of 100k+ requests inside 5
          minutes) consumes fresh entropy.
        </p>
      </div>

      <div className="panel mt-6 p-4 sm:p-6">
        <h3 className="mb-3 text-lg font-semibold text-heading">
          Is the output &ldquo;truly&rdquo; random?
        </h3>
        <p className="mb-3 text-sm text-text/90 sm:text-base">
          Only the 32-byte seed is <em>physically near perfectly </em> random. Everything
          downstream is <strong>cryptographically secure pseudorandom</strong>{" "}
          output — deterministic given the key, but computationally
          indistinguishable from random to anyone without it. This is the
          same architecture behind TLS, SSH, and most production crypto
          systems: a strong entropy seed feeding a standards DRBG, rather than
          streaming raw entropy bits over the wire per request.
        </p>
        <p className="text-sm text-text/70">
          Security rests on three things holding: the <code>root_key</code>{" "}
          stays encrypted at rest and is zeroized on rotation, the per-call
          counter never repeats, and the underlying quantum seed carries
          genuine entropy. All three hold here — which is what makes this
          setup suitable for real networking use (session keys, nonces, key
          material), not just as a demo.
        </p>
      </div>
    </section>
  );
}
