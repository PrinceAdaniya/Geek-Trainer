import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";
import { SessionProvider } from "@/lib/session";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";

export const metadata: Metadata = {
  title: {
    default: "Geek-Trainer — training tracker",
    template: "%s · Geek-Trainer",
  },
  description:
    "An equipment-aware training tracker. Log every set, keep the streak alive, "
    + "watch the numbers move. Works offline, in the gym, on your phone.",
  applicationName: "Geek-Trainer",
  openGraph: {
    title: "Geek-Trainer",
    description:
      "Log every set. Keep the streak alive. Works offline, in the gym.",
    type: "website",
  },
  icons: {
    icon: [
      {
        url:
          "data:image/svg+xml," +
          encodeURIComponent(
            `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
               <rect width="32" height="32" rx="7" fill="#0b0c0f"/>
               <path d="M7 12h3v8H7zM22 12h3v8h-3zM11 15h10v2H11z" fill="#7dd3a0"/>
             </svg>`,
          ),
        type: "image/svg+xml",
      },
    ],
  },
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
            <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 pb-16 sm:px-6">
              {children}
            </main>
            <Footer />
          </div>
        </SessionProvider>
      </body>
    </html>
  );
}
