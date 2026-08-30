import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";
import { SessionProvider } from "@/lib/session";
import { Nav } from "@/components/nav";

export const metadata: Metadata = {
  title: "Geek-Trainer",
  description: "Plan your week, log every set, watch the numbers move.",
};

export const viewport: Viewport = {
  themeColor: "#101114",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-dvh antialiased">
        <SessionProvider>
          <div className="relative z-[1] flex min-h-dvh w-full flex-col">
            <header className="sticky top-0 z-20 flex items-center justify-between border-b border-surface-edge bg-surface/80 px-4 py-3 backdrop-blur-md sm:px-6">
              <Link href="/" className="flex items-baseline gap-2">
                <span className="font-mono text-[15px] font-semibold tracking-tight">
                  GEEK<span className="text-accent">/</span>TRAINER
                </span>
                <span className="label hidden sm:inline">v0.1</span>
              </Link>
              <Nav />
            </header>
            <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 pb-24 sm:px-6">{children}</main>
          </div>
        </SessionProvider>
      </body>
    </html>
  );
}
