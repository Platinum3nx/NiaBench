import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "NiaBench",
  description: "Context retrieval benchmark for AI coding agents."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main>
          <nav className="nav">
            <Link href="/">Overview</Link>
            <Link href="/agent">Layer 2 Agent</Link>
            <Link href="/methodology">Methodology</Link>
          </nav>
          {children}
        </main>
      </body>
    </html>
  );
}
