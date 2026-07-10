import type { Metadata, Viewport } from "next";
import { Orbitron } from "next/font/google";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import "./globals.css";

const orbitron = Orbitron({
  variable: "--font-orbitron",
  weight: ["400", "600", "700"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Q-EaaS — Quantum Entropy as a Service",
  description:
    "Quantum-seeded randomness, seeds & post-quantum key material — with a live dice player.",
  icons: "/logo.png",
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
    <html lang="en" className={`${orbitron.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
