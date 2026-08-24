const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface AccountOption {
  account_id: string;
  account_name: string;
  plan: string;
}

export interface SessionInfo {
  session_id: string;
  role: "customer" | "internal";
  account_id: string | null;
}

export interface EscalationDraft {
  status: string;
  draft: {
    action_type: string;
    reason: string;
    summary: string;
    ticket_id: string | null;
    account_id: string | null;
  };
  confirmation_token: string;
  session_id: string;
}

export interface ChatMessage {
  role: "user" | "model";
  content: string;
  tool_calls: string[];
  created_at: string;
}

export interface FlaggedIssue {
  id: number;
  issue_type: string;
  severity: "red" | "amber" | "gray";
  summary: string;
  affected: Record<string, unknown>;
  created_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  listAccounts: () => request<AccountOption[]>("/api/auth/accounts"),
  createSession: (identity: string) =>
    request<SessionInfo>("/api/auth/session", { method: "POST", body: JSON.stringify({ identity }) }),
  history: (session_id: string) =>
    request<ChatMessage[]>(`/api/chat/history?session_id=${encodeURIComponent(session_id)}`),
  chat: (session_id: string, message: string) =>
    request<{ text: string; tool_calls: string[]; escalation_draft: EscalationDraft | null }>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ session_id, message }),
    }),
  confirmAction: (session_id: string, token: string, action: "confirm" | "cancel") =>
    request<{ status: string; escalation_id?: string; reason?: string }>("/api/chat/confirm-action", {
      method: "POST",
      body: JSON.stringify({ session_id, token, action }),
    }),
  flaggedIssues: (session_id: string) =>
    request<FlaggedIssue[]>(`/api/ops/flagged-issues?session_id=${encodeURIComponent(session_id)}`),
  runDetection: (session_id: string) =>
    request<Record<string, number>>(`/api/ops/run-detection?session_id=${encodeURIComponent(session_id)}`, {
      method: "POST",
    }),
};
