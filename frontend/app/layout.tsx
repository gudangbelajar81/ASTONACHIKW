import "../styles/globals.css";
import type { Metadata, Viewport } from "next";
import Script from "next/script";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: {
    default: "AstroCycle — Platform Cycle Forecasting Profesional",
    template: "%s | AstroCycle",
  },
  description:
    "AstroCycle adalah platform SaaS cycle forecasting dengan analisis teknikal multi-timeframe, deteksi gorengan IDX, dan AI market analyst berbasis astronomi.",
  manifest: "/manifest.json",
  keywords: ["trading", "cycle forecasting", "saham IDX", "technical analysis", "astro cycle"],
  authors: [{ name: "AstroCycle" }],
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "AstroCycle",
  },
  openGraph: {
    title: "AstroCycle — Platform Cycle Forecasting Profesional",
    description: "Analisis multi-timeframe, filter likuiditas IDX, dan AI analyst untuk trader profesional.",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#04070f",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className="dark" suppressHydrationWarning={true}>
      <head>
        {/* Google Fonts — Inter + JetBrains Mono */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
        {/* PWA */}
        <link rel="apple-touch-icon" href="/icon-192x192.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="mobile-web-app-capable" content="yes" />
      </head>
      <body suppressHydrationWarning={true}>
        <Providers>
          {children}
        </Providers>
        <Script id="register-sw" strategy="afterInteractive">
          {`
            if ('serviceWorker' in navigator) {
              window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js').catch(() => {
                  console.log('SW registration failed');
                });
              });
            }
          `}
        </Script>
      </body>
    </html>
  );
}
