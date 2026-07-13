const USE_CASES = [
  {
    title: "Ephemeral TLS/VPN keys",
    sentence:
      "QRNG-seeded entropy strengthens the randomness behind ephemeral session keys, supporting forward secrecy — it does not make the handshake protocol itself quantum-resistant.",
  },
  {
    title: "WireGuard ephemeral keys",
    sentence:
      "The same QRNG→DRBG entropy chain could seed WireGuard's ephemeral X25519 keypairs; this demo shows the entropy path with ML-KEM, not a WireGuard integration.",
  },
  {
    title: "SDN control-plane seeding / moving-target defence",
    sentence:
      "Centralized quantum entropy can seed the randomized re-keying or address/path rotation SDN controllers use for moving-target defence — again, entropy quality, not a new protocol.",
  },
  {
    title: "ECMP hash salt",
    sentence:
      "A quantum-seeded random salt for ECMP hashing reduces predictable flow-collision patterns across load-balanced paths — it improves salt unpredictability, not the hashing algorithm.",
  },
  {
    title: "IoT seed distribution",
    sentence:
      "Central quantum entropy, distributed to weak-RNG edge devices via API-key tiers, upgrades the entropy those devices seed their own local RNGs with — the devices still do the RNG work.",
  },
];

export default function NetworkingUseCases() {
  return (
    <section className="mx-auto w-full max-w-2xl px-4 py-12">
      <h2 className="glow mb-4 text-2xl font-semibold text-heading">
        Where this maps to networking
      </h2>
      <p className="mb-6 text-text/90">
        Honest framing: QRNG supplies entropy; ML-KEM supplies the quantum
        resistance. Five places that entropy plugs into networking —
        one sentence each, full write-up in{" "}
        <code>shared/docs/networking-demo.md</code>.
      </p>
      <div className="flex flex-col gap-4">
        {USE_CASES.map((useCase) => (
          <div key={useCase.title} className="panel p-4">
            <p className="mb-1 text-sm font-semibold text-heading">
              {useCase.title}
            </p>
            <p className="text-sm text-text/80">{useCase.sentence}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
