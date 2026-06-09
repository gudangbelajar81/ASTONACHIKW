"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import InstallPrompt from "./InstallPrompt";

const navLinks = [
  { href: "/dashboard", label: "Dasbor", icon: "📊" },
  { href: "/performance", label: "Performance", icon: "📈" },
  { href: "/watchlist", label: "Watchlist", icon: "⭐" },
  { href: "/workflow", label: "Workflow", icon: "🔄" },
  { href: "/opportunities", label: "Opportunity", icon: "💡" },
  { href: "/backtest", label: "Backtest", icon: "🧪" },
  { href: "/lists", label: "Lists", icon: "📋" },
  { href: "/ohlcv", label: "OHLCV", icon: "📉" },
  { href: "/studio/image", label: "Studio", icon: "🎨" },
  { href: "/alerts", label: "Alerts", icon: "🔔" },
  { href: "/portfolio", label: "Portfolio", icon: "💼" },
  { href: "/report", label: "Report", icon: "📄" },
  { href: "/explain", label: "Explain", icon: "❓" },
  { href: "/admin", label: "Admin", icon: "⚙️" },
  { href: "/settings", label: "Settings", icon: "🔧" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [isMobile, setIsMobile] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Close mobile menu when route changes
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  const NavContent = () => (
    <>
      <div className="nav-header">
        <Link href="/" className="nav-logo">
          <span className="nav-logo-icon">🌙</span>
          <span className="nav-logo-text">AstroCycle</span>
        </Link>
        {isMobile && (
          <button className="nav-close" onClick={() => setIsOpen(false)} aria-label="Tutup menu">
            ✕
          </button>
        )}
      </div>
      <nav className="nav-menu">
        {navLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`nav-link ${pathname === link.href ? "active" : ""}`}
            title={link.label}
          >
            <span className="nav-link-icon">{link.icon}</span>
            <span className="nav-link-text">{link.label}</span>
          </Link>
        ))}
      </nav>
      <div className="nav-footer">
        <Link href="/login" className="nav-link nav-link--account">
          <span className="nav-link-icon">👤</span>
          <span className="nav-link-text">Akun</span>
        </Link>
      </div>
    </>
  );

  if (isMobile) {
    return (
      <>
        {/* Mobile Top Bar */}
        <header className="mobile-header">
          <Link href="/" className="mobile-logo">
            <span>🌙</span>
            <span>AstroCycle</span>
          </Link>
          <button
            className="mobile-menu-btn"
            onClick={() => setIsOpen(true)}
            aria-label="Buka menu"
          >
            ☰
          </button>
        </header>

        {/* Mobile Menu Overlay */}
        {isOpen && (
          <>
            <div className="mobile-overlay" onClick={() => setIsOpen(false)} />
            <aside className="mobile-sidebar">
              <NavContent />
            </aside>
          </>
        )}

        {/* Install Prompt for Mobile */}
        <InstallPrompt />
      </>
    );
  }

  return (
    <>
      <aside className="sidebar">
        <NavContent />
      </aside>
      <InstallPrompt />
    </>
  );
}
