import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Inter, JetBrains_Mono } from "next/font/google";
import { Shell } from "@/components/shell";
import "./globals.css";

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

const code = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-code",
});

export const metadata: Metadata = {
  title: "Product OS",
  description: "A simple place for the product team",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#f5f5f7",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable} ${code.variable}`}>
      <head>
        <link rel="preload" as="image" href="/city/campus.webp" type="image/webp" />
        <link rel="preload" as="image" href="/city/mochi.png" type="image/png" />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="h-full font-sans antialiased">
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
