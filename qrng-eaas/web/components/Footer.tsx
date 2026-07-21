import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-border/60 px-4 py-8 text-center text-xs text-text/60 sm:text-sm">
      <nav className="flex flex-wrap items-center justify-center gap-4">
        <Link href="/agents" className="hover:text-accent">
          Agent integration
        </Link>
        <Link href="/llms.txt" className="hover:text-accent">
          llms.txt
        </Link>
      </nav>
      <p className="mt-2 text-text/40">&copy; 2026 Peter Jas</p>
    </footer>
  );
}
