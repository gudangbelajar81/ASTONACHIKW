import "../styles/globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AstroCycle",
  description: "Dasbor AstroCycle untuk prediksi siklus pasar.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className="dark">
      <body>{children}</body>
    </html>
  );
}
