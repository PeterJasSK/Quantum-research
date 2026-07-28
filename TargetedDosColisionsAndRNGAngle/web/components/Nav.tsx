import Link from "next/link";

/** Sticky top brand bar. The whole load-balancing + collision-attack demo lives
 * on one page (`/`), so this reads as a product header rather than a router. */
export default function Nav() {
  return (
    <header className="sticky top-0 z-20 border-b border-(--color-border) bg-[color-mix(in_srgb,var(--color-bg)_78%,transparent)] backdrop-blur-xl">
      <nav className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-3">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="lamp lamp-green" aria-hidden />
          <span className="text-base font-bold tracking-tight text-(--color-heading)">
            QEaaS<span className="text-(--color-accent)">·</span>ECMP
          </span>
        </Link>
        <div className="flex items-center gap-4">
          <span className="hidden text-xs text-(--color-text) opacity-70 md:inline">
            Live ECMP load-balancing &amp; collision-DoS lab
          </span>
          <a
            href="https://qeaas.eu"
            target="_blank"
            rel="noopener noreferrer"
            className="pill px-4 py-1.5 text-xs font-semibold"
          >
            qeaas.eu ↗
          </a>
        </div>
      </nav>
    </header>
  );
}
