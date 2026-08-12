import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GridPulse Intelligence",
  description:
    "Real-time electricity, weather, EV infrastructure, and data platform intelligence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
