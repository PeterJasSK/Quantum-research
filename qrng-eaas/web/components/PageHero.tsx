import Link from "next/link";
import type { ReactNode } from "react";

export default function PageHero({
  title,
  children,
  maxWidth = "max-w-3xl",
}: {
  title: string;
  children: ReactNode;
  maxWidth?: string;
}) {
  return (
    <section
      className={`mx-auto flex ${maxWidth} flex-col items-center gap-6 px-4 py-12 sm:gap-8 sm:py-16`}
    >
      <Link
        href="/"
        className="self-start text-sm text-accent hover:underline"
      >
        ← Back to overview
      </Link>
      <h1 className="glow text-2xl font-bold tracking-tight text-heading sm:text-3xl">
        {title}
      </h1>
      {children}
    </section>
  );
}
