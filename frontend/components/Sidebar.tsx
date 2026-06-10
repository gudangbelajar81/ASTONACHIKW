"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import InstallPrompt from "./InstallPrompt";

const navLinks = [
  { href: "/dashboard",    label: "Dasbor",      icon: "📊", group: "main" },
  { href: "/performance",  label: "Performance",  icon: "📈", group: "main" },
  { href: "/watchlist",    label: "Watchlist",    icon: "⭐", group: "main" },
  { href: "/workflow",     label: "Workflow",     icon: "🔄", group: "main" },
  { href: "/opportunities",label: "Opportunity",  icon: "💡", group: "main" },
  { href: "/backtest",     label: "Backtest",     icon: "🧪", group: "analysis" },
  { href: "/dsi-radar",    label: "DSI Radar",    icon: "🎯", group: "analysis" },
  { href: "/lists",        label: "Lists",        icon: "📋", group: "analysis" },
  { href: "/ohlcv",        label: "OHLCV",        icon: "📉", group: "analysis" },
  { href: "/studio/image", label: "Studio",       icon: "🎨", group: "tools" },
  { href: "/alerts",       label: "Alerts",       icon: "🔔", group: "tools" },
  { href: "/portfolio",    label: "Portfolio",    icon: "💼", group: "tools" },
  { href: "/report",       label: "Report",       icon: "📄", group: "tools" },
  { href: "/explain",      label: "Explain",      icon: "❓", group: "support" },
  { href: "/admin",        label: "Admin",        icon: "⚙️", group: "support" },
  { href: "/settings",     label: "Settings",     icon: "🔧", group: "support" },
];

const groupLabels: Record<string, string> = {
  main:     "Utama",
  analysis: "Analisis",
  tools:    "Tools",
  support:  "Support",
};

const groups = ["main", "analysis", "tools", "support"];

export default function Sidebar() {
  const pathname = usePathname();
  const [isMobile, setIsMobile] = useState(false);
  const [isOpen, setIsOpen]     = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth <= 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  useEffect(() => { setIsOpen(false); }, [pathname]);

  const NavContent = () => (
    <>
      {/* ── Logo Header ── */}
      <div className="nav-header">
        <Link href="/" className="nav-logo">
          <span className="nav-logo-icon">🌙</span>
          <span className="nav-logo-text">AstroCycle</span>
        </Link>
        {isMobile && (
          <button
            className="nav-close"
            onClick={() => setIsOpen(false)}
            aria-label="Tutup menu"
          >
            ✕
          </button>
        )}
      </div>

      {/* ── Navigation Menu ── */}
      <nav className="nav-menu" aria-label="Navigasi utama">
        {groups.map((group) => {
          const links = navLinks.filter((l) => l.group === group);
          return (
            <div key={group} style={{ marginBottom: "4px" }}>
              {/* Group label */}
              <p style={{
                padding: "8px 14px 4px",
                fontSize: "0.65rem",
                fontWeight: 700,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--ag-text-muted)",
                margin: 0,
              }}>
                {groupLabels[group]}
              </p>
              {links.map((link) => {
                const isActive = pathname === link.href ||
                  (link.href !== "/" && pathname.startsWith(link.href));
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`nav-link${isActive ? " active" : ""}`}
                    title={link.label}
                    aria-current={isActive ? "page" : undefined}
                  >
                    <span className="nav-link-icon">{link.icon}</span>
                    <span className="nav-link-text">{link.label}</span>
                    {isActive && (
                      <span style={{
                        marginLeft: "auto",
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background: "var(--ag-text-accent)",
                        boxShadow: "0 0 6px var(--ag-text-accent)",
                        flexShrink: 0,
                      }} />
                    )}
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>

      {/* ── Footer ── */}
      <div className="nav-footer">
        {/* System status */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 12px",
          marginBottom: 8,
          borderRadius: "var(--ag-radius-md)",
          background: "rgba(16, 185, 129, 0.06)",
          border: "1px solid rgba(16, 185, 129, 0.15)",
        }}>
          <span style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: "#10b981",
            boxShadow: "0 0 6px #10b981",
            animation: "ag-pulse-glow 2s infinite",
            flexShrink: 0,
          }} />
          <span style={{ fontSize: "0.72rem", color: "#6ee7b7", fontWeight: 600 }}>
            System Online
          </span>
        </div>

        <Link href="/login" className="nav-link nav-link--account">
          <span className="nav-link-icon">👤</span>
          <span className="nav-link-text">Akun</span>
        </Link>
      </div>
    </>
  );

  /* ── Mobile Layout ── */
  if (isMobile) {
    return (
      <>
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

        {isOpen && (
          <>
            <div
              className="mobile-overlay"
              onClick={() => setIsOpen(false)}
              aria-hidden="true"
            />
            <aside className="mobile-sidebar sidebar">
              <NavContent />
            </aside>
          </>
        )}

        <InstallPrompt />
      </>
    );
  }

  /* ── Desktop Layout ── */
  return (
    <>
      <aside className="sidebar">
        <NavContent />
      </aside>
      <InstallPrompt />
    </>
  );
}
