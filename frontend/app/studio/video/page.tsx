"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Sidebar from "../../../components/Sidebar";
import { DEFAULT_MEDIA_PROVIDERS, MediaProviderConfig, readMediaProviders } from "../../../lib/apiKeys";
import { appendUsageEvent } from "../../../lib/userData";
import { getApiBaseUrl } from "../../../lib/apiBase";

type VideoTaskResponse = {
  code?: number;
  msg?: string;
  data?: {
    taskId?: string;
    status?: string;
    successFlag?: number;
    response?: {
      videoUrl?: string;
      videoUrls?: string[];
      resultUrls?: string[];
    };
    errorMessage?: string;
    errorCode?: string;
  };
};

function pickVideoProvider(): MediaProviderConfig {
  const providers = readMediaProviders();
  return providers.find((item) => item.id === "kie_video") ?? DEFAULT_MEDIA_PROVIDERS[1];
}

function collectUrls(payload: unknown): string[] {
  const urls = new Set<string>();
  const visit = (value: unknown) => {
    if (!value) return;
    if (typeof value === "string" && /^https?:\/\//i.test(value)) {
      urls.add(value);
      return;
    }
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (typeof value === "object") {
      Object.values(value as Record<string, unknown>).forEach(visit);
    }
  };
  visit(payload);
  return [...urls];
}

export default function VideoStudioPage() {
  const [provider, setProvider] = useState<MediaProviderConfig>(pickVideoProvider());
  const [prompt, setPrompt] = useState("A cinematic stock chart spinning through a neon trading room");
  const [imageUrl, setImageUrl] = useState("");
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [duration, setDuration] = useState(5);
  const [quality, setQuality] = useState("720p");
  const [waterMark, setWaterMark] = useState("kie.ai");
  const [taskId, setTaskId] = useState("");
  const [statusText, setStatusText] = useState("Belum ada tugas.");
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [resultUrls, setResultUrls] = useState<string[]>([]);
  const [rawResult, setRawResult] = useState<VideoTaskResponse | null>(null);
  const [error, setError] = useState("");

  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);

  useEffect(() => {
    const updateProvider = () => setProvider(pickVideoProvider());
    updateProvider();
    window.addEventListener("storage", updateProvider);
    return () => window.removeEventListener("storage", updateProvider);
  }, []);

  const pollStatus = useCallback(
    async (nextTaskId = taskId) => {
      if (!nextTaskId) return;
      try {
        const response = await fetch(`${apiBaseUrl}/api/kie/media/video/record-detail`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            task_id: nextTaskId,
            api_key: provider.apiKey,
          }),
        });
        if (!response.ok) {
          const body = await response.json().catch(() => null);
          throw new Error(body?.detail ?? `${response.status} ${response.statusText}`);
        }
        const payload = (await response.json()) as VideoTaskResponse;
        setRawResult(payload);
        const record = payload.data;
        const resolvedUrls = record?.response?.videoUrls?.length
          ? record.response.videoUrls
          : record?.response?.resultUrls?.length
            ? record.response.resultUrls
            : collectUrls(record?.response ?? record);
        setResultUrls(resolvedUrls);
        const success = record?.successFlag === 1 || record?.status === "success";
        setStatusText(success ? "Selesai" : record?.status ?? "Memproses...");
        if (success) setPolling(false);
      } catch (exc) {
        setError(exc instanceof Error ? exc.message : "Gagal mengecek status video.");
        setPolling(false);
      }
    },
    [apiBaseUrl, provider.apiKey, taskId]
  );

  useEffect(() => {
    if (!taskId) return;
    void pollStatus(taskId);
    setPolling(true);
    const timer = window.setInterval(() => void pollStatus(taskId), 10000);
    return () => window.clearInterval(timer);
  }, [pollStatus, taskId]);

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResultUrls([]);
    try {
      if (!provider.apiKey.trim()) {
        throw new Error("API key Kie.ai belum diisi di Settings > Pusat Media.");
      }
      const response = await fetch(`${apiBaseUrl}/api/kie/media/video/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: provider.apiKey,
          model: provider.model,
          prompt,
          image_url: imageUrl.trim() || undefined,
          aspect_ratio: aspectRatio,
          duration,
          quality,
          water_mark: waterMark,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `${response.status} ${response.statusText}`);
      }
      const payload = (await response.json()) as { data?: { taskId?: string } };
      const nextTaskId = payload.data?.taskId ?? "";
      setTaskId(nextTaskId);
      setStatusText(nextTaskId ? "Tugas dikirim. Menunggu hasil..." : "Tugas terkirim.");
      appendUsageEvent({ action: "kie_video_generate", ticker: "local", source: "studio-video" });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Gagal generate video.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main">
        <div className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">Studio Video</p>
            <h1>Kie.ai Video Studio</h1>
            <p className="page-subtitle">Text-to-video dan image-to-video memakai provider yang diisi pengguna di Settings.</p>
          </div>
          <div className="report-toolbar">
            <Link className="watchlist-savebar__link" href="/settings">
              Buka Settings
            </Link>
          </div>
        </div>

        {error ? <div className="dashboard-alert">{error}</div> : null}

        <div className="studio-layout">
          <section className="studio-panel">
            <div className="studio-panel__topline">
              <div>
                <h2>{provider.name}</h2>
                <p>
                  Status:{" "}
                  <strong className={`api-status api-status--${provider.status}`}>
                    {provider.status === "live" ? "LIVE" : provider.status === "dead" ? "DEAD" : "BELUM CEK"}
                  </strong>
                  {" "}• Model: {provider.model}
                </p>
              </div>
              <span className={provider.enabled ? "mode-pill mode-pill--live" : "mode-pill mode-pill--demo"}>
                {provider.enabled ? "Siap Pakai" : "Nonaktif"}
              </span>
            </div>

            <form className="studio-form" onSubmit={handleGenerate}>
              <label>
                Prompt
                <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
              </label>
              <div className="studio-form__grid">
                <label>
                  Image URL Reference
                  <input value={imageUrl} onChange={(event) => setImageUrl(event.target.value)} />
                </label>
                <label>
                  Aspect Ratio
                  <select value={aspectRatio} onChange={(event) => setAspectRatio(event.target.value)}>
                    <option value="16:9">16:9</option>
                    <option value="9:16">9:16</option>
                    <option value="1:1">1:1</option>
                    <option value="4:3">4:3</option>
                  </select>
                </label>
                <label>
                  Duration
                  <select value={String(duration)} onChange={(event) => setDuration(Number(event.target.value))}>
                    <option value="5">5 detik</option>
                    <option value="10">10 detik</option>
                  </select>
                </label>
                <label>
                  Quality
                  <select value={quality} onChange={(event) => setQuality(event.target.value)}>
                    <option value="720p">720p</option>
                    <option value="1080p">1080p</option>
                  </select>
                </label>
              </div>

              <label>
                Watermark
                <input value={waterMark} onChange={(event) => setWaterMark(event.target.value)} />
              </label>

              <div className="studio-actions">
                <button type="submit" disabled={loading}>
                  {loading ? "Mengirim..." : "Generate"}
                </button>
                <button type="button" onClick={() => pollStatus()} disabled={!taskId || polling}>
                  {polling ? "Mengecek..." : "Refresh Status"}
                </button>
              </div>
            </form>
          </section>

          <aside className="studio-panel studio-preview">
            <div className="studio-panel__topline">
              <div>
                <h2>Status Tugas</h2>
                <p>{statusText}</p>
              </div>
              <span>{taskId || "no task"}</span>
            </div>

            <div className="studio-task">
              <span>Task ID</span>
              <strong>{taskId || "-"}</strong>
              <span>Provider: {provider.id}</span>
            </div>

            {resultUrls.length ? (
              <div className="studio-result-grid">
                {resultUrls.map((url) => (
                  <figure key={url}>
                    <video src={url} controls playsInline />
                    <figcaption>{url}</figcaption>
                  </figure>
                ))}
              </div>
            ) : (
              <div className="api-empty">
                {provider.apiKey ? "Hasil generate akan muncul di sini." : "Masukkan API key di Settings > Pusat Media dulu."}
              </div>
            )}

            {rawResult ? (
              <details className="studio-json">
                <summary>Lihat raw response</summary>
                <pre>{JSON.stringify(rawResult, null, 2)}</pre>
              </details>
            ) : null}
          </aside>
        </div>
      </main>
    </div>
  );
}
