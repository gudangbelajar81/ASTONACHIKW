"use client";

import Link from "next/link";

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div>
        <h2>AstroCycle</h2>
        <nav>
          <Link href="/dashboard" className="nav-link active">
            Dasbor
          </Link>
          <Link href="/login" className="nav-link">
            Akun
          </Link>
          <Link href="/" className="nav-link">
            Beranda
          </Link>
        </nav>
      </div>
    </aside>
  );
}
