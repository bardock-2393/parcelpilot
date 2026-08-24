# Product Note

## Chosen extra problem: proactive issue detection

Of the optional directions implied by the brief, I built out the **internal ops /
proactive-detection** path (Path B in the architecture diagram) rather than, say, deeper
personalization or a richer chat UI: a scheduled/on-demand job that reads the same
tickets/orders tables the chat agent reads and flags three things —

1. **Complaint spikes** — 3+ open tickets in a 3-day window matching the same known-issue
   tag from the Product Operations Guide.
2. **SLA breaches / near-breaches** — computed against each account's actual first-response
   target (agreement override where one exists, else the plan default from the current
   Support Policy), using the data pack's stated snapshot time as "now," not the wall clock.
3. **Multi-account patterns** — the same known issue reported by 2+ different accounts,
   which is a stronger signal than any single account's complaint volume.

**Why this one:** the chat agent is inherently reactive — it only ever sees what a customer
asks. The proactive job is where the product actually gets ahead of the ticket queue instead
of just answering it faster, and it reuses 100% of the existing data layer (no new ingestion
pipeline), so it was cheap to add well rather than bolt on.

## Roadmap ideas (not built, natural next steps)

- **Real severity classification**: the current tagger is a keyword heuristic
  (`ponytail:` noted in `detection.py`) — swap for a small classifier or an LLM call once
  ticket volume outgrows a keyword list.
- **Aggregate service-credit caps**: Northstar's INR 5,000/month cap isn't tracked; would
  need a rolling-window sum over `escalations`/credits actually paid out, not just computed.
- **Business-hour-aware SLA math**: current calculation treats "business hours" as literal
  hours; real business-hours/weekend-skipping logic would tighten SLA accuracy.
- **Dashboard → chat handoff**: clicking a flagged issue pre-fills a chat query about it
  (explicitly called out as optional/nice-to-have in the brief; not built).
- **True token streaming**: stream Gemini's generation itself rather than the resolved
  final answer (see architecture note's trade-offs section).
- **Real auth**: mock auth was the right call for a scoped demo; a real deployment needs
  actual login, not an identity switcher.

## What was left out

- The optional Screen 3 (dedicated trace/audit viewer UI) — the brief explicitly marks it
  as skippable in favor of querying `agent_traces` directly, which the `/api/ops/trace`
  endpoint already exposes for that purpose.
- Hosted deployment (Vercel/Railway/Supabase) — not completed within this session; see the
  README for local run instructions. [Update this note once deployed.]
- Demo video and submission form — outside what this session produced; see AI-tool-usage
  note for scope of what was and wasn't automated.

## Success metric

**% of chat turns where the agent's answer both cites a specific source document (or order/
ticket ID) *and* the citation is verifiably correct against `agent_traces`** — this is the
single metric that most directly measures the "trust and reliability" goal the brief cares
about (Section 6, Tests 8.1/8.2): a fast wrong answer is worse than a slower correct one for
a support agent making cancellation/credit decisions, so groundedness-with-traceability is a
better north star than raw response latency or ticket-deflection rate.
