"use client";

export type AnalystSummary = {
  ticker: string;
  summary: string;
  cycle_explanation: string;
  turning_points_explanation: string;
  scan_explanation: string;
  outlook: string;
};

type AIInfoPanelProps = {
  analysis: AnalystSummary | null;
  loading: boolean;
  error: string | null;
  ticker: string;
};

const fallbackSections = [
  {
    title: "Konteks Siklus",
    body: "Masukkan ticker untuk menggabungkan data siklus komposit, titik balik, dan peringkat scanner menjadi ringkasan pasar.",
  },
  {
    title: "Susunan Sinyal",
    body: "Analisis bekerja paling baik saat backend dapat membaca observasi planet dan pasar terbaru.",
  },
];

export default function AIInfoPanel({ analysis, loading, error, ticker }: AIInfoPanelProps) {
  return (
    <aside className="ai-panel">
      <div className="ai-panel__header">
        <div className="ai-panel__badge">AI</div>
        <div>
          <div className="ai-panel__eyebrow">Analisis AI</div>
          <div className="ai-panel__title">Analis {analysis?.ticker ?? ticker}</div>
        </div>
      </div>

      {loading ? (
        <div className="ai-panel__notice">Menyusun analisis pasar...</div>
      ) : error ? (
        <div className="ai-panel__notice ai-panel__notice--warning">{error}</div>
      ) : analysis ? (
        <>
          <section className="ai-panel__section">
            <h4>Ringkasan</h4>
            <p>{analysis.summary}</p>
          </section>

          <section className="ai-panel__section">
            <h4>Siklus Komposit</h4>
            <p>{analysis.cycle_explanation}</p>
          </section>

          <section className="ai-panel__section">
            <h4>Titik Balik</h4>
            <p>{analysis.turning_points_explanation}</p>
          </section>

          <section className="ai-panel__section">
            <h4>Insight Scanner</h4>
            <p>{analysis.scan_explanation}</p>
          </section>

          <div className="ai-panel__recommendation">
            <div>Prospek</div>
            <p>{analysis.outlook}</p>
          </div>
        </>
      ) : (
        fallbackSections.map((section) => (
          <section className="ai-panel__section" key={section.title}>
            <h4>{section.title}</h4>
            <p>{section.body}</p>
          </section>
        ))
      )}
    </aside>
  );
}
