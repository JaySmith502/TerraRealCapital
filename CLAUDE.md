# Terra Real Capital — Project Context

## Status
**Plan complete, no code yet.** Implementation plan at `docs/superpowers/plans/2026-04-28-trc-research-tool.md` (7 phases, 42 tasks). Plan has been reviewed and 7 issues fixed.

## What this project is
Internal research tool for Danielle + 2-3 analysts at Terra Real Capital, a Midwest-focused multifamily syndication. Serves two use cases from one tool:
1. **Investment decisions** — scan Midwest cities, decide what to invest in
2. **Newsletter content** — produce Beehiiv-ready Markdown drafts to grow an LP investment community

## Locked architecture (do not relitigate without explicit user approval)

- **Frontend:** Vite + React + TypeScript + Tailwind v4 + shadcn/ui SPA on Vercel
- **Backend:** Node + Express + TypeScript scanner microservice on Railway
- **Database/Auth/Realtime:** Supabase (Postgres + magic-link Auth + Realtime)
- **AI:** Claude `claude-sonnet-4-6` for both initial scan and section-regenerate, prompt caching on system prompt
- **Editor:** MDXEditor for Markdown narrative
- **State:** TanStack Query for server state; Supabase JS client for direct DB access
- **External data sources:** BLS (employment), Census ACS (population), HUD (FMR), USASpending (federal awards)

## Locked product spec

- Auth: Supabase magic-link, no roles
- Reports = structured JSON metrics + Markdown narrative produced from a SINGLE Sonnet call
- External-API caching via `api_cache` table keyed by `(source, geo_id, period, fetched_on)`
- Section regenerate: highlight paragraph -> floating popover -> Sonnet rewrite
- v1 screens: Login, Scanner, Report Editor, Library
- Newsletter export: copy Markdown to clipboard, paste into Beehiiv (no API integration v1)
- 16 Midwest cities seeded with FIPS codes
- TDD on all server-side modules; UI via smoke testing in browser

## Explicitly out of v1 (do not build)
Watchlist dashboard, Comparison view, Diff view, Newsletter assembly, Charts, Settings UI, Beehiiv API direct publishing, PDF export, mobile-optimized layout, Playwright E2E tests.

## Recommended execution mode
**Subagent-driven** via `superpowers:subagent-driven-development`. Dispatch a fresh subagent per task; review between tasks. The plan uses checkbox syntax for progress tracking.

Alternative: `superpowers:executing-plans` for inline batched execution.

## Environment notes
- Windows 11, bash + PowerShell available
- Project path has a space: `C:\Users\smith\Documents\1 Projects\TerraRealCapital`
- Greenfield: no git repo initialized yet (Task 0.1 does this)
- Sandboxed file edits: prefer PowerShell for new file writes; `.env`-pattern content trips a Bash credential guard

## Key files (when they exist)
- Plan: `docs/superpowers/plans/2026-04-28-trc-research-tool.md`
- Conversation that produced the plan: `Danielle_real_estate_chat.txt` (the original chat with Claude that birthed the project)

## What to do next session
Open the plan, pick subagent-driven execution, start with Phase 0 Task 0.1 (initialize git repo). Each task in the plan is self-contained with file paths, code snippets, and verification commands.