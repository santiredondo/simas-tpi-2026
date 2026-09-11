import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ERP grupo21",
  description: "ERP con IA — TPI SIMAS 2026",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
