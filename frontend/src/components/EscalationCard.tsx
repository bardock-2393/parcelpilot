import { useState } from "react";
import { api, type EscalationDraft } from "../api";

interface Props {
  sessionId: string;
  draft: EscalationDraft;
  onResolved: (state: "created" | "cancelled", escalationId?: string) => void;
}

export function EscalationCard({ sessionId, draft, onResolved }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act(action: "confirm" | "cancel") {
    setBusy(true);
    setError(null);
    try {
      const result = await api.confirmAction(sessionId, draft.confirmation_token, action);
      if (result.status === "created") onResolved("created", result.escalation_id);
      else if (result.status === "cancelled") onResolved("cancelled");
      else setError(result.reason ?? "Action rejected.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="escalation-card">
      <div className="escalation-card-title">Proposed action: {draft.draft.action_type.replace(/_/g, " ")}</div>
      <div className="escalation-card-summary">{draft.draft.summary}</div>
      <div className="escalation-card-reason">Why: {draft.draft.reason}</div>
      {error && <div className="escalation-card-error">{error}</div>}
      <div className="escalation-card-actions">
        <button disabled={busy} className="btn-primary" onClick={() => act("confirm")}>
          Confirm
        </button>
        <button disabled={busy} className="btn-secondary" onClick={() => act("cancel")}>
          Cancel
        </button>
      </div>
    </div>
  );
}

export function EscalationResultBadge({ state, escalationId }: { state: "created" | "cancelled"; escalationId?: string }) {
  if (state === "created") {
    return <div className="escalation-result created">✅ Escalation created — ID #{escalationId}</div>;
  }
  return <div className="escalation-result cancelled">Cancelled</div>;
}
