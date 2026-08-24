import type { AccountOption } from "../api";
import type { ViewName } from "../types";

interface Props {
  accounts: AccountOption[];
  identity: string;
  onIdentityChange: (identity: string) => void;
  onSelectCustomerMode: () => void;
  role: "customer" | "internal" | null;
  view: ViewName;
  onViewChange: (view: ViewName) => void;
}

export function TopBar({ accounts, identity, onIdentityChange, onSelectCustomerMode, role, view, onViewChange }: Props) {
  const isInternal = identity === "internal";

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="topbar-logo">📦</span> ParcelPilot
      </div>

      <div className="topbar-controls">
        <nav className="mode-tabs">
          <button className={!isInternal ? "active" : ""} onClick={onSelectCustomerMode}>
            Customer
          </button>
          <button className={isInternal ? "active" : ""} onClick={() => onIdentityChange("internal")}>
            Internal Team
          </button>
        </nav>

        {!isInternal && (
          <select className="account-select" value={identity} onChange={(e) => onIdentityChange(e.target.value)}>
            {accounts.map((a) => (
              <option key={a.account_id} value={a.account_id}>
                {a.account_name}
              </option>
            ))}
          </select>
        )}

        {role === "internal" && (
          <nav className="view-tabs">
            <button className={view === "chat" ? "active" : ""} onClick={() => onViewChange("chat")}>
              Chat
            </button>
            <button className={view === "ops" ? "active" : ""} onClick={() => onViewChange("ops")}>
              Ops Dashboard
            </button>
            <button className={view === "docs" ? "active" : ""} onClick={() => onViewChange("docs")}>
              Documents
            </button>
          </nav>
        )}
      </div>
    </header>
  );
}
