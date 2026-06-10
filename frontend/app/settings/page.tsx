"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Sidebar from "../../components/Sidebar";
import {
  ApiKeyEntry,
  ApiProviderConfig,
  DEFAULT_API_PROVIDERS,
  DEFAULT_MARKET_PROVIDERS,
  DEFAULT_MEDIA_PROVIDERS,
  MarketProviderConfig,
  MediaProviderConfig,
  MEDIA_PROVIDER_MODELS,
  PROVIDER_MODELS,
  maskKey,
  readApiProviders,
  readMarketProviders,
  readMediaProviders,
  writeApiProviders,
  writeMarketProviders,
  writeMediaProviders,
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
import { saveCloudState, readStoredToken, syncFromCloud } from "../../lib/cloudState";

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
  const [section, setSection] = useState<"ai" | "media" | "market" | "macro" | "news" | "global" | "mode" | "usage" | "backup">("ai");
  const [providers, setProviders] = useState<ApiProviderConfig[]>(DEFAULT_API_PROVIDERS);
  const [marketProviders, setMarketProviders] = useState<MarketProviderConfig[]>(DEFAULT_MARKET_PROVIDERS);
  const [mediaProviders, setMediaProviders] = useState<MediaProviderConfig[]>(DEFAULT_MEDIA_PROVIDERS);
  const [activeProviderId, setActiveProviderId] = useState(DEFAULT_API_PROVIDERS[0].id);
  const [activeMediaProviderId, setActiveMediaProviderId] = useState(DEFAULT_MEDIA_PROVIDERS[0].id);
  const [rawKeys, setRawKeys] = useState("");
  const [editingKeyId, setEditingKeyId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState("");
  const [checkingKeyId, setCheckingKeyId] = useState<string | null>(null);
  const [marketMode, setMarketMode] = useState<MarketMode>("us");
  const [planProfile, setPlanProfile] = useState<PlanProfile>({ tier: "free", ...PLAN_OPTIONS.free });
  const [usageLog, setUsageLog] = useState<UsageEvent[]>([]);
  const [backupJson, setBackupJson] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [cloudStatus, setCloudStatus] = useState("");

  useEffect(() => {
    setProviders(readApiProviders());
    setMarketProviders(readMarketProviders());
    setMediaProviders(readMediaProviders());
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

  function saveMediaProviders(nextProviders: MediaProviderConfig[]) {
    setMediaProviders(nextProviders);
    writeMediaProviders(nextProviders);
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

  const activeMediaProvider = useMemo(
    () => mediaProviders.find((provider) => provider.id === activeMediaProviderId) ?? mediaProviders[0],
    [mediaProviders, activeMediaProviderId]
  );

  function updateActiveMediaProvider(updater: (provider: MediaProviderConfig) => MediaProviderConfig) {
    if (!activeMediaProvider) return;
    saveMediaProviders(
      mediaProviders.map((provider) => (provider.id === activeMediaProvider.id ? updater(provider) : provider))
    );
  }

  async function checkMediaProvider(provider: MediaProviderConfig) {
    setCheckingKeyId(provider.id);
    try {
      const response = await fetch(`${API_BASE_URL}/api/kie/media/test-key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: provider.id,
          api_key: provider.apiKey,
        }),
      });
      const result = await response.json();
      saveMediaProviders(
        mediaProviders.map((item) =>
          item.id === provider.id
            ? {
                ...item,
                status: result.status === "live" ? "live" : "dead",
                lastChecked: new Date().toISOString(),
                lastCheckDetail: result.detail ?? "",
              }
            : item
        )
      );
      setStatusMessage(
        `${provider.name}: ${result.status === "live" ? "LIVE" : "DEAD"}${result.detail ? ` - ${result.detail}` : ""}`
      );
      appendUsageEvent({ action: "media_key_check", ticker: provider.id, source: "settings" });
    } catch {
      saveMediaProviders(
        mediaProviders.map((item) =>
          item.id === provider.id
            ? { ...item, status: "dead", lastChecked: new Date().toISOString(), lastCheckDetail: "Gagal cek key." }
            : item
        )
      );
      setStatusMessage(`${provider.name}: DEAD - Gagal cek key.`);
    } finally {
      setCheckingKeyId(null);
    }
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
          base_url: activeProvider.baseUrl || undefined,
        }),
      });
      const result = await response.json();
      updateKey(entry.id, (current) => ({
        ...current,
        status: result.status === "live" ? "live" : "dead",
        lastChecked: new Date().toISOString(),
      }));
      setStatusMessage(`${activeProvider.name} API: ${result.status === "live" ? "LIVE" : "DEAD"}${result.detail ? ` - ${result.detail}` : ""}`);
      appendUsageEvent({ action: "ai_key_check", ticker: activeProvider.id, source: "settings" });
    } catch {
      updateKey(entry.id, (current) => ({
        ...current,
        status: "dead",
        lastChecked: new Date().toISOString(),
      }));
      setStatusMessage(`Gagal menghubungi server backend untuk cek key.`);
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
    setBackupJson(
      JSON.stringify(
        {
          user: exportUserData(),
          apiProviders: readApiProviders(),
          marketProviders: readMarketProviders(),
          mediaProviders: readMediaProviders(),
        },
        null,
        2
      )
    );
    setStatusMessage("Backup data lokal siap disalin.");
  }

  function importBackup() {
    try {
      const payload = JSON.parse(backupJson) as {
        user?: ReturnType<typeof exportUserData>;
        apiProviders?: ApiProviderConfig[];
        marketProviders?: MarketProviderConfig[];
        mediaProviders?: MediaProviderConfig[];
      };
      if (payload.user) {
        importUserData(payload.user);
      }
      if (payload.apiProviders) {
        writeApiProviders(payload.apiProviders);
      }
      if (payload.marketProviders) {
        writeMarketProviders(payload.marketProviders);
      }
      if (payload.mediaProviders) {
        writeMediaProviders(payload.mediaProviders);
      }
      setProviders(readApiProviders());
      setMarketProviders(readMarketProviders());
      setMediaProviders(readMediaProviders());
      setMarketMode(readMarketMode());
      setPlanProfile(readPlanProfile());
      setUsageLog(readUsageLog());
      setStatusMessage("Backup berhasil diimpor.");
      appendUsageEvent({ action: "backup_import", ticker: "local", source: "settings" });
    } catch {
      setStatusMessage("JSON backup belum valid.");
    }
  }

  async function syncToCloud() {
    try {
      if (!readStoredToken()) {
        setCloudStatus("Login dulu agar bisa sinkron ke backend.");
        return;
      }
      const ok = await saveCloudState();
      setCloudStatus(ok ? "Data lokal tersimpan ke cloud." : "Gagal menyimpan ke cloud.");
      appendUsageEvent({ action: "cloud_save", ticker: "local", source: "settings" });
    } catch {
      setCloudStatus("Gagal menyimpan ke cloud.");
    }
  }

  async function syncFromCloudAction() {
    try {
      if (!readStoredToken()) {
        setCloudStatus("Login dulu agar bisa tarik data dari cloud.");
        return;
      }
      const ok = await syncFromCloud();
      if (ok) {
        setProviders(readApiProviders());
        setMarketProviders(readMarketProviders());
        setMediaProviders(readMediaProviders());
        setMarketMode(readMarketMode());
        setPlanProfile(readPlanProfile());
        setUsageLog(readUsageLog());
        setCloudStatus("Data cloud berhasil dimuat.");
        appendUsageEvent({ action: "cloud_load", ticker: "local", source: "settings" });
      } else {
        setCloudStatus("Belum ada state cloud untuk user ini.");
      }
    } catch {
      setCloudStatus("Gagal memuat data cloud.");
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
        {cloudStatus ? <div className="dashboard-alert">{cloudStatus}</div> : null}

        <div className="settings-section-tabs">
          <button className={section === "ai" ? "active" : ""} type="button" onClick={() => setSection("ai")}>
            <span>Pusat AI</span>
            <span className="tab-badge tab-badge--required">Wajib</span>
          </button>
          <button className={section === "media" ? "active" : ""} type="button" onClick={() => setSection("media")}>
            <span>Pusat Media</span>
            <span className="tab-badge tab-badge--optional">Opsional</span>
          </button>
          <button className={section === "market" ? "active" : ""} type="button" onClick={() => setSection("market")}>
            <span>Pusat Data IDX</span>
            <span className="tab-badge tab-badge--optional">Opsional</span>
          </button>
          <button className={section === "global" ? "active" : ""} type="button" onClick={() => setSection("global")}>
            <span>Data Global</span>
            <span className="tab-badge tab-badge--optional">Opsional</span>
          </button>
          <button className={section === "macro" ? "active" : ""} type="button" onClick={() => setSection("macro")}>
            <span>Data Macro</span>
            <span className="tab-badge tab-badge--optional">Opsional</span>
          </button>
          <button className={section === "news" ? "active" : ""} type="button" onClick={() => setSection("news")}>
            <span>Data Berita</span>
            <span className="tab-badge tab-badge--optional">Opsional</span>
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
              </div>

              <div className="api-provider-config">
                <label>
                  Base URL / Endpoint
                  <input
                    value={activeProvider.baseUrl}
                    onChange={(event) =>
                      updateActiveProvider((provider) => ({ ...provider, baseUrl: event.target.value }))
                    }
                    placeholder="https://api.provider.com/v1"
                  />
                </label>
                <label>
                  Model
                  <select
                    value={activeProvider.model}
                    onChange={(event) =>
                      updateActiveProvider((provider) => ({ ...provider, model: event.target.value }))
                    }
                  >
                    {PROVIDER_MODELS[activeProvider.id]?.map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </select>
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

        {section === "media" ? (
          <div className="settings-layout">
            <aside className="settings-tabs">
              {mediaProviders.map((provider) => (
                <button
                  key={provider.id}
                  className={provider.id === activeMediaProvider.id ? "active" : ""}
                  type="button"
                  onClick={() => setActiveMediaProviderId(provider.id)}
                >
                  <span>{provider.name}</span>
                  <strong>{provider.enabled ? "aktif" : "nonaktif"}</strong>
                </button>
              ))}
            </aside>

            <section className="api-center">
              <div className="api-center__topline">
                <div>
                  <h2>{activeMediaProvider.name}</h2>
                  <p>Key ini dipakai untuk generate gambar dan video langsung dari studio aplikasi.</p>
                </div>
                <span className={`api-status api-status--${activeMediaProvider.status}`}>
                  {activeMediaProvider.status === "live"
                    ? "LIVE"
                    : activeMediaProvider.status === "dead"
                      ? "DEAD"
                      : "BELUM CEK"}
                </span>
              </div>

              <div className="media-provider-grid">
                <label>
                  Model
                  <select
                    value={activeMediaProvider.model}
                    onChange={(event) =>
                      updateActiveMediaProvider((provider) => ({ ...provider, model: event.target.value }))
                    }
                  >
                    {MEDIA_PROVIDER_MODELS[activeMediaProvider.id]?.map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  API Key
                  <input
                    value={activeMediaProvider.apiKey}
                    onChange={(event) =>
                      updateActiveMediaProvider((provider) => ({
                        ...provider,
                        apiKey: event.target.value,
                        status: "unknown",
                      }))
                    }
                    placeholder="Tempel API key Kie.ai di sini"
                  />
                </label>

                <label className="provider-toggle">
                  <input
                    type="checkbox"
                    checked={activeMediaProvider.enabled}
                    onChange={(event) =>
                      updateActiveMediaProvider((provider) => ({ ...provider, enabled: event.target.checked }))
                    }
                  />
                  Aktifkan provider
                </label>

                <button type="button" onClick={() => checkMediaProvider(activeMediaProvider)}>
                  {checkingKeyId === activeMediaProvider.id ? "Cek..." : "Cek Status"}
                </button>
              </div>

              <div className="api-empty">{activeMediaProvider.notes}</div>
              {activeMediaProvider.lastCheckDetail ? (
                <div className="api-empty">Hasil cek terakhir: {activeMediaProvider.lastCheckDetail}</div>
              ) : null}

              <div className="api-key-list">
                <div className="media-preview-card">
                  <h3>Studio Pakai Provider Ini</h3>
                  <p>
                    {activeMediaProvider.id === "kie_image"
                      ? "Buka Studio Gambar untuk text-to-image dan image editing."
                      : "Buka Studio Video untuk text-to-video dan image-to-video."}
                  </p>
                  <div className="media-preview-actions">
                    <a href={activeMediaProvider.id === "kie_image" ? "/studio/image" : "/studio/video"}>
                      Buka Studio
                    </a>
                    <span>{activeMediaProvider.enabled ? "Siap dipakai" : "Aktifkan dulu agar enak dipakai"}</span>
                  </div>
                </div>
              </div>
            </section>
          </div>
        ) : null}

        {section === "market" ? (
          <section className="api-center">
            <div className="api-center__topline">
              <div>
                <h2>Data Provider IDX (Bursa Efek Indonesia)</h2>
                <p>Provider khusus untuk data pasar Indonesia: bandarmology, broker summary, foreign flow, dan order book.</p>
              </div>
            </div>

              <div className="market-provider-list">
              {marketProviders.filter((p) => p.category === "idx").map((provider) => (
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

                  {provider.placeholderEndpoint ? (
                    <p className="page-subtitle" style={{ marginBottom: "8px", color: "#666" }}>
                      💡 Contoh endpoint: <code>{provider.placeholderEndpoint}</code>
                    </p>
                  ) : null}

                  <label>
                    Endpoint API
                    <input
                      value={provider.endpoint}
                      placeholder={provider.placeholderEndpoint || "https://provider-api.com/idx/{ticker}"}
                      onChange={(event) =>
                        saveMarketProviders(
                          marketProviders.map((item) =>
                            item.id === provider.id ? { ...item, endpoint: event.target.value, status: "unknown" } : item
                          )
                        )
                      }
                    />
                  </label>

                  <p className="page-subtitle">
                    Pakai <code>{`{ticker}`}</code> dan <code>{`{days}`}</code> di endpoint kalau provider mendukung
                    template. Untuk RapidAPI, isi endpoint lengkap lalu cukup tempel API key.
                  </p>

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

        {section === "global" ? (
          <section className="api-center">
            <div className="api-center__topline">
              <div>
                <h2>Data Provider Global Market</h2>
                <p>Provider untuk data pasar global seperti MarketFlow, Yahoo Finance, Alpha Vantage, dll.</p>
              </div>
            </div>

            <div className="market-provider-list">
              {marketProviders.filter((p) => p.category === "global").map((provider) => (
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

                  {provider.placeholderEndpoint ? (
                    <p className="page-subtitle" style={{ marginBottom: "8px", color: "#666" }}>
                      💡 Contoh endpoint: <code>{provider.placeholderEndpoint}</code>
                    </p>
                  ) : null}

                  <label>
                    Endpoint API
                    <input
                      value={provider.endpoint}
                      placeholder={provider.placeholderEndpoint || "https://api.provider.com/market/{symbol}"}
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

        {section === "macro" ? (
          <section className="api-center">
            <div className="api-center__topline">
              <div>
                <h2>Data Provider Macro Economy</h2>
                <p>Provider untuk data makro ekonomi: kalender ekonomi, BI Rate, inflasi, USD/IDR, komoditas, dll.</p>
              </div>
            </div>

            <div className="market-provider-list">
              {marketProviders.filter((p) => p.category === "macro").map((provider) => (
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

                  {provider.placeholderEndpoint ? (
                    <p className="page-subtitle" style={{ marginBottom: "8px", color: "#666" }}>
                      💡 Contoh endpoint: <code>{provider.placeholderEndpoint}</code>
                    </p>
                  ) : null}

                  <label>
                    Endpoint API
                    <input
                      value={provider.endpoint}
                      placeholder={provider.placeholderEndpoint || "https://api.provider.com/macro/indicators"}
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

        {section === "news" ? (
          <section className="api-center">
            <div className="api-center__topline">
              <div>
                <h2>Data Provider News & Sentiment</h2>
                <p>Provider untuk berita ekonomi, RSS feed, sentiment analysis, dan news aggregator.</p>
              </div>
            </div>

            <div className="market-provider-list">
              {marketProviders.filter((p) => p.category === "news").map((provider) => (
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

                  {provider.placeholderEndpoint ? (
                    <p className="page-subtitle" style={{ marginBottom: "8px", color: "#666" }}>
                      💡 Contoh endpoint: <code>{provider.placeholderEndpoint}</code>
                    </p>
                  ) : null}

                  <label>
                    Endpoint API
                    <input
                      value={provider.endpoint}
                      placeholder={provider.placeholderEndpoint || "https://api.provider.com/news/finance"}
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
              <button type="button" onClick={syncFromCloudAction}>
                Load Cloud
              </button>
              <button type="button" onClick={syncToCloud}>
                Save Cloud
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
