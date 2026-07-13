"use client";

import { useCallback, useRef } from "react";

export const QUANTUM_UNLOCK_KEY = "qeaas-quantum-unlocked";
export const QUANTUM_UNLOCK_EVENT = "qeaas-quantum-unlocked-change";

export function isQuantumUnlocked(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(QUANTUM_UNLOCK_KEY) === "1";
}

export function unlockQuantum(): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(QUANTUM_UNLOCK_KEY, "1");
  window.dispatchEvent(new Event(QUANTUM_UNLOCK_EVENT));
}

export function useSecretTap(count: number, windowMs: number, onTrigger: () => void) {
  const taps = useRef<number[]>([]);

  return useCallback(() => {
    const now = Date.now();
    taps.current = [...taps.current, now].filter((t) => now - t <= windowMs);
    if (taps.current.length >= count) {
      taps.current = [];
      onTrigger();
    }
  }, [count, windowMs, onTrigger]);
}
