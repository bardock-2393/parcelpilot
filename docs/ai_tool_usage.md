# AI Tool Usage Note

## Tool used

**Claude Code** (Anthropic's agentic CLI) was used for effectively the entire build, in a
single driven session against `everthing.md` as the spec. This is a direct account of how,
not a reconstruction after the fact.

## How it was used

1. **Data acquisition**: downloaded the candidate data pack directly from the shared Drive
   folder (via `gdown`, since it's a public folder) rather than asking for it manually.
2. **Data exploration before building**: read every PDF's actual text and dumped every sheet
   of the xlsx *before* writing any schema or business logic — the account-specific
   cancellation/service-credit terms, the known-issue IDs, the severity/SLA tables, and the
   "some historical resolutions may be wrong" README note all came from that read, not from
   assumptions.
3. **Backend build**: FastAPI app, SQLite schema, ChromaDB ingestion, the 3 tools, the
   validator, the Gemini agent loop, the confirmation-token flow, and the detection job were
   written directly as files, then exercised against the *real* Gemini API (not mocked) to
   verify behavior — including catching and fixing two real integration issues along the way
   (see below).
4. **Frontend build**: React + TypeScript app scaffolded via Vite, chat UI with SSE
   streaming, escalation confirm/cancel cards, and the ops dashboard, written directly.
5. **Test suite**: pytest tests written to mirror the assessment's own function-level test
   table (Section 7) one-for-one by ID (`SD-1`..`SD-6`, `QD-1`..`QD-7`, etc.), then run for
   real — one bug was caught and fixed this way (see below).
6. **Manual verification against the brief's own test scripts**: several of Section 6's
   scripted test cases (1.1 agreement-overrides-SOP, 2.1/2.2 cross-account blocking, 3.1
   prompt injection, 5.1/5.2 confirm-then-replay) were run against the live running backend
   via `curl`, not just asserted in unit tests, before being called done.

## Real issues Claude Code found and fixed while building (not hypothetical)

- **Dependency/runtime mismatch**: the pinned `google-genai==0.7.0` SDK predates the
  `gemini-3.6-flash` model's requirement to round-trip a `thought_signature` on function
  calls; the first live test failed with a 400 error. Diagnosed from the actual error
  message and fixed by upgrading to the current SDK (`2.19.0`), not by guessing.
- **Deprecated/renamed models**: `gemini-2.0-flash` and `text-embedding-004` (both named in
  the original spec) return 404 against the live API; found via a direct API call and
  swapped for `gemini-3.6-flash` / `gemini-embedding-001`.
- **A real filtering bug**: `search_documents` initially let an unscoped (internal, no
  account) query surface *any* account's agreement whenever it happened to rank well — the
  `SD-1` unit test (adapted directly from the assessment's own test table) caught this
  before it shipped, and the fix was to always filter to public-only docs when no account
  context is present.
- **Python 3.14 incompatibility**: several pinned wheels (pydantic-core, tokenizers) don't
  yet build on the system's default Python 3.14; resolved by installing 3.12 via Homebrew
  rather than downgrading dependency versions blindly.

## What was not verified by AI, and needs a human pass

- Frontend visual/UX review in an actual browser (the browser-automation tool wasn't
  available this session) — layout was type-checked and production-built successfully, but
  not click-tested end to end visually.
- Hosted deployment, the demo video, and the submission form are outside what a coding
  session produces — see `docs/product.md`'s "what was left out."
