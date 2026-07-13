"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="data-theme"
      themes={["light", "dark", "quantum"]}
      defaultTheme="system"
      enableSystem
      storageKey="qeaas-theme"
    >
      {children}
    </NextThemesProvider>
  );
}
