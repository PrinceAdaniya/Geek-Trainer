import type { Metadata, Viewport } from "next";
import { Anton, Inter } from "next/font/google";
import "./globals.css";
import { SessionProvider } from "@/lib/session";
import { AccountMenu, MobileTabBar, Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import { Logo } from "@/components/brand";
import { GYM } from "@/lib/gym";

const display = Anton({ weight: "400", subsets: ["latin"], variable: "--font-display", display: "swap" });
const body = Inter({ subsets: ["latin"], variable: "--font-body", display: "swap" });

export const metadata: Metadata = {
  // Set SITE_URL to the public address in production so share previews
  // resolve the hero image.
  metadataBase: new URL(process.env.SITE_URL ?? "http://localhost:3000"),
  title: {
    default: `${GYM.name} — ${GYM.tagline}`,
    template: `%s · ${GYM.name}`,
  },
  description: GYM.description,
  applicationName: GYM.name,
  openGraph: {
    title: GYM.name,
    description: `${GYM.offer.headline}. ${GYM.tagline}`,
    type: "website",
    images: ["/gym/hero.jpg"],
  },
  icons: {
    icon: [
      {
        url:
          "data:image/svg+xml," +
          encodeURIComponent(
            `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
               <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
                 <stop offset="0" stop-color="#ff4d8d"/><stop offset=".55" stop-color="#ff8a3d"/><stop offset="1" stop-color="#ffd23f"/>
               </linearGradient></defs>
               <rect width="32" height="32" rx="9" fill="url(#g)"/>
               <path d="M6.5 12h3v8h-3zM22.5 12h3v8h-3zM10.5 14.5h11v3h-11z" fill="#0e0b1f"/>
             </svg>`,
          ),
        type: "image/svg+xml",
      },
    ],
  },
};

export const viewport: Viewport = {
  themeColor: "#0e0b1f",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body className="min-h-dvh font-sans antialiased">
        <SessionProvider>
          <div className="relative z-[1] flex min-h-dvh w-full flex-col">
            <header className="sticky top-0 z-20 border-b border-surface-edge/70 bg-surface/80 backdrop-blur-md">
              <div className="mx-auto flex w-full max-w-[1400px] items-center justify-between gap-3 px-4 py-3 sm:px-6">
                <Logo />
                <div className="flex items-center gap-1">
                  <Nav />
                  <AccountMenu />
                </div>
              </div>
            </header>
            <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 pb-24 sm:px-6 md:pb-16">
              {children}
            </main>
            <Footer />
            <MobileTabBar />
          </div>
        </SessionProvider>
      </body>
    </html>
  );
}
