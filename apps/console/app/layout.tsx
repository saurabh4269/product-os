import type { Metadata } from "next";
import { IBM_Plex_Mono, Inter } from "next/font/google";
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

export const metadata: Metadata = {
  title: "Product OS",
  description: "A simple place for the product team",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body className="h-full font-sans antialiased">
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
