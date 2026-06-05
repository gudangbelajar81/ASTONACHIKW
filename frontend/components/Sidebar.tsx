"use client";

import Link from "next/link";

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div>
        <h2>AstroCycle</h2>
        <nav>
          <Link href="/dashboard" className="nav-link active">
            Dashboard
          </Link>
          <Link href="/login" className="nav-link">
            Account
          </Link>
          <Link href="/" className="nav-link">
            Home
          </Link>
        </nav>
      </div>
    </aside>
  );
}
