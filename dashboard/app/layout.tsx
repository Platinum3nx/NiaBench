import { Inter, Roboto_Mono } from "next/font/google";
import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const robotoMono = Roboto_Mono({ subsets: ["latin"], variable: "--font-roboto-mono" });

export const metadata: Metadata = {
  title: "NiaBench",
  description: "Context retrieval benchmark for AI coding agents."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${robotoMono.variable}`}>
      <body>
        <main>
          <nav className="nav">
            <Link href="/">Overview</Link>
            <Link href="/methodology">Methodology</Link>
          </nav>
          {children}
        </main>
      </body>
    </html>
  );
}
