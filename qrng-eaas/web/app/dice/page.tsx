import type { Metadata } from "next";
import PageHero from "@/components/PageHero";
import DicePlayer from "@/components/DicePlayer";

export const metadata: Metadata = {
  title: "Play Quantum Dice — Q-EaaS",
};

export default function DicePage() {
  return (
    <PageHero title="Play quantum dice" maxWidth="max-w-4xl">
      <p className="max-w-xl text-center text-sm text-text/90 sm:text-base">
        Every roll is sampled from the same quantum-seeded DRBG that powers
        the rest of this service — no page reload, no bias.
      </p>
      <DicePlayer />
    </PageHero>
  );
}
