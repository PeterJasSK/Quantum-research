"use client";

import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";

/** Light/dark segmented toggle. Mirrors the qrng-eaas/web ThemeToggle look
 * (pill of icon buttons) but ships only the two themes this site defines, and
 * uses inline SVG so it needs no icon dependency. */
const SEGMENTS = [
  { value: "light", label: "Light theme" },
  { value: "dark", label: "Dark theme" },
] as const;

function useHasMounted(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const mounted = useHasMounted();

  if (!mounted) {
    return <div className="h-10 w-[4.5rem] rounded-full" aria-hidden="true" />;
  }

  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      className="flex items-center gap-1 rounded-full border border-(--color-border) p-1"
    >
      {SEGMENTS.map(({ value, label }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={theme === value}
          aria-label={label}
          title={label}
          onClick={() => setTheme(value)}
          className={`flex h-8 w-8 items-center justify-center rounded-full transition-colors ${
            theme === value
              ? "bg-(--color-primary) text-(--color-bg)"
              : "text-(--color-text)/70 hover:text-(--color-accent)"
          }`}
        >
          {value === "light" ? <SunIcon /> : <MoonIcon />}
        </button>
      ))}
    </div>
  );
}
