import type { AccountOption } from "../api";
import type { ViewName } from "../types";

interface Props {
  accounts: AccountOption[];
  identity: string;
  onIdentityChange: (identity: string) => void;
  role: "customer" | "internal" | null;
  view: ViewName;
  onViewChange: (view: ViewName) => void;
}

export function TopBar({ accounts, identity, onIdentityChange, role, view, onViewChange }: Props) {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="topbar-logo">📦</span> ParcelPilot
      </div>

      <div className="topbar-controls">
        <label className="switcher">
          <span>Viewing as</span>
          <select value={identity} onChange={(e) => onIdentityChange(e.target.value)}>
            {accounts.map((a) => (
              <option key={a.account_id} value={a.account_id}>
                {a.account_name}
              </option>
            ))}
            <option value="internal">Internal — Ops</option>
          </select>
        </label>

        {role && <span className={`role-pill role-${role}`}>{role === "internal" ? "Internal" : "Customer"}</span>}

        {role === "internal" && (
          <nav className="view-tabs">
            <button className={view === "chat" ? "active" : ""} onClick={() => onViewChange("chat")}>
              Chat
            </button>
            <button className={view === "ops" ? "active" : ""} onClick={() => onViewChange("ops")}>
              Ops Dashboard
            </button>
          </nav>
        )}
      </div>
    </header>
  );
}
