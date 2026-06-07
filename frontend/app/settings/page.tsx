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
import {
  appendUsageEvent,
  exportUserData,
  importUserData,
  MarketMode,
  normalizeTickerForMarket,
  readMarketMode,
  readPlanProfile,
  readUsageLog,
  writeMarketMode,
  writePlanProfile,
  PlanProfile,
  UsageEvent,
} from "../../lib/userData";

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

const PLAN_OPTIONS: Record<PlanProfile["tier"], Pick<PlanProfile, "dailyApiLimit" | "monthlyReportLimit">> = {
  free: { dailyApiLimit: 50, monthlyReportLimit: 100 },
  pro: { dailyApiLimit: 500, monthlyReportLimit: 1000 },
};

export default function SettingsPage() {
  const [section, setSection] = useState<"ai" | "market" | "mode" | "usage" | "backup">("ai");
  const [providers, setProviders] = useState<ApiProviderConfig[]>(DEFAULT_API_PROVIDERS);
  const [marketProviders, setMarketProviders] = useState<MarketProviderConfig[]>(DEFAULT_MARKET_PROVIDERS);
  const [activeProviderId, setActiveProviderId] = useState(DEFAULT_API_PROVIDERS[0].id);
  const [rawKeys, setRawKeys] = useState("");
  const [editingKeyId, setEditingKeyId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState("");
  const [checkingKeyId, setCheckingKeyId] = useState<string | null>(null);
  const [marketMode, setMarketMode] = useState<MarketMode>("us");
  const [planProfile, setPlanProfile] = useState<PlanProfile>({ tier: "free", ...PLAN_OPTIONS.free });
  const [usageLog, setUsageLog] = useState<UsageEvent[]>([]);
  const [backupJson, setBackupJson] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    setProviders(readApiProviders());
    setMarketProviders(readMarketProviders());
    setMarketMode(readMarketMode());
    setPlanProfile(readPlanProfile());
    setUsageLog(readUsageLog());
  }, []);

  function saveProviders(nextProviders: ApiProviderConfig[]) {
    setProviders(nextProviders);
    writeApiProviders(nextProviders);
  }

  function saveMarketProviders(nextProviders: MarketProviderConfig[]) {
    setMarketProviders(nextProviders);
    writeMarketProviders(nextProviders);
  }

  function savePlan(nextPlan: PlanProfile) {
    setPlanProfile(nextPlan);
    writePlanProfile(nextPlan);
  }

  function saveMarketMode(nextMode: MarketMode) {
    setMarketMode(nextMode);
    writeMarketMode(nextMode);
  }

  function refreshUsage() {
    setUsageLog(readUsageLog());
    setPlanProfile(readPlanProfile());
    setStatusMessage("Data lokal diperbarui.");
  }

  const activeProvider = useMemo(
    () => providers.find((provider) => provider.id === activeProviderId) ?? providers[0],
    [providers, activeProviderId]
  );

  const usageSummary = useMemo(() => {
    const counts = usageLog.reduce<Record<string, number>>((acc, item) => {
      acc[item.action] = (acc[item.action] ?? 0) + 1;
      return acc;
    }, {});
    return {
      total: usageLog.length,
      topActions: Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5),
    };
  }, [usageLog]);

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
    setStatusMessage(`Menambahkan ${nextKeys.length} key baru.`);
    appendUsageEvent({ action: "ai_key_add", ticker: activeProvider.id, source: "settings" });
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
      appendUsageEvent({ action: "ai_key_check", ticker: activeProvider.id, source: "settings" });
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
    appendUsageEvent({ action: "market_provider_check", ticker: provider.id, source: "settings" });
  }

  function exportBackup() {
    setBackupJson(JSON.stringify(exportUserData(), null, 2));
    setStatusMessage("Backup data lokal siap disalin.");
  }

  function importBackup() {
    try {
      const payload = JSON.parse(backupJson) as Parameters<typeof importUserData>[0];
      importUserData(payload);
      setProviders(readApiProviders());
      setMarketProviders(readMarketProviders());
      setMarketMode(readMarketMode());
      setPlanProfile(readPlanProfile());
      setUsageLog(readUsageLog());
      setStatusMessage("Backup berhasil diimpor.");
      appendUsageEvent({ action: "backup_import", ticker: "local", source: "settings" });
    } catch {
      setStatusMessage("JSON backup belum valid.");
    }
  }

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="settings-header">
          <p className="dashboard-eyebrow">Settings</p>
          <h1>Pusat Kontrol</h1>
          <p>Kelola AI key, provider IDX, mode pasar, paket kuota, dan backup data lokal pengguna.</p>
        </div>

        {statusMessage ? <div className="dashboard-alert">{statusMessage}</div> : null}

        <div className="settings-section-tabs">
          <button className={section === "ai" ? "active" : ""} type="button" onClick={() => setSection("ai")}>
            Pusat AI
          </button>
          <button className={section === "market" ? "active" : ""} type="button" onClick={() => setSection("market")}>
            Pusat Data IDX
          </button>
          <button className={section === "mode" ? "active" : ""} type="button" onClick={() => setSection("mode")}>
            Mode Pasar
          </button>
          <button className={section === "usage" ? "active" : ""} type="button" onClick={() => setSection("usage")}>
            Paket & Kuota
          </button>
          <button className={section === "backup" ? "active" : ""} type="button" onClick={() => setSection("backup")}>
            Backup
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
        ) : null}

        {section === "market" ? (
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
        ) : null}

        {section === "mode" ? (
          <section className="api-center">
            <div className="api-center__topline">
              <div>
                <h2>Mode Pasar</h2>
                <p>Mode ini menentukan perilaku ticker default dan auto-suffix saat pengguna mengetik saham tanpa kode bursa.</p>
              </div>
            </div>

            <div className="mode-switcher">
              <button type="button" className={marketMode === "us" ? "active" : ""} onClick={() => saveMarketMode("us")}>
                US Market
              </button>
              <button type="button" className={marketMode === "id" ? "active" : ""} onClick={() => saveMarketMode("id")}>
                IDX / Indonesia
              </button>
            </div>

            <div className="mode-grid">
              <div>
                <span>Contoh auto-normalize</span>
                <strong>{marketMode === "id" ? normalizeTickerForMarket("BBCA", "id") : normalizeTickerForMarket("AAPL", "us")}</strong>
              </div>
              <div>
                <span>Input manual</span>
                <strong>{marketMode === "id" ? "BBCA, BBRI, TLKM" : "AAPL, MSFT, NVDA"}</strong>
              </div>
            </div>

            <p className="api-empty">
              Saat mode IDX aktif, ticker tanpa suffix akan otomatis menjadi `.JK`. Ini membantu scanner, report, dan portfolio tetap konsisten.
            </p>
          </section>
        ) : null}

        {section === "usage" ? (
          <section className="api-center">
            <div className="api-center__topline">
              <div>
                <h2>Paket & Kuota</h2>
                <p>Rangkuman pemakaian lokal untuk persiapan free/pro, plus log aktivitas fitur yang paling sering dipakai.</p>
              </div>
              <button type="button" onClick={refreshUsage}>
                Refresh
              </button>
            </div>

            <div className="mode-grid">
              <div>
                <span>Tier</span>
                <strong>{planProfile.tier.toUpperCase()}</strong>
              </div>
              <div>
                <span>Limit API Harian</span>
                <strong>{planProfile.dailyApiLimit}</strong>
              </div>
              <div>
                <span>Limit Report Bulanan</span>
                <strong>{planProfile.monthlyReportLimit}</strong>
              </div>
              <div>
                <span>Total Event</span>
                <strong>{usageSummary.total}</strong>
              </div>
            </div>

            <div className="mode-switcher">
              <button
                type="button"
                className={planProfile.tier === "free" ? "active" : ""}
                onClick={() => savePlan({ tier: "free", ...PLAN_OPTIONS.free })}
              >
                Free
              </button>
              <button
                type="button"
                className={planProfile.tier === "pro" ? "active" : ""}
                onClick={() => savePlan({ tier: "pro", ...PLAN_OPTIONS.pro })}
              >
                Pro
              </button>
            </div>

            <div className="usage-list">
              <article className="utility-card">
                <h2>Aktivitas Teratas</h2>
                {usageSummary.topActions.length ? (
                  usageSummary.topActions.map(([action, count]) => (
                    <div className="utility-row" key={action}>
                      <span>{action}</span>
                      <strong>{count}</strong>
                    </div>
                  ))
                ) : (
                  <p>Belum ada aktivitas tercatat.</p>
                )}
              </article>

              <article className="utility-card">
                <h2>Riwayat Terbaru</h2>
                {usageLog.length ? (
                  <div className="usage-log-list">
                    {usageLog.slice(0, 10).map((event) => (
                      <div className="usage-log-row" key={event.id}>
                        <span>{event.action}</span>
                        <strong>{event.ticker || "-"}</strong>
                        <span>{event.source}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p>Belum ada log penggunaan.</p>
                )}
              </article>
            </div>
          </section>
        ) : null}

        {section === "backup" ? (
          <section className="api-center">
            <div className="api-center__topline">
              <div>
                <h2>Backup & Restore</h2>
                <p>Ekspor dan impor semua data lokal pengguna dalam satu file JSON.</p>
              </div>
            </div>

            <div className="backup-toolbar">
              <button type="button" onClick={exportBackup}>
                Export JSON
              </button>
              <button type="button" onClick={importBackup} disabled={!backupJson.trim()}>
                Import JSON
              </button>
              <button type="button" onClick={() => setBackupJson("")}>
                Bersihkan
              </button>
            </div>

            <textarea
              className="backup-textarea"
              value={backupJson}
              onChange={(event) => setBackupJson(event.target.value)}
              placeholder="Klik Export JSON untuk mengisi backup, atau tempel file backup di sini."
            />
          </section>
        ) : null}
      </main>
    </div>
  );
}
