# ParcelPilot AI Support Agent

An AI support agent for ParcelPilot: a Gemini-powered chat assistant (with document search,
structured-data lookups, and confirm-first escalations) plus a proactive issue-detection job
and internal ops dashboard.

See also: [`docs/architecture.md`](docs/architecture.md), [`docs/product.md`](docs/product.md),
[`docs/ai_tool_usage.md`](docs/ai_tool_usage.md).

## Stack

- **Backend:** FastAPI (Python, async), SQLite, ChromaDB (persistent, local), Gemini
  (`google-genai`, function calling), PyMuPDF for PDF parsing.
- **Frontend:** React + TypeScript (Vite), plain CSS, no UI framework.
- **No LangGraph/CrewAI/ADK** — the agent loop is a plain send → check `function_call` →
  execute tool → send `function_response` → repeat loop (see `backend/app/agent.py`).

## Prerequisites

- Python 3.12 (3.13/3.14 currently break some pinned wheels for this project — see
  Troubleshooting below if `pip install` fails on your machine)
- Node.js 18+
- A Gemini API key: https://aistudio.google.com/apikey

## 1. Get the data pack

Download the 6 policy/agreement PDFs and `ParcelPilot_Assessment_Data.xlsx` from the
candidate Drive folder and place them in a `data/` folder at the repo root:

```
data/
  01_Support_Policy_v3_CURRENT.pdf
  02_Support_Policy_v2_DEPRECATED.pdf
  03_Cancellation_and_Service_Credit_SOP_v4.pdf
  04_Product_Operations_Guide_and_Known_Issues.pdf
  05_Northstar_Logistics_Enterprise_Agreement.pdf
  06_LumenWorks_Service_Agreement.pdf
  ParcelPilot_Assessment_Data.xlsx
```

`data/` is gitignored (not committed) — you must (re)download it before running ingestion.

## 2. Backend setup

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set GEMINI_API_KEY

python -m app.seed      # loads accounts/orders/tickets into SQLite
python -m app.ingest     # parses the 6 PDFs, embeds them, stores in ChromaDB

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (`GET /api/health` to check). Seeding and
ingestion also run automatically on startup if the DB/vector store are empty, so the two
manual commands above are optional but recommended the first time (clearer error messages).

Re-running `python -m app.seed` or `python -m app.ingest` is safe — both are idempotent
(upsert by primary key / `doc_id`, never duplicate rows or vectors).

### Environment variables

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | **Required.** Gemini API key. |
| `GEMINI_MODEL` | Chat/function-calling model (default `gemini-3.6-flash`). |
| `GEMINI_EMBEDDING_MODEL` | Embedding model (default `gemini-embedding-001`). |
| `SNAPSHOT_TIME` | Reference "now" for SLA/cancellation-window logic — the data pack's stated snapshot time, not the wall clock. |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins. |
| `TOKEN_SECRET` | HMAC secret for signing escalation-confirmation tokens. Set a real random value in production. |

### Run the backend tests

```bash
cd backend
.venv/bin/pytest -q
```

Covers every function-level test case in the assessment's Section 7 (`SD-*`, `QD-*`,
`CE-*`, `TV-*`, `PD-*`, `SP-*`, `EH-*`), plus a couple of live agent-loop checks (`AL-*`)
that call the real Gemini API — those are skipped automatically if the API key's free-tier
quota is exhausted rather than failing the suite.

## 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL, defaults to http://localhost:8000
npm run dev
```

Open `http://localhost:5173`. Use the "Viewing as" switcher in the top bar to demo access
scoping across the 4 seeded accounts and the internal/ops role.

## How sessions work (mock auth)

There's no real login: picking an identity in the switcher *is* the auth step, so access
scoping is easy to demo live. Session ids are deterministic per identity
(`session-<account_id>` / `session-internal-ops`), so refreshing the page reconnects to the
same persisted conversation for whichever identity is currently selected.

## Architecture at a glance

```
Client → mock-auth session → Gemini agent loop (context-isolated retrieval)
       → tool-call validator (schema check + forced account_id)
       → search_documents / query_structured_data / create_escalation
       → vector store / SQL database / escalations table (write only after confirm)

Scheduled/on-demand job → same SQL database → flagged_issues table → ops dashboard
```

Full detail in [`docs/architecture.md`](docs/architecture.md).

## Uploading additional documents (Internal Team → Documents)

Beyond the fixed data pack, Internal Team sessions can upload new PDFs through the
**Documents** tab: pick a doc type, current/deprecated status, and an optional
account-scope, then upload. The file is parsed with PyMuPDF, chunked by page, embedded,
and upserted into the same ChromaDB collection `search_documents` queries — so it's
immediately usable in chat, with the same source-authority rules as the seeded docs
(`agreement` → highest authority, `deprecated` → lowest). Not part of the assessment's
minimum requirements; added per its "feel free to add more data" allowance. Uploaded
files are stored in `backend/uploads/` (gitignored).

## Manually running the proactive-detection job

```bash
curl -X POST "http://localhost:8000/api/ops/run-detection?session_id=session-internal-ops"
curl "http://localhost:8000/api/ops/flagged-issues?session_id=session-internal-ops"
```

(Or use the "Run detection now" button on the Ops Dashboard screen, viewing as Internal.)

## Troubleshooting

- **`pip install` fails building `pydantic-core`/`tokenizers` wheels:** your Python version
  is too new for some pinned dependencies' prebuilt wheels. Install Python 3.12
  (`brew install python@3.12` on macOS) and recreate the venv with
  `/opt/homebrew/bin/python3.12 -m venv .venv` (or your platform's 3.12 path).
- **Gemini calls fail with `RESOURCE_EXHAUSTED` / 429:** the free tier caps requests per
  day per model. Wait for the quota to reset or use a billed key.
- **CORS errors in the browser:** make sure `CORS_ORIGINS` in `backend/.env` includes the
  exact origin the frontend is served from.

## Known simplifications (see `ponytail:` comments in the code for more)

- Business-hour SLA math treats hours as literal (doesn't skip nights/weekends).
- Known-issue tagging and ticket severity classification are keyword heuristics, not ML.
- Northstar's monthly INR 5,000 service-credit aggregate cap is not tracked/enforced.
- Streaming sends the final answer progressively after tool calls resolve, rather than
  true token-by-token generation streamed through the tool-calling loop.
