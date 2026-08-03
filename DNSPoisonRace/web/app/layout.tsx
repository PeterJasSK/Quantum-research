import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import ThemeProvider from "@/components/ThemeProvider";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import { WEB_URL } from "@/lib/urls";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(WEB_URL),
  title: "DNS Poison Race · how many entropy bits stop a cache poisoner?",
  description:
    "Live client-side lab: watch an attacker's forged-answer flood race the authoritative reply into a resolver's cache. Drop the entropy slider off the cliff, flip on the SAD-DNS side-channel leak, and see a QRNG-backed signed provenance receipt -- the deployable product a strong CSPRNG cannot give you.",
  alternates: { canonical: "/" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full">
        <ThemeProvider>
          <Nav />
          <main>{children}</main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
