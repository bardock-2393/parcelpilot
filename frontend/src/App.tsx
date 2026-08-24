import { useEffect, useState } from "react";
import { api, type AccountOption, type SessionInfo } from "./api";
import { TopBar } from "./components/TopBar";
import { ChatView } from "./components/ChatView";
import { OpsDashboard } from "./components/OpsDashboard";
import type { ViewName } from "./types";
import "./App.css";

const IDENTITY_KEY = "parcelpilot_identity";

export default function App() {
  const [accounts, setAccounts] = useState<AccountOption[]>([]);
  const [identity, setIdentity] = useState<string>(() => localStorage.getItem(IDENTITY_KEY) ?? "");
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [view, setView] = useState<ViewName>("chat");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listAccounts()
      .then((list) => {
        setAccounts(list);
        setIdentity((current) => current || list[0]?.account_id || "internal");
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!identity) return;
    localStorage.setItem(IDENTITY_KEY, identity);
    api
      .createSession(identity)
      .then(setSession)
      .catch((e) => setError(e.message));
    setView("chat");
  }, [identity]);

  if (error) {
    return (
      <div className="app-error">
        Could not reach the ParcelPilot backend at the configured API URL. Is it running? ({error})
      </div>
    );
  }

  return (
    <div className="app-shell">
      <TopBar
        accounts={accounts}
        identity={identity}
        onIdentityChange={setIdentity}
        role={session?.role ?? null}
        view={view}
        onViewChange={setView}
      />
      <main className="app-main">
        {!session ? (
          <div className="app-loading">Loading…</div>
        ) : view === "chat" ? (
          <ChatView sessionId={session.session_id} />
        ) : (
          <OpsDashboard sessionId={session.session_id} />
        )}
      </main>
    </div>
  );
}
