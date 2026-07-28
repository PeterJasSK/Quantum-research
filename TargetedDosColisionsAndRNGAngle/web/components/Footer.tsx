import Link from "next/link";

/** Site footer: attribution + the agent/MCP integration link (kept out of the
 * header so the nav stays clean). */
export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-16 border-t border-(--color-border)">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-6 py-6 text-xs text-(--color-text) sm:flex-row">
        <span className="opacity-70">
          © {year}{" "}
          <a
            href="https://peterjas.sk"
            target="_blank"
            rel="noopener noreferrer"
            className="text-(--color-accent) hover:underline"
          >
            Peter Jaš
          </a>{" "}
          · ECMP salt-collision DoS lab
        </span>
        <div className="flex items-center gap-4">
          <Link href="/agents" className="text-(--color-accent) hover:underline">
            Agents &amp; MCP
          </Link>
          <a
            href="https://qeaas.eu"
            target="_blank"
            rel="noopener noreferrer"
            className="opacity-70 hover:opacity-100"
          >
            qeaas.eu ↗
          </a>
        </div>
      </div>
    </footer>
  );
}
