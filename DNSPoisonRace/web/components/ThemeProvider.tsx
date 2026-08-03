"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="data-theme"
      themes={["light", "dark"]}
      defaultTheme="system"
      enableSystem
      storageKey="dns-poison-theme"
    >
      {children}
    </NextThemesProvider>
  );
}
