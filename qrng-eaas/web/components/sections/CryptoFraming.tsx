export default function CryptoFraming() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-16">
      <div className="panel p-6">
        <h2 className="glow mb-4 text-2xl font-semibold text-heading">
          Entropy, not quantum resistance
        </h2>
        <p className="mb-3 text-text/90">
          QRNG does <strong>not</strong> &ldquo;defeat quantum attackers.&rdquo;
          It supplies high-quality <em>entropy</em> that seeds a standards
          DRBG, which in turn seeds post-quantum algorithms (ML-KEM) and
          ephemeral session keys. The quantum part is the{" "}
          <strong>entropy source</strong>; the quantum{" "}
          <strong>resistance</strong> comes from ML-KEM.
        </p>
        <p className="text-sm text-text/70">
          The ML-KEM implementation used here (<code>kyber-py</code>) is
          educational and not constant-time — correct for this demo, not a
          production deployment. See the README for the production-grade
          alternative.
        </p>
      </div>
    </section>
  );
}
