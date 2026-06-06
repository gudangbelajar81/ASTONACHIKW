"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Sidebar from "../../components/Sidebar";
import {
  ApiKeyEntry,
  ApiProviderConfig,
  DEFAULT_API_PROVIDERS,
  DEFAULT_MARKET_PROVIDERS,
  MarketProviderConfig,
  maskKey,
  readApiProviders,
  readMarketProviders,
  writeApiProviders,
  writeMarketProviders,
} from "../../lib/apiKeys";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "https://astonachikw-production.up.railway.app";

function createKeyEntry(rawKey: string): ApiKeyEntry {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    label: "Belum diberi label",
    key: rawKey.trim(),
    status: "unknown",
  };
}

export default function SettingsPage() {
  const [section, setSection] = useState<"ai" | "market">("ai");
  const [providers, setProviders] = useState<ApiProviderConfig[]>(DEFAULT_API_PROVIDERS);
  const [marketProviders, setMarketProviders] = useState<MarketProviderConfig[]>(DEFAULT_MARKET_PROVIDERS);
  const [activeProviderId, setActiveProviderId] = useState(DEFAULT_API_PROVIDERS[0].id);
  const [rawKeys, setRawKeys] = useState("");
  const [editingKeyId, setEditingKeyId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState("");
  const [checkingKeyId, setCheckingKeyId] = useState<string | null>(null);

  useEffect(() => {
    setProviders(readApiProviders());
    setMarketProviders(readMarketProviders());
  }, []);

  function saveProviders(nextProviders: ApiProviderConfig[]) {
    setProviders(nextProviders);
    writeApiProviders(nextProviders);
  }

  function saveMarketProviders(nextProviders: MarketProviderConfig[]) {
    setMarketProviders(nextProviders);
    writeMarketProviders(nextProviders);
  }

  const activeProvider = useMemo(
    () => providers.find((provider) => provider.id === activeProviderId) ?? providers[0],
    [providers, activeProviderId]
  );

  function updateActiveProvider(updater: (provider: ApiProviderConfig) => ApiProviderConfig) {
    saveProviders(providers.map((provider) => (provider.id === activeProvider.id ? updater(provider) : provider)));
  }

  function handleAddKeys(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextKeys = rawKeys
      .split(/\r?\n|,/)
      .map((key) => key.trim())
      .filter(Boolean)
      .filter((key, index, allKeys) => allKeys.indexOf(key) === index)
      .filter((key) => !activeProvider.keys.some((entry) => entry.key === key));

    if (!nextKeys.length) return;

    updateActiveProvider((provider) => ({
      ...provider,
      keys: [...provider.keys, ...nextKeys.map(createKeyEntry)],
    }));
    setRawKeys("");
  }

  function updateKey(keyId: string, updater: (entry: ApiKeyEntry) => ApiKeyEntry) {
    updateActiveProvider((provider) => ({
      ...provider,
      keys: provider.keys.map((entry) => (entry.id === keyId ? updater(entry) : entry)),
    }));
  }

  function removeKey(keyId: string) {
    updateActiveProvider((provider) => ({
      ...provider,
      keys: provider.keys.filter((entry) => entry.id !== keyId),
    }));
  }

  async function checkKey(entry: ApiKeyEntry) {
    setCheckingKeyId(entry.id);
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyst/test-key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: activeProvider.id,
          api_key: entry.key,
          model: activeProvider.model,
        }),
      });
      const result = await response.json();
      updateKey(entry.id, (current) => ({
        ...current,
        status: result.status === "live" ? "live" : "dead",
        lastChecked: new Date().toISOString(),
      }));
    } catch {
      updateKey(entry.id, (current) => ({
        ...current,
        status: "dead",
        lastChecked: new Date().toISOString(),
      }));
    } finally {
      setCheckingKeyId(null);
    }
  }

  async function checkMarketProvider(provider: MarketProviderConfig) {
    const nextStatus = provider.endpoint.trim() && provider.apiKey.trim() ? "live" : "dead";
    saveMarketProviders(
      marketProviders.map((item) =>
        item.id === provider.id
          ? { ...item, status: nextStatus, lastChecked: new Date().toISOString() }
          : item
      )
    );
  }

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="settings-header">
          <p className="dashboard-eyebrow">Settings</p>
          <h1>Pusat API</h1>
          <p>Kelola AI key dan provider data IDX/Bandarmology milik pengguna.</p>
        </div>

        <div className="settings-section-tabs">
          <button className={section === "ai" ? "active" : ""} type="button" onClick={() => setSection("ai")}>
            Pusat AI
          </button>
          <button className={section === "market" ? "active" : ""} type="button" onClick={() => setSection("market")}>
            Pusat Data IDX
          </button>
        </div>

        {section === "ai" ? (
          <div className="settings-layout">
          <aside className="settings-tabs">
            {providers.map((provider) => (
              <button
                key={provider.id}
                className={provider.id === activeProvider.id ? "active" : ""}
                type="button"
                onClick={() => setActiveProviderId(provider.id)}
              >
                <span>{provider.name}</span>
                <strong>{provider.keys.length} key</strong>
              </button>
            ))}
          </aside>

          <section className="api-center">
            <div className="api-center__topline">
              <div>
                <h2>{activeProvider.name} Keys</h2>
                <p>{activeProvider.keys.length} key tersimpan di browser pengguna ini.</p>
              </div>
              <label>
                Model
                <input
                  value={activeProvider.model}
                  onChange={(event) =>
                    updateActiveProvider((provider) => ({ ...provider, model: event.target.value }))
                  }
                />
              </label>
            </div>

            <form className="api-key-box" onSubmit={handleAddKeys}>
              <textarea
                value={rawKeys}
                onChange={(event) => setRawKeys(event.target.value)}
                placeholder={`Tempel ${activeProvider.name} API key di sini. Bisa banyak key, satu baris satu key.`}
              />
              <button type="submit">Tambah Key</button>
            </form>

            <div className="api-key-list">
              {activeProvider.keys.length ? (
                activeProvider.keys.map((entry) => (
                  <article className="api-key-row" key={entry.id}>
                    <div className={`api-key-dot api-key-dot--${entry.status}`} />
                    <div className="api-key-row__main">
                      <strong>{entry.label}</strong>
                      <span>{maskKey(entry.key)}</span>
                    </div>
                    <span className={`api-status api-status--${entry.status}`}>
                      {entry.status === "live" ? "LIVE" : entry.status === "dead" ? "DEAD" : "BELUM CEK"}
                    </span>
                    <button type="button" onClick={() => checkKey(entry)} disabled={checkingKeyId === entry.id}>
                      {checkingKeyId === entry.id ? "Cek..." : "Cek"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingKeyId(entry.id);
                        setEditingLabel(entry.label);
                      }}
                    >
                      Edit
                    </button>
                    <button type="button" onClick={() => removeKey(entry.id)}>
                      Hapus
                    </button>
                  </article>
                ))
              ) : (
                <div className="api-empty">Belum ada key untuk provider ini.</div>
              )}
            </div>

            {editingKeyId ? (
              <form
                className="api-edit-panel"
                onSubmit={(event) => {
                  event.preventDefault();
                  updateKey(editingKeyId, (entry) => ({ ...entry, label: editingLabel.trim() || entry.label }));
                  setEditingKeyId(null);
                  setEditingLabel("");
                }}
              >
                <label>
                  Edit Label
                  <input value={editingLabel} onChange={(event) => setEditingLabel(event.target.value)} />
                </label>
                <button type="submit">Simpan</button>
                <button type="button" onClick={() => setEditingKeyId(null)}>
                  Batal
                </button>
              </form>
            ) : null}
          </section>
          </div>
        ) : (
          <section className="api-center">
            <div className="api-center__topline">
              <div>
                <h2>Data Provider Bandarmology IDX</h2>
                <p>Provider ini disimpan di browser pengguna dan bisa dipakai untuk broker summary, foreign flow, dan order book saat API tersedia.</p>
              </div>
            </div>

            <div className="market-provider-list">
              {marketProviders.map((provider) => (
                <article className="market-provider-card" key={provider.id}>
                  <div className="market-provider-card__topline">
                    <div>
                      <h3>{provider.name}</h3>
                      <p>{provider.notes}</p>
                    </div>
                    <span className={`api-status api-status--${provider.status}`}>
                      {provider.status === "live" ? "LIVE" : provider.status === "dead" ? "DEAD" : "BELUM CEK"}
                    </span>
                  </div>

                  <label>
                    Endpoint API
                    <input
                      value={provider.endpoint}
                      placeholder="https://provider-api.com/idx/broker-summary"
                      onChange={(event) =>
                        saveMarketProviders(
                          marketProviders.map((item) =>
                            item.id === provider.id ? { ...item, endpoint: event.target.value, status: "unknown" } : item
                          )
                        )
                      }
                    />
                  </label>

                  <label>
                    API Key
                    <input
                      value={provider.apiKey}
                      placeholder="Masukkan API key provider data"
                      onChange={(event) =>
                        saveMarketProviders(
                          marketProviders.map((item) =>
                            item.id === provider.id ? { ...item, apiKey: event.target.value, status: "unknown" } : item
                          )
                        )
                      }
                    />
                  </label>

                  <div className="market-provider-actions">
                    <label className="provider-toggle">
                      <input
                        type="checkbox"
                        checked={provider.enabled}
                        onChange={(event) =>
                          saveMarketProviders(
                            marketProviders.map((item) =>
                              item.id === provider.id ? { ...item, enabled: event.target.checked } : item
                            )
                          )
                        }
                      />
                      Aktifkan provider
                    </label>
                    <button type="button" onClick={() => checkMarketProvider(provider)}>
                      Cek Status
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
