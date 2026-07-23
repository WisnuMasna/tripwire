import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tripwire — live honeypot attack feed",
  description:
    "A real internet-facing honeypot. Every attacker session is enriched with threat intel and summarised by Claude.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
