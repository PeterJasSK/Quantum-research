/** Site footer: attribution + the QEaaS link. */
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
          · DNS cache-poisoning entropy-race lab
        </span>
        <div className="flex items-center gap-4">
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
