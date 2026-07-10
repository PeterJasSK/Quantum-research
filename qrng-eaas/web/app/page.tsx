import Link from "next/link";
import WhatIsQrng from "@/components/sections/WhatIsQrng";
import PipelineDiagram from "@/components/sections/PipelineDiagram";
import ApiUsage from "@/components/sections/ApiUsage";
import CryptoFraming from "@/components/sections/CryptoFraming";

export default function Home() {
  return (
    <>
      <section
        id="top"
        className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-4 py-20 text-center"
      >
        <span className="glow text-sm uppercase tracking-widest text-accent">
          Q-EaaS
        </span>
        <h1 className="glow text-3xl font-bold text-heading md:text-5xl">
          Quantum random number generator
        </h1>
        <p className="max-w-xl text-text/90">
          Quantum-seeded randomness, seeds, and post-quantum key material —
          with a live dice player you can roll right now.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Link href="/dice" className="pill h-14 px-8 text-lg font-semibold">
            Play the dice
          </Link>
          <a
            href="#overview"
            className="flex h-14 items-center justify-center rounded-full border border-border px-8 text-text/90 hover:border-accent"
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
      <CryptoFraming />
    </>
  );
}
