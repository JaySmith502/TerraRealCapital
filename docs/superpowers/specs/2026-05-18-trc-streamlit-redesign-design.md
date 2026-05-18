# Terra Real Capital Research Tool — Streamlit Redesign (Design Spec)

- **Date:** 2026-05-18
- **Status:** Approved design, ready to convert to implementation plan
- **Supersedes:** the architecture in `docs/superpowers/plans/2026-04-28-trc-research-tool.md` (React SPA + Node scanner + 4-source fan-out). That plan's product intent stands; its tech architecture is replaced by this document.

## 1. Why this change

The original plan specified a Vite + React SPA on Vercel, a Node/Express scanner microservice on Railway, a 4-source external-API fan-out (BLS / Census / HUD / USASpending), and Supabase Auth + Realtime. For an internal tool used by 3–4 people, that is more moving parts, languages, and infrastructure than the problem needs. No code had been written, so changing direction is free.

This redesign collapses the system to a single Python Streamlit application backed by Supabase Postgres, and replaces the 4-source fan-out with one Perplexity research call plus one Claude writing call.

## 2. Locked decisions

| Decision | Choice |
|---|---|
| Frontend + backend | One Python Streamlit app (no Node, no React, no separate microservice) |
| Data source | Single Perplexity Sonar API call (research, prose + citations) |
| Report generation | Single Claude API call, dual-output (strict JSON metrics + Markdown narrative), prompt caching on system prompt |
| Report shape | Dual-output kept as originally specced; numeric metrics are "Perplexity-cited", not API-authoritative |
| Persistence | Supabase Postgres (data only) |
| Auth | Single shared app password via `st.secrets`; no Supabase Auth, no RLS, no per-user identity |
| Scan execution | Synchronous, blocking, with `st.status` step updates; no `report_events`, no Realtime; row written only on full success |
| Section regenerate | Section selector (split by Markdown headings) + optional instruction box + Regenerate button; Claude rewrites one section, spliced back into the in-session buffer; persisted only on explicit Save |
| Markdown editing | `st.text_area` + live `st.markdown` preview; no MDXEditor / 3rd-party editor |
| Newsletter export | `st.code(markdown)` (built-in copy button) |
| Hosting | Streamlit Community Cloud (Supabase stays managed) |
| Testing | TDD with pytest + respx on all non-UI modules; UI by manual browser smoke |
| Model verification | Perplexity Sonar model + request schema doc-verified at plan-writing time, not written from memory |

## 3. Architecture

```
Streamlit app  ──password gate──►  Scanner / Report Editor / Library pages
      │
      ├─ Perplexity Sonar API   1 call: research the selected city's
      │                         multifamily / economic / capital-flow signals
      │                         (returns prose + citations)
      ├─ Anthropic Claude API   1 call: dual-output -> strict JSON
      │                         (metrics/signals/capital_flows/submarkets/evidence)
      │                         + long-form Markdown narrative; prompt caching
      │                         on the system prompt
      └─ Supabase Postgres      service-role key, server-side only:
                                cities, reports, api_cache
```

The Supabase service-role key lives only in Streamlit server-side secrets and never reaches a browser. The app password is the only access gate.

## 4. Data model (Supabase)

- **`cities`** — unchanged from the original plan: 16 Midwest metros with `name`, `state`, `fips_county`, `fips_metro`, `lat`, `lng`.
- **`reports`** — keep `metrics`, `signals`, `capital_flows`, `submarkets`, `evidence`, `metrics_extra` (jsonb); `narrative_raw`, `narrative_edited` (text); `tags` (text[]); `status` (enum); `scan_date` (date); timestamps. **Removed:** `created_by`, `edited_by`, and their `auth.users` foreign keys (no per-user identity); the `error` column (no failed rows are ever written — see §5). The `status` enum is reduced to `('ready', 'edited')`: a row is `ready` on creation and `edited` once a user saves any change. `scanning`/`failed`/`published` states are dropped (scan is synchronous and only persists on success; publishing is out of v1). `metrics_extra` is the catch-all jsonb bucket for any additional metrics Claude emits that do not fit the named buckets; the StructuredPanel renders it generically at the end.
- **`api_cache`** — kept but slim. Caches only the Perplexity research call, keyed `(source='perplexity', geo_id=<city FIPS>, period=<scan_date>)`, so re-scanning a city on the same day does not re-pay Perplexity. Claude output is not cached.
- **Removed entirely:** the `report_events` table, all RLS policies, and any Realtime usage.

## 5. Scan flow (synchronous)

1. On the Scanner page the user selects a city and toggles which signals to emphasise.
2. User clicks **Scan**. The script runs the pipeline inline inside an `st.status` block that shows live steps: "Researching via Perplexity…", "Writing report with Claude…", "Saving…".
3. Orchestrator, entirely in memory: read-through `api_cache` for the Perplexity call → call Perplexity → call Claude with the research as input, producing dual output → parse and validate the JSON half. Only after all of that succeeds does it write one `reports` row (`status='ready'`).
4. On success the app navigates to the Report Editor for that report.

**Failure behavior:** if any step fails (Perplexity error, Claude error, JSON validation failure, or the final DB write), no `reports` row is created — there are no partial or `failed` rows. The `st.status` block is marked error state and a compact human-readable error is shown in the UI (full exception logged server-side). The user fixes the condition (or retries) and re-runs the scan.

One scan per session; the page blocks until done (~30–60s). Acceptable for 3–4 internal users running occasional scans. If the tab closes mid-scan, the scan is lost (re-run it; nothing is persisted until success).

## 6. Screens

1. **Login** — single shared password from `st.secrets`, success held in `st.session_state`; gates all other pages.
2. **Scanner** — city picker + signal toggles + Scan button (drives the flow in §5).
3. **Report Editor**
   - Read-only **StructuredPanel**: renders `metrics` / `signals` / `capital_flows` (and submarkets/evidence) from the jsonb columns, plus a generic render of `metrics_extra` at the end.
   - Narrative editor: `st.text_area` bound to an in-session copy of `narrative_edited`, with a live `st.markdown` preview shown side-by-side.
   - **Section regenerate**: narrative split by Markdown headings into sections; a `selectbox` lists them; user picks one, optionally types an instruction ("make it punchier"), clicks Regenerate; Claude rewrites just that section and it is spliced back into the in-session narrative buffer. The regenerated text is **not** auto-persisted — it becomes part of the unsaved edit buffer and is written to Supabase only when the user clicks Save (same model as manual text edits).
   - Tags input.
   - **Copy Markdown** via `st.code(narrative)` (Streamlit's built-in copy-to-clipboard).
   - Save — writes the in-session `narrative_edited` / `tags` back to Supabase and sets `status='edited'`.
4. **Library** — list reports with filters (city, status, date, tags), open a report into the Editor, empty state when none.

## 7. Phase remap

The original 7-phase / 42-task plan becomes leaner:

- **P0 Repo setup** — git, Python `.gitignore`, README, Python 3.12 + `uv`/venv.
- **P1 Supabase foundation** — create project; schema migration for `cities`, `reports`, `api_cache` (no `report_events`, no RLS, no auth FKs, no `error` column, reduced status enum); seed 16 cities. The original "generate TypeScript types" task is replaced by pydantic models in code.
- **P2 Scan pipeline (TDD: pytest + respx)** — config loader (pydantic-settings), Supabase client, Perplexity client, Claude dual-output client, cache layer, orchestrator, prompts (system + regenerate). Replaces the original 14-task Node Phase 2 (no four source clients, no progress emitter).
- **P3 Streamlit shell** — app entry, password gate, page navigation, Supabase data-access helpers, session state.
- **P4 Scanner screen** — city picker + signal toggles; synchronous scan with `st.status`.
- **P5 Report Editor screen** — StructuredPanel, editor + live preview, section regenerate, tags, copy-markdown, save.
- **P6 Library screen** — list + filters + open + empty state.
- **P7 Deploy + e2e smoke** — push to GitHub, deploy on Streamlit Community Cloud, set secrets, end-to-end smoke test.

## 8. Testing strategy

- TDD (pytest + respx for HTTP mocking) on all non-UI modules: config, Supabase access, Perplexity client, Claude client, cache, orchestrator, narrative section-splitting/splicing, parsers.
- Streamlit UI verified by manual browser smoke testing (the original plan already treated UI this way).

## 9. Out of v1 (unchanged from original intent)

Watchlist dashboard, Comparison view, Diff view, Newsletter assembly, Charts, Settings UI, Beehiiv API direct publishing, PDF export, mobile-optimized layout, automated E2E tests, per-user identity/roles.

## 10. To verify at plan-writing time

- Exact Perplexity Sonar model name and request/response schema (against Perplexity official docs).
- Anthropic `claude-sonnet-4-6` dual-output prompt structure and prompt-caching block placement (against Anthropic docs).
- Streamlit Community Cloud secrets handling for the Supabase service-role key and app password.
