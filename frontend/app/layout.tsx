import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Market Monitor",
  description: "Stock market breadth and momentum dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-gray-950 text-gray-100">
        <nav className="border-b border-gray-800 bg-gray-900 px-6 py-3 flex items-center justify-between">
          <span className="text-lg font-semibold text-white tracking-tight">
            Market Monitor
          </span>
          <span className="text-xs text-gray-500">US Equities</span>
        </nav>
        <main className="px-4 py-6 max-w-screen-2xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
