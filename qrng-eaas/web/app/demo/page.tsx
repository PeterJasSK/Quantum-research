import type { Metadata } from "next";
import PageHero from "@/components/PageHero";
import KemHandshakeDemo from "@/components/KemHandshakeDemo";
import NetworkingUseCases from "@/components/sections/NetworkingUseCases";

export const metadata: Metadata = {
  title: "Networking demo — Q-EaaS",
};

export default function DemoPage() {
  return (
    <PageHero title="QRNG-seeded ML-KEM handshake">
      <p className="max-w-xl text-center text-sm text-text/90 sm:text-base">
        A Server holds a QRNG-seeded ML-KEM-768 keypair; a Client encapsulates
        to derive a shared secret; both derive an AES-GCM key and exchange one
        encrypted message — no page reload. The API key that drives this
        stays server-side; the browser only ever sees the same responses a
        keyed client would.
      </p>
      <KemHandshakeDemo />
      <NetworkingUseCases />
    </PageHero>
  );
}
