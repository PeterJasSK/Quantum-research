import type { Metadata, Viewport } from "next";
import { Orbitron, Inter, JetBrains_Mono } from "next/font/google";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ThemeProvider from "@/components/ThemeProvider";
import "./globals.css";

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
  metadataBase: new URL("https://qrng.peterjas.sk"),
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
    url: "https://qrng.peterjas.sk",
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
        <ThemeProvider>
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
