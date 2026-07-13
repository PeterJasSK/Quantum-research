"use client";

import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import { FiSun, FiMoon } from "react-icons/fi";
import { TbAtom2 } from "react-icons/tb";
import { isQuantumUnlocked, QUANTUM_UNLOCK_EVENT } from "@/lib/theme";

const SEGMENTS = [
  { value: "light", label: "Light theme", Icon: FiSun },
  { value: "dark", label: "Dark theme", Icon: FiMoon },
] as const;

const QUANTUM_SEGMENT = { value: "quantum", label: "Quantum theme", Icon: TbAtom2 } as const;

function subscribeToUnlock(callback: () => void) {
  window.addEventListener(QUANTUM_UNLOCK_EVENT, callback);
  return () => window.removeEventListener(QUANTUM_UNLOCK_EVENT, callback);
}

function useHasMounted(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const mounted = useHasMounted();
  const unlocked = useSyncExternalStore(subscribeToUnlock, isQuantumUnlocked, () => false);

  if (!mounted) {
    return <div className="h-10 w-20 rounded-full" aria-hidden="true" />;
  }

  const segments = unlocked ? [...SEGMENTS, QUANTUM_SEGMENT] : SEGMENTS;

  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      className="flex items-center gap-1 rounded-full border border-border/60 p-1"
    >
      {segments.map(({ value, label, Icon }) => (
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
              ? "bg-primary text-bg-deep"
              : "text-text/70 hover:text-accent"
          }`}
        >
          <Icon size={16} />
        </button>
      ))}
    </div>
  );
}
