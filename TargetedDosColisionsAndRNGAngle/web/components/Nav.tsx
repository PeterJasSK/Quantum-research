import Link from "next/link";

/** Minimal cross-link, demo <-> /load-balancing (plan-8). `next/link` handles
 * `basePath` automatically for static export -- no manual prefixing needed
 * (unlike `fetch`, see lib/qeaas.ts). */
export default function Nav() {
  return (
    <nav className="mx-auto flex max-w-4xl gap-4 px-6 pt-4 text-sm">
      <Link href="/" className="text-(--color-text) hover:underline">
        Attack demo
      </Link>
      <Link href="/load-balancing" className="text-(--color-text) hover:underline">
        Load balancing
      </Link>
    </nav>
  );
}
