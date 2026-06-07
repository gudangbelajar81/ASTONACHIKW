"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Sidebar() {
  const pathname = usePathname();

  const links = [
    { href: "/dashboard", label: "Dasbor" },
    { href: "/performance", label: "Performance" },
    { href: "/watchlist", label: "Watchlist" },
    { href: "/lists", label: "Saved Watchlists" },
    { href: "/ohlcv", label: "OHLCV Pro" },
    { href: "/alerts", label: "Alerts" },
    { href: "/portfolio", label: "Portfolio" },
    { href: "/report", label: "Report" },
    { href: "/explain", label: "Explain" },
    { href: "/admin", label: "Admin" },
    { href: "/login", label: "Akun" },
    { href: "/settings", label: "Settings" },
    { href: "/", label: "Beranda" },
  ];

  return (
    <aside className="sidebar">
      <div>
        <h2>AstroCycle</h2>
        <nav>
          {links.map((link) => (
            <Link key={link.href} href={link.href} className={`nav-link ${pathname === link.href ? "active" : ""}`}>
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  );
}
