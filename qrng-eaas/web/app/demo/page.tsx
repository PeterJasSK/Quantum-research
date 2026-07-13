import type { Metadata } from "next";
import Link from "next/link";
import KemHandshakeDemo from "@/components/KemHandshakeDemo";
import NetworkingUseCases from "@/components/sections/NetworkingUseCases";

export const metadata: Metadata = {
  title: "Networking demo — Q-EaaS",
};

export default function DemoPage() {
  return (
    <section className="mx-auto flex max-w-3xl flex-col items-center gap-8 px-4 py-16">
      <Link href="/" className="self-start text-sm text-accent hover:underline">
        ← Back to overview
      </Link>
      <h1 className="glow text-3xl font-bold text-heading">
        QRNG-seeded ML-KEM handshake
      </h1>
      <p className="max-w-xl text-center text-text/90">
        A Server holds a QRNG-seeded ML-KEM-768 keypair; a Client encapsulates
        to derive a shared secret; both derive an AES-GCM key and exchange one
        encrypted message — no page reload. The API key that drives this
        stays server-side; the browser only ever sees the same responses a
        keyed client would.
      </p>
      <KemHandshakeDemo />
      <NetworkingUseCases />
    </section>
  );
}
