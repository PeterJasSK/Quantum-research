import type { Metadata, Viewport } from "next";
import { Orbitron, Inter, JetBrains_Mono } from "next/font/google";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ThemeProvider from "@/components/ThemeProvider";
import StructuredData from "@/components/StructuredData";
import { WEB_URL } from "@/lib/urls";
import "./globals.css";

// EPIC 13 AC-9: site-wide WebSite + Organization structured data.
const SITE_JSON_LD: Record<string, unknown>[] = [
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "Q-EaaS — Quantum Entropy as a Service",
    url: WEB_URL,
    description:
      "Quantum-seeded randomness, seeds & post-quantum key material — with a live dice player.",
  },
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "Q-EaaS",
    url: WEB_URL,
    logo: `${WEB_URL}/logo.png`,
  },
];

const orbitron = Orbitron({
  variable: "--font-orbitron",
  weight: ["400", "600", "700"],
  subsets: ["latin"],
});

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
  title: {
    default: "Q-EaaS — Quantum Entropy as a Service",
    template: "%s — Q-EaaS",
  },
  description:
    "Quantum-seeded randomness, seeds & post-quantum key material — with a live dice player.",
  keywords: [
    "quantum random number generator",
    "QRNG",
    "quantum entropy",
    "entropy as a service",
    "post-quantum key material",
    "true random numbers",
    "quantum computing",
  ],
  authors: [{ name: "Peter Jas" }],
  creator: "Peter Jas",
  icons: "/logo.png",
  alternates: {
    canonical: "/",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    url: WEB_URL,
    siteName: "Q-EaaS",
    title: "Q-EaaS — Quantum Entropy as a Service",
    description:
      "Quantum-seeded randomness, seeds & post-quantum key material — with a live dice player.",
    locale: "en_US",
    images: [{ url: "/logo.png", width: 512, height: 512, alt: "Q-EaaS" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Q-EaaS — Quantum Entropy as a Service",
    description:
      "Quantum-seeded randomness, seeds & post-quantum key material — with a live dice player.",
    images: ["/logo.png"],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${orbitron.variable} ${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col">
        <StructuredData data={SITE_JSON_LD} />
        <ThemeProvider>
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
