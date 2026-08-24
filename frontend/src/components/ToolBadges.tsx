const LABELS: Record<string, { icon: string; label: string }> = {
  search_documents: { icon: "🔍", label: "Search documents" },
  query_structured_data: { icon: "📊", label: "Query data" },
  create_escalation: { icon: "🚨", label: "Create escalation" },
};

export function ToolBadges({ tools }: { tools: string[] }) {
  if (!tools.length) return null;
  return (
    <div className="tool-badges">
      {tools.map((t, i) => {
        const meta = LABELS[t] ?? { icon: "🛠️", label: t };
        return (
          <span className="tool-badge" key={`${t}-${i}`} title={t}>
            {meta.icon} {meta.label}
          </span>
        );
      })}
    </div>
  );
}
