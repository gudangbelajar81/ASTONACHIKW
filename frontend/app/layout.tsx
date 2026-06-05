import "../styles/globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AstroCycle",
  description: "AstroCycle SaaS dashboard for cycle forecasting.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
