import type { Metadata } from "next";
import Link from "next/link";
import DicePlayer from "@/components/DicePlayer";

export const metadata: Metadata = {
  title: "Play Quantum Dice — Q-EaaS",
};

export default function DicePage() {
  return (
    <section className="mx-auto flex max-w-3xl flex-col items-center gap-8 px-4 py-16">
      <Link href="/" className="self-start text-sm text-accent hover:underline">
        ← Back to overview
      </Link>
      <h1 className="glow text-3xl font-bold text-heading">
        Play quantum dice
      </h1>
      <p className="max-w-xl text-center text-text/90">
        Every roll is sampled from the same quantum-seeded DRBG that powers
        the rest of this service — no page reload, no bias.
      </p>
      <DicePlayer />
    </section>
  );
}
