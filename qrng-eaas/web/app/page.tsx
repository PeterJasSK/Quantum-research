import Link from "next/link";
import WhatIsQrng from "@/components/sections/WhatIsQrng";
import PipelineDiagram from "@/components/sections/PipelineDiagram";
import ApiUsage from "@/components/sections/ApiUsage";
import VerifyReceipt from "@/components/sections/VerifyReceipt";
import CryptoFraming from "@/components/sections/CryptoFraming";

export default function Home() {
  return (
    <>
      <section
        id="top"
        className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-4 py-16 text-center sm:py-20"
      >
        <span className="glow text-xs uppercase tracking-[0.2em] text-accent sm:text-sm sm:tracking-[0.3em]">
          Q-EaaS
        </span>
        <h1 className="glow text-3xl font-bold tracking-tight text-heading sm:text-4xl md:text-5xl">
          Quantum random number generator
        </h1>
        <p className="max-w-xl text-sm text-text/90 sm:text-base">
          Quantum-seeded randomness, seeds, and post-quantum key material —
          with a live dice player you can roll right now.
        </p>
        <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
          <Link
            href="/dice"
            className="pill h-14 w-full px-8 text-lg font-semibold sm:w-auto"
          >
            Play the dice
          </Link>
          <a
            href="#overview"
            className="flex h-14 w-full items-center justify-center rounded-full border border-border px-8 text-text/90 hover:border-accent sm:w-auto"
          >
            Discover more
          </a>
        </div>
      </section>

      <div id="overview">
        <WhatIsQrng />
      </div>
      <div id="pipeline">
        <PipelineDiagram />
      </div>
      <div id="api">
        <ApiUsage />
      </div>
      <VerifyReceipt />
      <CryptoFraming />
    </>
  );
}
