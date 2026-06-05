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
    title: "Cycle Context",
    body: "Load a ticker to combine composite cycle data, turning points, and scanner rankings into an AI market read.",
  },
  {
    title: "Signal Stack",
    body: "The analyst works best after seed data is available and the backend can return recent planetary and market observations.",
  },
];

export default function AIInfoPanel({ analysis, loading, error, ticker }: AIInfoPanelProps) {
  return (
    <aside className="ai-panel">
      <div className="ai-panel__header">
        <div className="ai-panel__badge">AI</div>
        <div>
          <div className="ai-panel__eyebrow">AI Analysis</div>
          <div className="ai-panel__title">{analysis?.ticker ?? ticker} Analyst</div>
        </div>
      </div>

      {loading ? (
        <div className="ai-panel__notice">Generating market read...</div>
      ) : error ? (
        <div className="ai-panel__notice ai-panel__notice--warning">{error}</div>
      ) : analysis ? (
        <>
          <section className="ai-panel__section">
            <h4>Summary</h4>
            <p>{analysis.summary}</p>
          </section>

          <section className="ai-panel__section">
            <h4>Composite Cycle</h4>
            <p>{analysis.cycle_explanation}</p>
          </section>

          <section className="ai-panel__section">
            <h4>Turning Points</h4>
            <p>{analysis.turning_points_explanation}</p>
          </section>

          <section className="ai-panel__section">
            <h4>Scanner Insight</h4>
            <p>{analysis.scan_explanation}</p>
          </section>

          <div className="ai-panel__recommendation">
            <div>Outlook</div>
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
