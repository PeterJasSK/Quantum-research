"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { AnimatePresence, motion } from "framer-motion";
import HealthBadge from "@/components/HealthBadge";
import ThemeToggle from "@/components/ThemeToggle";
import { unlockQuantum, useSecretTap } from "@/lib/theme";

type NavChild = { href: string; label: string };

type NavLink = { href: string; label: string; children?: NavChild[] };

const NAV_LINKS: NavLink[] = [
  { href: "/", label: "Home" },
  { href: "/#pipeline", label: "How it works" },
  { href: "/#api", label: "API" },
  { href: "/dice", label: "Dice" },
  { href: "/demo", label: "Demo" },
];

function DesktopNavItem({ link }: { link: NavLink }) {
  const [open, setOpen] = useState(false);

  if (!link.children?.length) {
    return (
      <Link
        href={link.href}
        className="text-sm text-text/90 transition-colors hover:text-accent"
      >
        {link.label}
      </Link>
    );
  }

  return (
    <div className="relative" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="text-sm text-text/90 transition-colors hover:text-accent"
      >
        {link.label}
      </button>
      <div
        className={`absolute left-0 top-full w-56 pt-2 transition-all duration-300 ease-in-out ${
          open ? "translate-y-0 opacity-100" : "pointer-events-none -translate-y-2 opacity-0"
        }`}
      >
        <div className="rounded-xl border border-border/60 bg-surface p-2 shadow-xl">
          {link.children.map((child) => (
            <Link
              key={child.href}
              href={child.href}
              onClick={() => setOpen(false)}
              className="block rounded-lg px-3 py-2 text-sm text-text/90 transition-colors hover:bg-bg-deep hover:text-accent"
            >
              {child.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [showUnlockToast, setShowUnlockToast] = useState(false);
  const { setTheme } = useTheme();

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  const handleSecretTap = useSecretTap(5, 3000, () => {
    unlockQuantum();
    setTheme("quantum");
    setShowUnlockToast(true);
  });

  useEffect(() => {
    if (!showUnlockToast) return;
    const timeout = setTimeout(() => setShowUnlockToast(false), 2000);
    return () => clearTimeout(timeout);
  }, [showUnlockToast]);

  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-bg-deep">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4">
        <Link
          href="/"
          className="flex items-center gap-2"
          onClick={() => {
            setMenuOpen(false);
            handleSecretTap();
          }}
        >
          <span
            className="flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold"
            style={{ background: "var(--color-primary)", color: "var(--color-bg-deep)" }}
          >
            Q
          </span>
          <span className="glow text-lg font-semibold tracking-tight text-heading">
            Q&#8209;EaaS
          </span>
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          {NAV_LINKS.map((link) => (
            <DesktopNavItem key={link.href} link={link} />
          ))}
          <HealthBadge />
          <ThemeToggle />
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

      <div
        aria-hidden={!menuOpen}
        className={`fixed inset-0 top-16 z-40 flex flex-col items-center gap-8 overflow-y-auto bg-bg-deep pt-12 transition-all duration-500 ease-in-out md:hidden ${
          menuOpen
            ? "visible translate-y-0 opacity-100"
            : "invisible pointer-events-none -translate-y-full opacity-0"
        }`}
      >
        {NAV_LINKS.map((link) => (
          <div key={link.href} className="flex flex-col items-center gap-4">
            <Link
              href={link.href}
              onClick={() => setMenuOpen(false)}
              className="text-xl text-text hover:text-accent"
            >
              {link.label}
            </Link>
            {link.children?.map((child) => (
              <Link
                key={child.href}
                href={child.href}
                onClick={() => setMenuOpen(false)}
                className="text-base text-text/70 hover:text-accent"
              >
                {child.label}
              </Link>
            ))}
          </div>
        ))}
        <ThemeToggle />
      </div>

      <AnimatePresence>
        {showUnlockToast && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="pointer-events-none fixed left-1/2 top-20 z-[60] -translate-x-1/2 rounded-full border border-border/60 bg-bg-deep/95 px-4 py-2 text-sm text-heading backdrop-blur"
          >
            Quantum mode unlocked
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
