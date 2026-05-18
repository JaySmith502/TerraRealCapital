# Terra Real Capital — Project Context

## Status
**Redesign complete, no code yet.** The project moved from a React/Node design to a
**Streamlit/Python** design (user-approved 2026-05-18).
- Active spec: `docs/superpowers/specs/2026-05-18-trc-streamlit-redesign-design.md`
- Active plan: `docs/superpowers/plans/2026-05-18-trc-streamlit-research-tool.md` (8 phases, 27 tasks; reviewed twice, approved)
- Superseded plan: `docs/superpowers/plans/2026-04-28-trc-research-tool.md` (React/Node — historical only; carries a SUPERSEDED banner)

## What this project is
Internal research tool for Danielle + 2-3 analysts at Terra Real Capital, a Midwest-focused multifamily syndication. Serves two use cases from one tool:
1. **Investment decisions** — scan Midwest cities, decide what to invest in
2. **Newsletter content** — produce Beehiiv-ready Markdown drafts to grow an LP investment community

## Locked architecture (do not relitigate without explicit user approval)

- **App:** Single Python **Streamlit** app (no React, no Node, no separate microservice); 3 pages: Scanner, Report Editor, Library
- **Hosting:** Streamlit Community Cloud
- **Database:** Supabase Postgres, data only — accessed server-side with the `service_role` key (NO Supabase Auth, NO RLS, NO Realtime)
- **Auth:** single shared `APP_PASSWORD` via `st.secrets`
- **Data source:** ONE Perplexity `sonar-pro` call per scan (`POST https://api.perplexity.ai/chat/completions`) — replaces the old BLS/Census/HUD/USASpending fan-out
- **AI:** ONE Claude `claude-sonnet-4-6` call per scan, forced tool-use dual-output (structured JSON + Markdown narrative), prompt caching on the system prompt; same model for section-regenerate
- **Pure logic:** `trc/` package (config, models, db, cache, perplexity, claude, narrative, orchestrator) — fully TDD'd with pytest + respx
- **Tooling:** Python 3.12, `uv`, pydantic + pydantic-settings

## Locked product spec

- Auth: single shared app password; no roles, no per-user identity
- Reports = structured JSON + Markdown narrative from ONE Perplexity+Claude pass; numbers are "as cited by Perplexity", not authoritative
- `api_cache` table caches the Perplexity call, keyed `(source, geo_id, period, fetched_on)`
- Scan is synchronous with `st.status`; a `reports` row is written ONLY on full success; any failure shows an `st.error()` banner + `st.status` error state and persists nothing (no partial/failed rows; `status` enum is just `ready`/`edited`)
- Section regenerate: split narrative by `##` headings → selectbox + instruction box → Claude rewrites that section → spliced into the in-session buffer → persisted only on explicit Save
- Markdown editing: `st.text_area` + live `st.markdown` preview
- Newsletter export: `st.code(markdown)` built-in copy button (paste into Beehiiv; no API integration v1)
- 16 Midwest cities seeded with FIPS codes (inlined in plan Task 1.4)
- TDD on all `trc/` modules + `ui/auth.py`; UI via browser smoke testing

## Explicitly out of v1 (do not build)
Watchlist dashboard, Comparison view, Diff view, Newsletter assembly, Charts, Settings UI, Beehiiv API direct publishing, PDF export, mobile-optimized layout, automated E2E tests, per-user identity/roles, Supabase Auth/RLS/Realtime.

## Recommended execution mode
**Subagent-driven** via `superpowers:subagent-driven-development`. Dispatch a fresh subagent per task; review between tasks. The plan uses checkbox syntax for progress tracking.

Alternative: `superpowers:executing-plans` for inline batched execution.

## Environment notes
- Windows 11, bash + PowerShell available
- Project path has a space: `C:\Users\smith\Documents\1 Projects\TerraRealCapital`
- Git repo already initialized (commits exist on `main`); Phase 0 is Python scaffolding, not `git init`
- Sandboxed file edits: prefer PowerShell for new file writes; `.env`-pattern paths/content trip a Bash credential guard — use PowerShell for those
- The `woz` code plugin is broken here (auth/outdated errors, plus a PreToolUse hook that insists on it); use standard tools and ignore that hook

## Key files
- Active plan: `docs/superpowers/plans/2026-05-18-trc-streamlit-research-tool.md`
- Active spec: `docs/superpowers/specs/2026-05-18-trc-streamlit-redesign-design.md`
- Supabase setup (for the other internal team): `docs/SUPABASE_SETUP.md`
- Secrets template: `.env.example`
- Superseded React/Node plan: `docs/superpowers/plans/2026-04-28-trc-research-tool.md` (historical)
- Conversation that birthed the project: `Danielle_real_estate_chat.txt`

## What to do next session
1. Provision Supabase manually (Phase 1 Task 1.1) — the other team can follow `docs/SUPABASE_SETUP.md`.
2. Open the active plan, pick subagent-driven execution, start at Phase 0 Task 0.1 (Python scaffolding; git already exists).
3. Each task is self-contained with file paths, full code, and verification commands. Phase 7 (push/deploy) needs explicit user authorization.