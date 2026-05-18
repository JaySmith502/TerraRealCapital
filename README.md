# Terra Real Capital — Research Tool

Internal Streamlit app for Danielle + analysts at Terra Real Capital. Scans Midwest multifamily markets and produces investment reports and Beehiiv-ready newsletter drafts.

**How a scan works:** one Perplexity `sonar-pro` call fetches city data → one Claude `claude-sonnet-4-6` call produces dual output (structured JSON + Markdown narrative) → persisted to Supabase.

## Layout

```
trc/          Pure logic (config, models, db, cache, perplexity, claude, orchestrator) — fully TDD'd
ui/           Shared Streamlit UI components (auth, etc.)
app/          Streamlit multi-page app (Home.py + pages/)
supabase/     SQL migrations
tests/        pytest suite (mirrors trc/ and ui/)
docs/         Spec, plan, and setup guides
```

## Quick start

```bash
uv sync                          # install deps + create .venv
cp .env.example .streamlit/secrets.toml   # fill in real keys
uv run pytest                    # run test suite
uv run streamlit run app/Home.py # launch the app
```

## Key docs

- **Spec:** `docs/superpowers/specs/2026-05-18-trc-streamlit-redesign-design.md`
- **Plan:** `docs/superpowers/plans/2026-05-18-trc-streamlit-research-tool.md`
- **Supabase setup:** `docs/SUPABASE_SETUP.md`

## Tech stack

- Python 3.12, `uv`, Streamlit (Community Cloud)
- Supabase Postgres (service role key, no Auth/RLS)
- Perplexity sonar-pro + Anthropic claude-sonnet-4-6
- pydantic-settings, httpx, pytest + respx
