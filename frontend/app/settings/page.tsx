"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Sidebar from "../../components/Sidebar";
import {
  ApiKeyEntry,
  ApiProviderConfig,
  DEFAULT_API_PROVIDERS,
  maskKey,
  readApiProviders,
  writeApiProviders,
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
  const [providers, setProviders] = useState<ApiProviderConfig[]>(DEFAULT_API_PROVIDERS);
  const [activeProviderId, setActiveProviderId] = useState(DEFAULT_API_PROVIDERS[0].id);
  const [rawKeys, setRawKeys] = useState("");
  const [editingKeyId, setEditingKeyId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState("");
  const [checkingKeyId, setCheckingKeyId] = useState<string | null>(null);

  useEffect(() => {
    setProviders(readApiProviders());
  }, []);

  function saveProviders(nextProviders: ApiProviderConfig[]) {
    setProviders(nextProviders);
    writeApiProviders(nextProviders);
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

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="settings-header">
          <p className="dashboard-eyebrow">Settings</p>
          <h1>Pusat API</h1>
          <p>Kelola key AI pribadi pengguna untuk Gemini, DeepSeek, Grok/xAI, dan OpenAI.</p>
        </div>

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
      </main>
    </div>
  );
}
