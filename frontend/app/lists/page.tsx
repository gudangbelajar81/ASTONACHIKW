"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Sidebar from "../../components/Sidebar";
import { SavedWatchlist, makeId, readSavedWatchlists, writeSavedWatchlists } from "../../lib/userData";

function normalizeTickers(raw: string) {
  return raw
    .split(",")
    .map((value) => value.trim().toUpperCase())
    .filter(Boolean);
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function SavedWatchlistsPage() {
  const [lists, setLists] = useState<SavedWatchlist[]>([]);
  const [name, setName] = useState("US Momentum");
  const [tickers, setTickers] = useState("AAPL,MSFT,NVDA,AMZN");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setLists(readSavedWatchlists());
  }, []);

  const editingList = useMemo(() => lists.find((item) => item.id === editingId) ?? null, [lists, editingId]);

  function persist(nextLists: SavedWatchlist[]) {
    setLists(nextLists);
    writeSavedWatchlists(nextLists);
  }

  function startEdit(list: SavedWatchlist) {
    setEditingId(list.id);
    setName(list.name);
    setTickers(list.tickers.join(", "));
  }

  function cancelEdit() {
    setEditingId(null);
    setName("US Momentum");
    setTickers("AAPL,MSFT,NVDA,AMZN");
  }

  function saveList(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextTickers = normalizeTickers(tickers);
    if (!nextTickers.length) return;

    const payload: SavedWatchlist = {
      id: editingId ?? makeId(),
      name: name.trim() || "Saved Watchlist",
      tickers: nextTickers,
      createdAt: editingList?.createdAt ?? new Date().toISOString(),
    };

    const nextLists = editingId
      ? lists.map((item) => (item.id === editingId ? payload : item))
      : [payload, ...lists];

    persist(nextLists);
    setMessage(editingId ? `Watchlist "${payload.name}" diperbarui.` : `Watchlist "${payload.name}" tersimpan.`);
    cancelEdit();
  }

  function removeList(id: string) {
    persist(lists.filter((item) => item.id !== id));
  }

  function openList(list: SavedWatchlist) {
    window.location.href = `/watchlist?tickers=${encodeURIComponent(list.tickers.join(","))}`;
  }

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">Watchlists</p>
            <h1>Saved Watchlists</h1>
            <p className="page-subtitle">Kelola daftar ticker yang tersimpan di browser pengguna ini.</p>
          </div>
          <Link href="/watchlist" className="action-button">
            Buka Scanner
          </Link>
        </div>

        {message ? <div className="dashboard-alert">{message}</div> : null}

        <form className="watchlist-savebar watchlist-savebar--stacked" onSubmit={saveList}>
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Nama watchlist" />
          <input value={tickers} onChange={(event) => setTickers(event.target.value)} placeholder="Ticker dipisah koma" />
          <button type="submit">{editingId ? "Perbarui" : "Simpan"}</button>
          {editingId ? (
            <button type="button" className="watchlist-savebar__ghost" onClick={cancelEdit}>
              Batal
            </button>
          ) : null}
        </form>

        <section className="saved-watchlist-grid">
          {lists.length ? (
            lists.map((list) => (
              <article className="saved-watchlist-card" key={list.id}>
                <div className="saved-watchlist-card__topline">
                  <div>
                    <h2>{list.name}</h2>
                    <p>{formatDate(list.createdAt)}</p>
                  </div>
                  <span>{list.tickers.length} ticker</span>
                </div>

                <div className="saved-watchlist-tags">
                  {list.tickers.map((ticker) => (
                    <span key={ticker}>{ticker}</span>
                  ))}
                </div>

                <div className="saved-watchlist-actions">
                  <button type="button" onClick={() => openList(list)}>
                    Pakai di Scanner
                  </button>
                  <button type="button" onClick={() => startEdit(list)}>
                    Edit
                  </button>
                  <button type="button" onClick={() => removeList(list.id)}>
                    Hapus
                  </button>
                </div>
              </article>
            ))
          ) : (
            <div className="api-empty">Belum ada watchlist tersimpan.</div>
          )}
        </section>
      </main>
    </div>
  );
}
