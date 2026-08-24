import { useEffect, useRef, useState } from "react";
import { api, type ChatMessage, type EscalationDraft } from "../api";
import { ToolBadges } from "./ToolBadges";
import { EscalationCard, EscalationResultBadge } from "./EscalationCard";
import { Markdown } from "./Markdown";

interface LocalMessage extends ChatMessage {
  escalationDraft?: EscalationDraft;
  escalationState?: "created" | "cancelled";
  escalationId?: string;
  isError?: boolean;
}

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function ChatView({ sessionId }: { sessionId: string }) {
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([]);
    api
      .history(sessionId)
      .then((history) => setMessages(history.map((h) => ({ ...h }))))
      .catch(() => setMessages([]));
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setSending(true);
    setMessages((m) => [...m, { role: "user", content: text, tool_calls: [], created_at: "" }]);
    setMessages((m) => [...m, { role: "model", content: "", tool_calls: [], created_at: "" }]);

    try {
      const res = await fetch(`${API_URL}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      });
      if (!res.body) throw new Error("No response stream");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let full = "";

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const raw of events) {
          const eventMatch = raw.match(/^event: (\w+)/m);
          const dataMatch = raw.match(/^data: (.*)$/m);
          if (!eventMatch || !dataMatch) continue;
          const payload = JSON.parse(dataMatch[1]);
          if (eventMatch[1] === "token") {
            full += payload.text;
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1] = { ...copy[copy.length - 1], content: full };
              return copy;
            });
          } else if (eventMatch[1] === "done") {
            setMessages((m) => {
              const copy = [...m];
              const last = { ...copy[copy.length - 1] };
              last.tool_calls = payload.tool_calls;
              last.escalationDraft = payload.escalation_draft ?? undefined;
              last.isError = !payload.escalation_draft && /escalat/i.test(last.content);
              copy[copy.length - 1] = last;
              return copy;
            });
          } else if (eventMatch[1] === "error") {
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1] = { ...copy[copy.length - 1], content: payload.message, isError: true };
              return copy;
            });
          }
        }
      }
    } catch {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = {
          ...copy[copy.length - 1],
          content: "I'm having trouble reaching the assistant right now. Please try again.",
          isError: true,
        };
        return copy;
      });
    } finally {
      setSending(false);
    }
  }

  function resolveEscalation(index: number, state: "created" | "cancelled", escalationId?: string) {
    setMessages((m) => {
      const copy = [...m];
      copy[index] = { ...copy[index], escalationState: state, escalationId };
      return copy;
    });
  }

  return (
    <div className="chat-view">
      <div className="chat-scroll" ref={scrollRef}>
        {messages.map((msg, i) => (
          <div key={i} className={`message-row ${msg.role}`}>
            <div className={`message-bubble ${msg.role} ${msg.isError ? "amber" : ""}`}>
              {msg.role === "model" ? (
                msg.content ? <Markdown content={msg.content} /> : sending && i === messages.length - 1 ? "…" : ""
              ) : (
                msg.content
              )}
            </div>
            {msg.role === "model" && <ToolBadges tools={msg.tool_calls} />}
            {msg.role === "model" && msg.escalationDraft && !msg.escalationState && (
              <EscalationCard
                sessionId={sessionId}
                draft={msg.escalationDraft}
                onResolved={(state, id) => resolveEscalation(i, state, id)}
              />
            )}
            {msg.role === "model" && msg.escalationState && (
              <EscalationResultBadge state={msg.escalationState} escalationId={msg.escalationId} />
            )}
          </div>
        ))}
        {messages.length === 0 && (
          <div className="chat-empty">Ask about an order, a policy, or a ticket to get started.</div>
        )}
      </div>

      <div className="chat-input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask ParcelPilot support…"
          disabled={sending}
        />
        <button className="btn-primary" onClick={send} disabled={sending || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
