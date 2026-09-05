import type { Metadata } from "next";
import "./globals.css";
import Navbar from "../components/Navbar";

export const metadata: Metadata = {
  title: "FORGE — Agents don't just run. They evolve.",
  description: "Autonomous agent engineering and empirical failure-driven evolution platform for Syndicate by Maximor.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0d1117] text-[#c9d1d9] flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-[#212631] py-6 text-center text-xs text-gray-500">
          FORGE — Syndicate by Maximor Track 1: Automated Agent Engineering • Powered by TensorMux
        </footer>
      </body>
    </html>
  );
}
