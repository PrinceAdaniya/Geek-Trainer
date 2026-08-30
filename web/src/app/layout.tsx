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
          <div className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col">
            <header className="flex items-center justify-between px-4 py-4">
              <Link href="/" className="text-[17px] font-semibold tracking-tight">
                Geek<span className="text-accent">-</span>Trainer
              </Link>
              <Nav />
            </header>
            <main className="flex-1 px-4 pb-24">{children}</main>
          </div>
        </SessionProvider>
      </body>
    </html>
  );
}
