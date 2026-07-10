"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import HealthBadge from "@/components/HealthBadge";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/#pipeline", label: "How it works" },
  { href: "/#api", label: "API" },
  { href: "/dice", label: "Dice" },
];

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-bg-deep/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2" onClick={() => setMenuOpen(false)}>
          <Image src="/logo.png" alt="Q-EaaS logo" width={32} height={32} priority />
          <span className="glow text-lg font-semibold text-heading">Q-EaaS</span>
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm text-text/90 transition-colors hover:text-accent"
            >
              {link.label}
            </Link>
          ))}
          <HealthBadge />
        </nav>

        <div className="flex items-center gap-3 md:hidden">
          <HealthBadge />
          <button
            type="button"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
            className="flex h-11 w-11 items-center justify-center rounded-full text-2xl text-text"
          >
            {menuOpen ? "✕" : "☰"}
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="fixed inset-0 top-16 z-40 flex flex-col items-center gap-8 bg-bg-deep/95 pt-12 backdrop-blur md:hidden">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setMenuOpen(false)}
              className="text-xl text-text hover:text-accent"
            >
              {link.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}
