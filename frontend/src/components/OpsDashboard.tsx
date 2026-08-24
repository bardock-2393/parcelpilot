import { useEffect, useMemo, useState } from "react";
import { api, type FlaggedIssue } from "../api";

const SEVERITY_ORDER = { red: 0, amber: 1, gray: 2 };
const SEVERITY_LABEL: Record<string, string> = { red: "Breached", amber: "Approaching", gray: "Pattern" };

export function OpsDashboard({ sessionId }: { sessionId: string }) {
  const [issues, setIssues] = useState<FlaggedIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"severity" | "recency" | "type">("severity");
  const [filterType, setFilterType] = useState<string>("all");

  function load() {
    setLoading(true);
    api
      .flaggedIssues(sessionId)
      .then(setIssues)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [sessionId]);

  async function runDetection() {
    setRunning(true);
    setError(null);
    try {
      await api.runDetection(sessionId);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run detection.");
    } finally {
      setRunning(false);
    }
  }

  const types = useMemo(() => Array.from(new Set(issues.map((i) => i.issue_type))), [issues]);

  const sorted = useMemo(() => {
    let list = issues;
    if (filterType !== "all") list = list.filter((i) => i.issue_type === filterType);
    return [...list].sort((a, b) => {
      if (sortBy === "severity") return SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
      if (sortBy === "recency") return b.created_at.localeCompare(a.created_at);
      return a.issue_type.localeCompare(b.issue_type);
    });
  }, [issues, sortBy, filterType]);

  return (
    <div className="ops-dashboard">
      <div className="ops-toolbar">
        <div className="ops-filters">
          <label>
            Sort by
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as typeof sortBy)}>
              <option value="severity">Severity</option>
              <option value="recency">Recency</option>
              <option value="type">Type</option>
            </select>
          </label>
          <label>
            Type
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="all">All</option>
              {types.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </label>
        </div>
        <button className="btn-primary" onClick={runDetection} disabled={running}>
          {running ? "Running…" : "Run detection now"}
        </button>
      </div>

      {error && <div className="ops-error">{error}</div>}
      {loading ? (
        <div className="ops-empty">Loading…</div>
      ) : sorted.length === 0 ? (
        <div className="ops-empty">No flagged issues. Run detection to check for new ones.</div>
      ) : (
        <div className="ops-grid">
          {sorted.map((issue) => (
            <div className={`ops-card severity-${issue.severity}`} key={issue.id}>
              <div className="ops-card-header">
                <span className="ops-card-type">{issue.issue_type.replace(/_/g, " ")}</span>
                <span className={`severity-dot severity-${issue.severity}`} title={SEVERITY_LABEL[issue.severity]} />
              </div>
              <div className="ops-card-summary">{issue.summary}</div>
              <div className="ops-card-meta">
                {Object.entries(issue.affected)
                  .filter(([k]) => k !== "ticket_ids")
                  .map(([k, v]) => (
                    <span key={k}>
                      {k}: {Array.isArray(v) ? v.join(", ") : String(v)}
                    </span>
                  ))}
              </div>
              <div className="ops-card-timestamp">{new Date(Number(issue.created_at) * 1000).toLocaleString()}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
