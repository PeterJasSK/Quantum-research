import type { Metadata, Viewport } from "next";
import Script from "next/script";
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
  title: "QEaaS · quantum entropy for the network fabric",
  description:
    "Live k=6 fat-tree lab: QEaaS serves per-switch quantum salts that spread ECMP traffic, scatter a precision collision attacker, and ship a signed provenance receipt for every draw — auditable randomness as a service.",
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
        {/* Cloudflare Web Analytics */}
        <Script
          id="cloudflare-analytics"
          strategy="afterInteractive"
          src="https://static.cloudflareinsights.com/beacon.min.js"
          data-cf-beacon='{"token": "d872bd63e0824e0b9d54782354a6d184"}'
        />
      </body>
    </html>
  );
}
