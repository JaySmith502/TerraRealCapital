# Terra Real Capital Research Tool (Streamlit) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an internal Streamlit tool for Danielle + team that researches a Midwest city via one Perplexity call, turns it into a dual-output report (structured JSON + Beehiiv-ready Markdown) via one Claude call, and persists everything to Supabase.

**Architecture:** A single Python Streamlit app, password-gated, with three pages (Scanner, Report Editor, Library). A pure `trc/` package holds all non-UI logic (config, models, Supabase access, Perplexity client, Claude client, narrative split/splice, orchestrator) and is fully unit-tested with TDD. The scan runs synchronously inside `st.status`; a row is written to Supabase only on full success, and any failure produces a frontend error notification.

**Tech Stack:** Python 3.12, `uv`, Streamlit, `httpx` (Perplexity), `anthropic` SDK (Claude `claude-sonnet-4-6`, prompt caching + forced tool-use), `supabase` (service-role), `pydantic` + `pydantic-settings`, `pytest` + `respx`. Supabase Postgres (data only). Hosted on Streamlit Community Cloud.

**Supersedes:** the React/Node architecture in `docs/superpowers/plans/2026-04-28-trc-research-tool.md`. Authoritative design: `docs/superpowers/specs/2026-05-18-trc-streamlit-redesign-design.md`.

---

## Reference Spec (locked)

| Decision | Choice |
|---|---|
| App | One Python Streamlit app, no Node/React, no microservice |
| Data source | One Perplexity `sonar-pro` call (`POST https://api.perplexity.ai/chat/completions`) |
| Report gen | One Claude `claude-sonnet-4-6` call, forced tool-use dual-output, prompt caching on system prompt |
| Persistence | Supabase Postgres (service-role key, server-side only) |
| Auth | Single shared app password via `st.secrets` |
| Scan | Synchronous + `st.status`; row written only on full success; failure -> `st.status` error + `st.error()` banner |
| Regenerate | Section selector (split by Markdown headings) + instruction box; persisted on explicit Save |
| Editing | `st.text_area` + live `st.markdown` preview |
| Export | `st.code(markdown)` (built-in copy) |
| Hosting | Streamlit Community Cloud |
| Testing | TDD (pytest + respx) on all `trc/` modules; UI by manual browser smoke |
| Out of v1 | Watchlist, Comparison, Diff, Newsletter assembly, Charts, Settings UI, Beehiiv API, PDF, mobile, E2E, per-user identity |

---

## File Structure

```
TerraRealCapital/
├── .gitignore                       # Python + Streamlit secrets
├── .editorconfig
├── README.md
├── .python-version                  # 3.12
├── pyproject.toml                   # uv project: deps + pytest config
├── .streamlit/
│   ├── config.toml                  # committed (theme/server)
│   └── secrets.toml.example         # committed; real secrets.toml is gitignored
├── supabase/
│   ├── config.toml
│   └── migrations/
│       ├── 0001_initial_schema.sql  # cities, reports, api_cache
│       └── 0002_seed_cities.sql     # 16 Midwest metros
├── trc/                             # pure logic, fully unit-tested
│   ├── __init__.py
│   ├── config.py                    # pydantic-settings loader
│   ├── models.py                    # pydantic: City, ReportPayload, ScanRequest
│   ├── db.py                        # Supabase client + typed CRUD
│   ├── cache.py                     # read-through api_cache (Perplexity only)
│   ├── perplexity.py                # Sonar client (httpx)
│   ├── claude.py                    # Anthropic dual-output (forced tool-use, caching)
│   ├── narrative.py                 # split/splice Markdown by headings
│   ├── orchestrator.py              # scan(): cache->perplexity->claude->validate->persist
│   └── prompts/
│       ├── __init__.py
│       ├── system.py                # cached scan system prompt + emit_report tool schema
│       └── regenerate.py            # section-rewrite prompt
├── ui/
│   ├── __init__.py
│   ├── auth.py                      # password gate (pure check + st.session_state guard)
│   └── structured_panel.py          # render metrics/signals/capital_flows/metrics_extra
├── app/
│   ├── Home.py                      # entrypoint: password gate + landing
│   └── pages/
│       ├── 1_Scanner.py
│       ├── 2_Report_Editor.py
│       └── 3_Library.py
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_models.py
    ├── test_db.py
    ├── test_cache.py
    ├── test_perplexity.py
    ├── test_claude.py
    ├── test_narrative.py
    ├── test_orchestrator.py
    └── test_auth.py
```

**File responsibility rule:** every file does one thing. If a file passes ~200 lines or grows two unrelated responsibilities, split it.

---

## Phase 0: Repo Setup

Goal: Python project scaffolding committed (git repo already exists with prior PRD commits).

### Task 0.1: Replace Node `.gitignore` with Python, add editorconfig

**Files:**
- Modify: `.gitignore`
- Create: `.editorconfig`

- [ ] **Step 1: Overwrite `.gitignore`** (the existing one targets Node from the superseded plan)

```gitignore
__pycache__/
*.py[cod]
.venv/
.uv/
*.egg-info/
.pytest_cache/
.ruff_cache/
.streamlit/secrets.toml
.env
.env.*
*.log
.DS_Store
Thumbs.db
supabase/.branches/
supabase/.temp/
```

- [ ] **Step 2: Create `.editorconfig`**

```editorconfig
root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.md]
trim_trailing_whitespace = false

[*.{yml,yaml,toml,json}]
indent_size = 2
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore .editorconfig
git commit -m "chore: switch project tooling to Python (gitignore, editorconfig)"
```

### Task 0.2: uv project + pyproject.toml + pinned Python

**Files:**
- Create: `.python-version`
- Create: `pyproject.toml`

- [ ] **Step 1:** Verify `uv` is installed: `uv --version` (install from https://docs.astral.sh/uv/ if missing). Verify `python --version` resolves to 3.12+ (uv will manage this).

- [ ] **Step 2: Create `.python-version`**

```
3.12
```

- [ ] **Step 3: Create `pyproject.toml`**

```toml
[project]
name = "trc-research-tool"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "streamlit>=1.40",
  "httpx>=0.27",
  "anthropic>=0.40",
  "supabase>=2.9",
  "pydantic>=2.9",
  "pydantic-settings>=2.6",
]

[dependency-groups]
dev = [
  "pytest>=8.3",
  "respx>=0.21",
  "pytest-asyncio>=0.24",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.uv]
package = false
```

- [ ] **Step 4:** `uv sync` (creates `.venv`, resolves deps). Expected: completes without error; `uv run python -c "import streamlit, httpx, anthropic, supabase, pydantic"` prints nothing and exits 0.

- [ ] **Step 5: Commit**

```bash
git add .python-version pyproject.toml uv.lock
git commit -m "chore: uv project with streamlit/httpx/anthropic/supabase deps"
```

### Task 0.3: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1:** Replace `README.md` with a short doc: what the tool is, the `trc/` + `ui/` + `app/` + `supabase/` layout, quick start (`uv sync`, `uv run pytest`, `uv run streamlit run app/Home.py`), and pointers to the spec and this plan.

- [ ] **Step 2: Commit** `git add README.md && git commit -m "docs: rewrite README for Streamlit/Python layout"`

---

## Phase 1: Supabase Foundation

Goal: Supabase project with schema (no `report_events`, no RLS, no auth FKs) and 16 seeded cities.

### Task 1.1: Create Supabase project (manual)

- [ ] **Step 1:** Dashboard -> New project, region `us-east-1`, name `trc-research-tool`. Store DB password in a password manager.
- [ ] **Step 2:** Project Settings -> API: capture `Project URL` and `service_role` key. The service-role key is used ONLY server-side by Streamlit. (We do not use the anon key or Supabase Auth.)

### Task 1.2: Supabase CLI init + link

- [ ] **Step 1:** Install Supabase CLI (https://supabase.com/docs/guides/cli). `supabase --version`.
- [ ] **Step 2:** `supabase init` (creates `supabase/config.toml`).
- [ ] **Step 3:** `supabase link --project-ref <ref>` (ref is in the dashboard URL).
- [ ] **Step 4:** Commit: `git add supabase/config.toml && git commit -m "chore: supabase init + link"`

### Task 1.3: Initial schema migration

**Files:**
- Create: `supabase/migrations/0001_initial_schema.sql`

- [ ] **Step 1: Write migration**

```sql
-- 0001_initial_schema.sql
create extension if not exists "pgcrypto";

create table public.cities (
  id           uuid primary key default gen_random_uuid(),
  name         text not null,
  state        text not null,
  fips_county  text not null,
  fips_metro   text not null,
  lat          numeric(9,6),
  lng          numeric(9,6),
  created_at   timestamptz not null default now(),
  unique (name, state)
);

create type report_status as enum ('ready', 'edited');

create table public.reports (
  id                uuid primary key default gen_random_uuid(),
  city_id           uuid not null references public.cities(id) on delete restrict,
  scan_date         date not null default current_date,
  status            report_status not null default 'ready',
  toggled_signals   text[] not null default '{}',
  metrics           jsonb,
  signals           jsonb,
  capital_flows     jsonb,
  submarkets        jsonb,
  evidence          jsonb,
  metrics_extra     jsonb,
  narrative_raw     text,
  narrative_edited  text,
  tags              text[] not null default '{}',
  created_at        timestamptz not null default now(),
  edited_at         timestamptz
);
create index reports_city_id_idx on public.reports (city_id);
create index reports_scan_date_idx on public.reports (scan_date desc);

create table public.api_cache (
  id          uuid primary key default gen_random_uuid(),
  source      text not null,
  geo_id      text not null,
  period      text not null,
  fetched_on  date not null default current_date,
  payload     jsonb not null,
  created_at  timestamptz not null default now(),
  unique (source, geo_id, period, fetched_on)
);
```

> No RLS, no `report_events`, no `auth.users` FKs, no `error` column — by design (spec §4/§5). Access is exclusively via the service-role key from the Streamlit server.

- [ ] **Step 2:** `supabase db push`. Expected: migration applies cleanly.
- [ ] **Step 3:** Commit `supabase/migrations/0001_initial_schema.sql`.

### Task 1.4: Seed 16 Midwest cities

**Files:**
- Create: `supabase/migrations/0002_seed_cities.sql`

- [ ] **Step 1: Write `supabase/migrations/0002_seed_cities.sql`** (16 Midwest metros; FIPS verified against Census 2024 MSA delineation files)

```sql
-- 0002_seed_cities.sql
insert into public.cities (name, state, fips_county, fips_metro, lat, lng) values
  ('Columbus',      'OH', '39049', '18140', 39.9612, -82.9988),
  ('Indianapolis',  'IN', '18097', '26900', 39.7684, -86.1581),
  ('Cleveland',     'OH', '39035', '17460', 41.4993, -81.6944),
  ('Cincinnati',    'OH', '39061', '17140', 39.1031, -84.5120),
  ('Kansas City',   'MO', '29095', '28140', 39.0997, -94.5786),
  ('St. Louis',     'MO', '29510', '41180', 38.6270, -90.1994),
  ('Minneapolis',   'MN', '27053', '33460', 44.9778, -93.2650),
  ('Milwaukee',     'WI', '55079', '33340', 43.0389, -87.9065),
  ('Madison',       'WI', '55025', '31540', 43.0731, -89.4012),
  ('Des Moines',    'IA', '19153', '19780', 41.5868, -93.6250),
  ('Omaha',         'NE', '31055', '36540', 41.2565, -95.9345),
  ('Detroit',       'MI', '26163', '19820', 42.3314, -83.0458),
  ('Grand Rapids',  'MI', '26081', '24340', 42.9634, -85.6681),
  ('Louisville',    'KY', '21111', '31140', 38.2527, -85.7585),
  ('Lexington',     'KY', '21067', '30460', 38.0406, -84.5037),
  ('Fort Wayne',    'IN', '18003', '23060', 41.0793, -85.1394)
on conflict (name, state) do nothing;
```

- [ ] **Step 2:** `supabase db push`. Verify: Supabase SQL editor `select count(*) from cities;` -> 16.
- [ ] **Step 3:** Commit `supabase/migrations/0002_seed_cities.sql`.

---

## Phase 2: Scan Pipeline (TDD)

Goal: the entire `trc/` package, each module test-first with pytest. Run all tests with `uv run pytest`.

### Task 2.1: Config loader (TDD)

**Files:**
- Create: `trc/__init__.py` (empty), `trc/config.py`
- Test: `tests/test_config.py`, `tests/conftest.py`

- [ ] **Step 1: Write failing test** `tests/test_config.py`

```python
import pytest
from trc.config import Settings

def test_settings_reads_required_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "svc")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pk")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ak")
    monkeypatch.setenv("APP_PASSWORD", "hunter2")
    s = Settings()
    assert s.supabase_url == "https://x.supabase.co"
    assert s.app_password == "hunter2"

def test_settings_missing_required_raises(monkeypatch):
    for k in ["SUPABASE_URL","SUPABASE_SERVICE_ROLE_KEY","PERPLEXITY_API_KEY","ANTHROPIC_API_KEY","APP_PASSWORD"]:
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(Exception):
        Settings()
```

- [ ] **Step 2:** `uv run pytest tests/test_config.py -v` -> FAIL (no module).

- [ ] **Step 3: Implement `trc/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    perplexity_api_key: str
    anthropic_api_key: str
    app_password: str
    perplexity_model: str = "sonar-pro"
    claude_model: str = "claude-sonnet-4-6"

def get_settings() -> Settings:
    return Settings()  # raises ValidationError if any required var is absent
```

- [ ] **Step 4:** `uv run pytest tests/test_config.py -v` -> PASS.
- [ ] **Step 5: Commit** `git add trc/__init__.py trc/config.py tests/test_config.py tests/conftest.py && git commit -m "feat(trc): pydantic-settings config loader"`

### Task 2.2: Pydantic models (TDD)

**Files:**
- Create: `trc/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write failing test** `tests/test_models.py`

```python
from trc.models import City, ReportPayload, ScanRequest

def test_report_payload_requires_narrative_and_buckets():
    p = ReportPayload(
        metrics={"population": "1.2M (per source)"},
        signals={"jobs": "growing"},
        capital_flows={"federal": "award X"},
        submarkets={"downtown": "tight"},
        evidence=[{"claim": "x", "source": "https://a"}],
        metrics_extra={},
        narrative_markdown="# Title\n\nBody",
    )
    assert p.narrative_markdown.startswith("# Title")

def test_scan_request_defaults_signals_empty():
    r = ScanRequest(city_id="abc")
    assert r.toggled_signals == []
```

- [ ] **Step 2:** Run -> FAIL.

- [ ] **Step 3: Implement `trc/models.py`**

```python
from pydantic import BaseModel, Field

class City(BaseModel):
    id: str
    name: str
    state: str
    fips_county: str
    fips_metro: str

class ScanRequest(BaseModel):
    city_id: str
    toggled_signals: list[str] = Field(default_factory=list)

class ReportPayload(BaseModel):
    """The dual-output Claude must produce (enforced via forced tool-use)."""
    metrics: dict = Field(default_factory=dict)
    signals: dict = Field(default_factory=dict)
    capital_flows: dict = Field(default_factory=dict)
    submarkets: dict = Field(default_factory=dict)
    evidence: list = Field(default_factory=list)
    metrics_extra: dict = Field(default_factory=dict)
    narrative_markdown: str
```

- [ ] **Step 4:** Run -> PASS.
- [ ] **Step 5: Commit.**

### Task 2.3: Supabase client + CRUD (TDD)

**Files:**
- Create: `trc/db.py`
- Test: `tests/test_db.py`

The Supabase client is created once from `Settings`. CRUD helpers are thin and accept an injected client so tests use a fake (no network).

- [ ] **Step 1: Write failing test** `tests/test_db.py`

```python
from trc.db import Database

class FakeTable:
    def __init__(self, store, name): self.store, self.name, self._q = store, name, {}
    def insert(self, row): self._row = row; return self
    def select(self, *_): self._op = "select"; return self
    def eq(self, k, v): self._q[k] = v; return self
    def order(self, *_a, **_k): return self
    def execute(self):
        if getattr(self, "_row", None) is not None:
            rec = {**self._row, "id": "r1"}; self.store[self.name].append(rec)
            return type("R", (), {"data": [rec]})
        rows = [r for r in self.store[self.name]
                if all(r.get(k) == v for k, v in self._q.items())]
        return type("R", (), {"data": rows})

class FakeClient:
    def __init__(self): self.store = {"reports": [], "cities": []}
    def table(self, n): return FakeTable(self.store, n)

def test_insert_and_get_report():
    db = Database(FakeClient())
    rid = db.insert_report({"city_id": "c1", "narrative_raw": "x"})
    assert rid == "r1"
    got = db.get_report("r1")
    assert got["narrative_raw"] == "x"

def test_list_reports_returns_rows():
    db = Database(FakeClient())
    db.insert_report({"city_id": "c1"})
    assert len(db.list_reports()) == 1
```

- [ ] **Step 2:** Run -> FAIL.

- [ ] **Step 3: Implement `trc/db.py`**

```python
from supabase import create_client
from trc.config import Settings

def make_client(settings: Settings):
    return create_client(settings.supabase_url, settings.supabase_service_role_key)

class Database:
    def __init__(self, client):
        self.c = client

    def insert_report(self, row: dict) -> str:
        res = self.c.table("reports").insert(row).execute()
        return res.data[0]["id"]

    def get_report(self, report_id: str) -> dict | None:
        res = self.c.table("reports").select("*").eq("id", report_id).execute()
        return res.data[0] if res.data else None

    def list_reports(self) -> list[dict]:
        return self.c.table("reports").select("*").order("scan_date", desc=True).execute().data

    def update_report(self, report_id: str, patch: dict) -> None:
        self.c.table("reports").update(patch).eq("id", report_id).execute()

    def list_cities(self) -> list[dict]:
        return self.c.table("cities").select("*").order("name").execute().data

    def get_cache(self, source, geo_id, period, fetched_on) -> dict | None:
        res = (self.c.table("api_cache").select("payload")
               .eq("source", source).eq("geo_id", geo_id)
               .eq("period", period).eq("fetched_on", fetched_on).execute())
        return res.data[0]["payload"] if res.data else None

    def put_cache(self, source, geo_id, period, fetched_on, payload) -> None:
        self.c.table("api_cache").insert({
            "source": source, "geo_id": geo_id, "period": period,
            "fetched_on": fetched_on, "payload": payload,
        }).execute()
```

> The `FakeTable` in the test only needs the methods the tests exercise; extend it minimally if a later test needs `update`.

- [ ] **Step 4:** Run -> PASS.
- [ ] **Step 5: Commit.**

### Task 2.4: Read-through cache (TDD)

**Files:**
- Create: `trc/cache.py`
- Test: `tests/test_cache.py`

- [ ] **Step 1: Write failing test** `tests/test_cache.py`

```python
import datetime as dt
from trc.cache import cached_perplexity

def test_cache_miss_calls_fetcher_then_stores():
    calls = []
    store = {}
    class DB:
        def get_cache(s,g,p,f): return None
        def put_cache(s,g,p,f,payload): store["v"] = payload
    def fetch(): calls.append(1); return {"content": "fresh"}
    out = cached_perplexity(DB(), geo_id="26163", scan_date=dt.date(2026,5,18), fetch=fetch)
    assert out == {"content": "fresh"}
    assert calls == [1] and store["v"] == {"content": "fresh"}

def test_cache_hit_skips_fetcher():
    class DB:
        def get_cache(s,g,p,f): return {"content": "cached"}
        def put_cache(*a, **k): raise AssertionError("should not write")
    out = cached_perplexity(DB(), geo_id="26163", scan_date=dt.date(2026,5,18),
                            fetch=lambda: (_ for _ in ()).throw(AssertionError("no call")))
    assert out == {"content": "cached"}
```

- [ ] **Step 2:** Run -> FAIL.

- [ ] **Step 3: Implement `trc/cache.py`**

```python
import datetime as dt
from typing import Callable

def cached_perplexity(db, *, geo_id: str, scan_date: dt.date, fetch: Callable[[], dict]) -> dict:
    period = scan_date.isoformat()
    hit = db.get_cache("perplexity", geo_id, period, scan_date)
    if hit is not None:
        return hit
    payload = fetch()
    db.put_cache("perplexity", geo_id, period, scan_date, payload)
    return payload
```

- [ ] **Step 4:** Run -> PASS.
- [ ] **Step 5: Commit.**

### Task 2.5: Perplexity client (TDD, respx)

**Files:**
- Create: `trc/perplexity.py`
- Test: `tests/test_perplexity.py`

Verified contract: `POST https://api.perplexity.ai/chat/completions`, header `Authorization: Bearer <key>`, body `{"model","messages","search_recency_filter"}`; response has `choices[0].message.content`, top-level `citations` (list[str]) and `search_results` (list[dict]).

- [ ] **Step 1: Write failing test** `tests/test_perplexity.py`

```python
import httpx, respx
from trc.perplexity import research_city

@respx.mock
def test_research_city_posts_and_parses():
    route = respx.post("https://api.perplexity.ai/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "Detroit multifamily brief..."}}],
            "citations": ["https://a.com", "https://b.com"],
            "search_results": [{"title": "T", "url": "https://a.com", "date": "2026-05-01"}],
        })
    )
    out = research_city(api_key="pk", model="sonar-pro",
                         city_name="Detroit", state="MI", signals=["jobs"])
    assert route.called
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer pk"
    assert out["content"].startswith("Detroit")
    assert out["citations"] == ["https://a.com", "https://b.com"]
    assert out["search_results"][0]["url"] == "https://a.com"

@respx.mock
def test_research_city_raises_on_http_error():
    respx.post("https://api.perplexity.ai/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "boom"}))
    import pytest
    with pytest.raises(httpx.HTTPStatusError):
        research_city(api_key="pk", model="sonar-pro",
                      city_name="Detroit", state="MI", signals=[])
```

- [ ] **Step 2:** Run -> FAIL.

- [ ] **Step 3: Implement `trc/perplexity.py`**

```python
import httpx

ENDPOINT = "https://api.perplexity.ai/chat/completions"

def _prompt(city_name: str, state: str, signals: list[str]) -> str:
    focus = f" Emphasise these signals: {', '.join(signals)}." if signals else ""
    return (
        f"Research the multifamily real-estate investment outlook for "
        f"{city_name}, {state}. Cover population and migration, employment and "
        f"major employers, rent and vacancy trends, multifamily construction "
        f"pipeline, notable capital flows and federal awards, and submarket "
        f"dynamics. Cite recent, specific sources.{focus}"
    )

def research_city(*, api_key: str, model: str, city_name: str, state: str,
                  signals: list[str], timeout: float = 90.0) -> dict:
    resp = httpx.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user",
                          "content": _prompt(city_name, state, signals)}],
            "search_recency_filter": "month",
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "content": data["choices"][0]["message"]["content"],
        "citations": data.get("citations", []),
        "search_results": data.get("search_results", []),
    }
```

- [ ] **Step 4:** Run -> PASS.
- [ ] **Step 5: Commit.**

### Task 2.6: Scan system prompt + emit_report tool schema

**Files:**
- Create: `trc/prompts/__init__.py` (empty), `trc/prompts/system.py`
- Test: `tests/test_claude.py` (assertions added here, used by 2.7)

- [ ] **Step 1: Implement `trc/prompts/system.py`**

```python
# System prompt must be >= ~1024 tokens for Sonnet 4.6 prompt caching to engage.
# Keep it long, stable, and identical across calls (verbatim) so the cache hits.

SCAN_SYSTEM_PROMPT = """You are a senior multifamily real-estate research analyst \
for Terra Real Capital, a Midwest-focused syndication. You convert raw web research \
about a single metro into TWO synchronized outputs in ONE pass:

1. A STRUCTURED object capturing decision-grade signals.
2. A long-form Beehiiv-ready Markdown narrative for an LP investor newsletter.

Rules:
- Use ONLY facts present in the provided research. Never invent numbers.
- Every numeric claim is 'as reported by the cited research', not authoritative.
- The narrative MUST be well-structured Markdown with clear '##' section headings \
(e.g. '## Market Overview', '## Employment & Population', '## Rent & Supply', \
'## Capital Flows', '## Submarket Notes', '## Bottom Line for LPs').
- Keep the narrative concrete, skimmable, and free of hype.
- Populate every structured bucket; use metrics_extra for anything that does not \
fit metrics/signals/capital_flows/submarkets.
- 'evidence' is a list of {claim, source_url} objects tying key claims to citations.

[Extend this prompt with detailed scoring rubric, tone guide, and worked examples \
so it comfortably exceeds 1024 tokens and remains byte-identical between calls.]
"""

EMIT_REPORT_TOOL = {
    "name": "emit_report",
    "description": "Emit the structured report and the Markdown narrative together.",
    "input_schema": {
        "type": "object",
        "properties": {
            "metrics": {"type": "object"},
            "signals": {"type": "object"},
            "capital_flows": {"type": "object"},
            "submarkets": {"type": "object"},
            "evidence": {"type": "array", "items": {"type": "object"}},
            "metrics_extra": {"type": "object"},
            "narrative_markdown": {"type": "string"},
        },
        "required": ["metrics", "signals", "capital_flows", "submarkets",
                     "evidence", "metrics_extra", "narrative_markdown"],
    },
}
```

- [ ] **Step 2:** No test of its own (constants). Commit with Task 2.7.

> **Sub-skill:** consult @claude-api for current Anthropic SDK patterns (forced tool-use, prompt-caching block placement, usage fields) before implementing Task 2.7.

### Task 2.7: Claude dual-output client (TDD)

**Files:**
- Create: `trc/claude.py`
- Test: `tests/test_claude.py`

Verified contract: `system` is a list with one text block carrying `cache_control={"type":"ephemeral"}`; force structured output with `tool_choice={"type":"tool","name":"emit_report"}`; read the tool input from the `tool_use` content block.

- [ ] **Step 1: Write failing test** `tests/test_claude.py`

```python
from trc.claude import generate_report
from trc.models import ReportPayload

class FakeBlock:
    def __init__(self, **kw): self.__dict__.update(kw)

class FakeMessages:
    def __init__(self, captured): self.captured = captured
    def create(self, **kw):
        self.captured.update(kw)
        tool_block = FakeBlock(type="tool_use", name="emit_report", input={
            "metrics": {"pop": "1.2M"}, "signals": {}, "capital_flows": {},
            "submarkets": {}, "evidence": [], "metrics_extra": {},
            "narrative_markdown": "## Market Overview\n\nText.",
        })
        return FakeBlock(content=[tool_block],
                         usage=FakeBlock(cache_read_input_tokens=0))

class FakeAnthropic:
    def __init__(self): self.captured = {}; self.messages = FakeMessages(self.captured)

def test_generate_report_forces_tool_and_caches_system():
    client = FakeAnthropic()
    payload = generate_report(client, model="claude-sonnet-4-6",
                              research_text="raw research", signals=["jobs"])
    assert isinstance(payload, ReportPayload)
    assert payload.metrics == {"pop": "1.2M"}
    sys = client.captured["system"]
    assert isinstance(sys, list) and sys[0]["cache_control"] == {"type": "ephemeral"}
    assert client.captured["tool_choice"] == {"type": "tool", "name": "emit_report"}
```

- [ ] **Step 2:** Run -> FAIL.

- [ ] **Step 3: Implement `trc/claude.py`**

```python
from anthropic import Anthropic
from trc.config import Settings
from trc.models import ReportPayload
from trc.prompts.system import SCAN_SYSTEM_PROMPT, EMIT_REPORT_TOOL

def make_anthropic(settings: Settings) -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)

def generate_report(client, *, model: str, research_text: str,
                     signals: list[str]) -> ReportPayload:
    focus = f"\n\nEmphasise: {', '.join(signals)}." if signals else ""
    msg = client.messages.create(
        model=model,
        max_tokens=8000,
        system=[{
            "type": "text",
            "text": SCAN_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        tools=[EMIT_REPORT_TOOL],
        tool_choice={"type": "tool", "name": "emit_report"},
        messages=[{
            "role": "user",
            "content": f"Research to convert into the report:\n\n{research_text}{focus}",
        }],
    )
    tool_use = next(b for b in msg.content if getattr(b, "type", None) == "tool_use")
    return ReportPayload.model_validate(tool_use.input)
```

- [ ] **Step 4:** Run -> PASS.
- [ ] **Step 5: Commit** `trc/prompts/`, `trc/claude.py`, `tests/test_claude.py`.

### Task 2.8: Narrative split/splice by headings (TDD)

**Files:**
- Create: `trc/narrative.py`
- Test: `tests/test_narrative.py`

Powers the section-regenerate UX: split the Markdown at `##` headings, list section titles, replace one section's body, reassemble.

- [ ] **Step 1: Write failing test** `tests/test_narrative.py`

```python
from trc.narrative import split_sections, section_titles, splice_section

MD = "Intro line\n\n## Alpha\n\nA body\n\n## Beta\n\nB body\n"

def test_split_keeps_preamble_and_sections():
    pre, secs = split_sections(MD)
    assert pre.strip() == "Intro line"
    assert [s.title for s in secs] == ["Alpha", "Beta"]
    assert secs[0].body.strip() == "A body"

def test_titles_helper():
    assert section_titles(MD) == ["Alpha", "Beta"]

def test_splice_replaces_only_target_section():
    out = splice_section(MD, "Beta", "NEW B")
    assert "## Beta\n\nNEW B" in out
    assert "A body" in out          # other section untouched
    assert out.count("## ") == 2

def test_splice_unknown_title_raises():
    import pytest
    with pytest.raises(KeyError):
        splice_section(MD, "Gamma", "x")
```

- [ ] **Step 2:** Run -> FAIL.

- [ ] **Step 3: Implement `trc/narrative.py`**

```python
import re
from dataclasses import dataclass

_H = re.compile(r"^##\s+(.*)$", re.M)

@dataclass
class Section:
    title: str
    body: str

def split_sections(md: str) -> tuple[str, list[Section]]:
    matches = list(_H.finditer(md))
    if not matches:
        return md, []
    preamble = md[: matches[0].start()]
    sections: list[Section] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        body = md[m.end(): end].lstrip("\n").rstrip()
        sections.append(Section(title=m.group(1).strip(), body=body))
    return preamble, sections

def section_titles(md: str) -> list[str]:
    return [s.title for s in split_sections(md)[1]]

def splice_section(md: str, title: str, new_body: str) -> str:
    preamble, sections = split_sections(md)
    if title not in {s.title for s in sections}:
        raise KeyError(title)
    rebuilt = [preamble.rstrip()]
    for s in sections:
        body = new_body.strip() if s.title == title else s.body
        rebuilt.append(f"## {s.title}\n\n{body}")
    return "\n\n".join(part for part in rebuilt if part).strip() + "\n"
```

- [ ] **Step 4:** Run -> PASS.
- [ ] **Step 5: Commit.**

### Task 2.9: Section-regenerate prompt + Claude rewrite (TDD)

**Files:**
- Create: `trc/prompts/regenerate.py`
- Modify: `trc/claude.py` (add `regenerate_section`)
- Test: `tests/test_claude.py` (add cases)

- [ ] **Step 1: Implement `trc/prompts/regenerate.py`**

```python
REGEN_INSTRUCTIONS = """Rewrite ONLY the given newsletter section. Preserve the \
section's intent and any factual claims; do not introduce facts not present in the \
original section. Return Markdown body text only (no '##' heading line)."""
```

- [ ] **Step 2: Write failing test** (append to `tests/test_claude.py`)

```python
def test_regenerate_section_returns_plain_body():
    from trc.claude import regenerate_section
    class M:
        def create(self, **kw):
            self.kw = kw
            return FakeBlock(content=[FakeBlock(type="text", text="Punchier body.")],
                             usage=FakeBlock(cache_read_input_tokens=0))
    class C: messages = M()
    c = C()
    out = regenerate_section(c, model="claude-sonnet-4-6",
                             section_title="Beta", section_body="Old body",
                             instruction="make it punchier")
    assert out == "Punchier body."
```

- [ ] **Step 3:** Run -> FAIL.

- [ ] **Step 4: Add to `trc/claude.py`**

```python
from trc.prompts.regenerate import REGEN_INSTRUCTIONS

def regenerate_section(client, *, model: str, section_title: str,
                        section_body: str, instruction: str) -> str:
    extra = f"\n\nUser instruction: {instruction}" if instruction.strip() else ""
    msg = client.messages.create(
        model=model,
        max_tokens=2000,
        system=[{"type": "text", "text": REGEN_INSTRUCTIONS,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user",
                   "content": f"Section: {section_title}\n\n{section_body}{extra}"}],
    )
    return "".join(b.text for b in msg.content
                   if getattr(b, "type", None) == "text").strip()
```

> The regenerate system prompt is short and will not meet the 1024-token cache minimum — that is acceptable (caching simply no-ops). The block shape stays consistent with the scan call.

- [ ] **Step 5:** Run -> PASS. Commit.

### Task 2.10: Orchestrator (TDD)

**Files:**
- Create: `trc/orchestrator.py`
- Test: `tests/test_orchestrator.py`

Contract: `scan()` accepts injected `db`, `perplexity_fetch`, `claude_generate`, a city, signals, and a `progress` callback. It runs cache->perplexity->claude->validate, then inserts the report ONLY on success and returns the new report id. Any exception propagates (caller renders the failure); nothing is persisted on failure.

- [ ] **Step 1: Write failing test** `tests/test_orchestrator.py`

```python
import datetime as dt, pytest
from trc.orchestrator import scan
from trc.models import ReportPayload

class DB:
    def __init__(self): self.inserted=None; self.cache={}
    def get_cache(self,*a): return None
    def put_cache(self,*a): pass
    def insert_report(self, row): self.inserted=row; return "rid-1"

def good_payload():
    return ReportPayload(metrics={"p":"1"}, signals={}, capital_flows={},
        submarkets={}, evidence=[], metrics_extra={},
        narrative_markdown="## Market Overview\n\nText.")

def test_scan_happy_path_persists_once_and_reports_progress():
    db = DB(); steps=[]
    rid = scan(db,
        city={"id":"c1","name":"Detroit","state":"MI","fips_metro":"19820"},
        signals=["jobs"], scan_date=dt.date(2026,5,18),
        perplexity_fetch=lambda: {"content":"raw","citations":["u"],"search_results":[]},
        claude_generate=lambda research: good_payload(),
        progress=steps.append)
    assert rid == "rid-1"
    assert db.inserted["status"] == "ready"
    assert db.inserted["narrative_raw"] == db.inserted["narrative_edited"]
    assert "Researching" in steps[0]

def test_scan_failure_persists_nothing():
    db = DB()
    def boom(): raise RuntimeError("perplexity down")
    with pytest.raises(RuntimeError):
        scan(db, city={"id":"c1","name":"X","state":"MI","fips_metro":"00000"},
             signals=[], scan_date=dt.date(2026,5,18),
             perplexity_fetch=boom, claude_generate=lambda r: good_payload(),
             progress=lambda s: None)
    assert db.inserted is None
```

- [ ] **Step 2:** Run -> FAIL.

- [ ] **Step 3: Implement `trc/orchestrator.py`**

```python
import datetime as dt
from typing import Callable
from trc.cache import cached_perplexity
from trc.models import ReportPayload

def scan(db, *, city: dict, signals: list[str], scan_date: dt.date,
         perplexity_fetch: Callable[[], dict],
         claude_generate: Callable[[str], ReportPayload],
         progress: Callable[[str], None]) -> str:
    progress("Researching via Perplexity…")
    research = cached_perplexity(db, geo_id=city["fips_metro"],
                                 scan_date=scan_date, fetch=perplexity_fetch)

    progress("Writing report with Claude…")
    payload: ReportPayload = claude_generate(research["content"])

    progress("Saving…")
    row = {
        "city_id": city["id"],
        "scan_date": scan_date.isoformat(),
        "status": "ready",
        "toggled_signals": signals,
        "metrics": payload.metrics,
        "signals": payload.signals,
        "capital_flows": payload.capital_flows,
        "submarkets": payload.submarkets,
        "evidence": payload.evidence,
        "metrics_extra": payload.metrics_extra,
        "narrative_raw": payload.narrative_markdown,
        "narrative_edited": payload.narrative_markdown,
    }
    return db.insert_report(row)
```

- [ ] **Step 4:** Run -> PASS. Run the whole suite: `uv run pytest` -> all green.
- [ ] **Step 5: Commit.**

---

## Phase 3: Streamlit Shell + Password Gate

Goal: app boots, password gate works, three pages register, Supabase reachable.

### Task 3.1: Streamlit config + secrets example

**Files:**
- Create: `.streamlit/config.toml`, `.streamlit/secrets.toml.example`

- [ ] **Step 1: `.streamlit/config.toml`**

```toml
[server]
headless = true
[theme]
base = "light"
```

- [ ] **Step 2: `.streamlit/secrets.toml.example`** (copy to `.streamlit/secrets.toml` locally; the real file is gitignored)

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "service-role-key"
PERPLEXITY_API_KEY = "pplx-..."
ANTHROPIC_API_KEY = "sk-ant-..."
APP_PASSWORD = "choose-a-strong-shared-password"
```

- [ ] **Step 3:** Commit both (and confirm `.streamlit/secrets.toml` is gitignored — added in Task 0.1).

### Task 3.2: Password gate (TDD the pure check)

**Files:**
- Create: `ui/__init__.py` (empty), `ui/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write failing test** `tests/test_auth.py`

```python
from ui.auth import password_matches

def test_password_matches_is_constant_time_equal():
    assert password_matches("hunter2", "hunter2") is True
    assert password_matches("wrong", "hunter2") is False
    assert password_matches("", "hunter2") is False
```

- [ ] **Step 2:** Run -> FAIL.

- [ ] **Step 3: Implement `ui/auth.py`**

```python
import hmac
import streamlit as st

def password_matches(entered: str, expected: str) -> bool:
    return hmac.compare_digest(entered or "", expected or "")

def require_auth() -> None:
    """Call at the top of every page/entrypoint. Blocks until authed."""
    if st.session_state.get("authed"):
        return
    st.title("Terra Real Capital — Research Tool")
    pw = st.text_input("Password", type="password")
    if st.button("Enter"):
        if password_matches(pw, st.secrets["APP_PASSWORD"]):
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()
```

- [ ] **Step 4:** Run -> PASS (`password_matches` is import-safe; `require_auth` is smoke-tested only).
- [ ] **Step 5: Commit.**

### Task 3.3: App entrypoint + Supabase resource

**Files:**
- Create: `app/__init__.py` (empty), `app/Home.py`
- Create: `ui/resources.py` (cached singletons bridging `st.secrets` -> `Settings`/clients)

- [ ] **Step 1: `ui/resources.py`**

```python
import streamlit as st
from trc.config import Settings
from trc.db import Database, make_client
from trc.claude import make_anthropic

@st.cache_resource
def settings() -> Settings:
    import os
    for k in ["SUPABASE_URL","SUPABASE_SERVICE_ROLE_KEY","PERPLEXITY_API_KEY",
              "ANTHROPIC_API_KEY","APP_PASSWORD"]:
        os.environ.setdefault(k, st.secrets[k])
    return Settings()

@st.cache_resource
def database() -> Database:
    return Database(make_client(settings()))

@st.cache_resource
def anthropic_client():
    return make_anthropic(settings())
```

- [ ] **Step 2: `app/Home.py`**

```python
import streamlit as st
from ui.auth import require_auth

st.set_page_config(page_title="TRC Research Tool", layout="wide")
require_auth()
st.title("Terra Real Capital — Research Tool")
st.write("Use the sidebar: **Scanner** to generate a report, "
         "**Report Editor** to refine it, **Library** to browse history.")
```

- [ ] **Step 3: Smoke test:** `uv run streamlit run app/Home.py`. With a valid local `.streamlit/secrets.toml`: password prompt appears; correct password -> landing page; sidebar shows three (currently empty) pages once Phase 4-6 add them.
- [ ] **Step 4: Commit.**

---

## Phase 4: Scanner Page

Goal: choose city + signals, run a synchronous scan with live `st.status`, surface failures.

### Task 4.1: Scanner page

**Files:**
- Create: `app/pages/1_Scanner.py`

- [ ] **Step 1: Implement `app/pages/1_Scanner.py`**

```python
import datetime as dt
import streamlit as st
from ui.auth import require_auth
from ui.resources import database, anthropic_client, settings
from trc.orchestrator import scan
from trc.perplexity import research_city
from trc.claude import generate_report

st.set_page_config(page_title="Scanner", layout="wide")
require_auth()
st.title("Scanner")

db = database()
cities = db.list_cities()
by_label = {f'{c["name"]}, {c["state"]}': c for c in cities}

label = st.selectbox("City", list(by_label))
SIGNALS = ["jobs", "population", "rents", "supply pipeline",
           "capital flows", "submarkets"]
chosen = st.multiselect("Emphasise signals (optional)", SIGNALS)

if st.button("Scan", type="primary"):
    city = by_label[label]
    cfg = settings()
    today = dt.date.today()
    try:
        with st.status("Starting scan…", expanded=True) as status:
            def progress(msg: str):
                status.update(label=msg)
                st.write(msg)

            rid = scan(
                db,
                city=city,
                signals=chosen,
                scan_date=today,
                perplexity_fetch=lambda: research_city(
                    api_key=cfg.perplexity_api_key,
                    model=cfg.perplexity_model,
                    city_name=city["name"], state=city["state"],
                    signals=chosen),
                claude_generate=lambda research: generate_report(
                    anthropic_client(), model=cfg.claude_model,
                    research_text=research, signals=chosen),
                progress=progress,
            )
            status.update(label="Scan complete", state="complete")
        st.session_state["open_report_id"] = rid
        st.success("Report ready. Open it from **Report Editor** in the sidebar.")
    except Exception as e:  # noqa: BLE001 - top-level scan boundary
        # st.status auto-marks error when the with-block raises; reinforce with a banner.
        # Spec §5: human-readable banner in the UI; full traceback server-side ONLY
        # (never st.exception()). Streamlit Community Cloud captures stdout/stderr.
        import logging
        logging.exception("scan failed")
        st.error(f"Scan failed ({type(e).__name__}): {e}")
```

> Failure behavior (spec §5): the `with st.status(...)` block auto-flips to the error state when the body raises; the `st.error()` banner names the failure; nothing was persisted because `scan()` inserts only after success. City/signal controls remain populated for an immediate re-run.

- [ ] **Step 2: Smoke test (mock-free dry run):** with real secrets, pick a city, Scan. Verify live step messages, a `reports` row appears in Supabase, and `open_report_id` is set. Then temporarily set `PERPLEXITY_API_KEY` to a bad value and confirm the red error state + banner + no new row.
- [ ] **Step 3: Commit.**

---

## Phase 5: Report Editor Page

Goal: view structured panel, edit narrative with live preview, regenerate a section, tag, copy, save.

### Task 5.1: Structured panel component

**Files:**
- Create: `ui/structured_panel.py`

- [ ] **Step 1: Implement `ui/structured_panel.py`**

```python
import streamlit as st

def _kv(title: str, obj):
    if not obj:
        return
    st.subheader(title)
    if isinstance(obj, dict):
        for k, v in obj.items():
            st.markdown(f"- **{k}:** {v}")
    else:
        st.json(obj)

def render_structured_panel(report: dict) -> None:
    _kv("Metrics", report.get("metrics"))
    _kv("Signals", report.get("signals"))
    _kv("Capital flows", report.get("capital_flows"))
    _kv("Submarkets", report.get("submarkets"))
    _kv("Evidence", report.get("evidence"))
    _kv("Other metrics", report.get("metrics_extra"))
```

- [ ] **Step 2: Commit.**

### Task 5.2: Report Editor page

**Files:**
- Create: `app/pages/2_Report_Editor.py`

- [ ] **Step 1: Implement `app/pages/2_Report_Editor.py`**

```python
import datetime as dt
import streamlit as st
from ui.auth import require_auth
from ui.resources import database, anthropic_client, settings
from ui.structured_panel import render_structured_panel
from trc.narrative import section_titles, split_sections, splice_section
from trc.claude import regenerate_section

st.set_page_config(page_title="Report Editor", layout="wide")
require_auth()
st.title("Report Editor")

db = database()
reports = db.list_reports()
if not reports:
    st.info("No reports yet. Run one from the Scanner.")
    st.stop()

labels = {f'{r["scan_date"]} · {r["id"][:8]} · {r.get("status")}': r["id"]
          for r in reports}
default_id = st.session_state.get("open_report_id")
keys = list(labels)
idx = next((i for i, k in enumerate(keys) if labels[k] == default_id), 0)
sel = st.selectbox("Report", keys, index=idx)
report = db.get_report(labels[sel])

# Per-report edit buffer in session
buf_key = f"narr::{report['id']}"
if buf_key not in st.session_state:
    st.session_state[buf_key] = report.get("narrative_edited") or ""

left, right = st.columns(2)
with left:
    st.subheader("Structured")
    render_structured_panel(report)
with right:
    st.subheader("Narrative")
    st.session_state[buf_key] = st.text_area(
        "Markdown", st.session_state[buf_key], height=480, label_visibility="collapsed")
    st.markdown("**Preview**")
    st.markdown(st.session_state[buf_key])

st.divider()
st.subheader("Regenerate a section")
titles = section_titles(st.session_state[buf_key])
if titles:
    tcol, icol, bcol = st.columns([2, 3, 1])
    target = tcol.selectbox("Section", titles)
    instruction = icol.text_input("Instruction (optional)",
                                  placeholder="make it punchier")
    if bcol.button("Regenerate"):
        _, secs = split_sections(st.session_state[buf_key])
        body = next(s.body for s in secs if s.title == target)
        new_body = regenerate_section(
            anthropic_client(), model=settings().claude_model,
            section_title=target, section_body=body, instruction=instruction)
        st.session_state[buf_key] = splice_section(
            st.session_state[buf_key], target, new_body)
        st.rerun()
else:
    st.caption("No `##` sections detected to regenerate.")

st.divider()
tags = st.text_input("Tags (comma-separated)",
                     ", ".join(report.get("tags") or []))
if st.button("Save", type="primary"):
    db.update_report(report["id"], {
        "narrative_edited": st.session_state[buf_key],
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "status": "edited",
        "edited_at": dt.datetime.utcnow().isoformat(),
    })
    st.success("Saved.")

st.divider()
st.subheader("Copy for Beehiiv")
st.code(st.session_state[buf_key], language="markdown")
```

> Spec §6: regenerate writes only to the in-session buffer; persistence happens on explicit **Save**. `st.code` gives the built-in copy button.

- [ ] **Step 2: Smoke test:** open a scanned report; edit text -> preview updates; regenerate a section -> only that section changes; Save -> reload page, edits persisted, status `edited`; copy button works.
- [ ] **Step 3: Commit.**

---

## Phase 6: Library Page

Goal: browse + filter history, jump into the editor.

### Task 6.1: Library page

**Files:**
- Create: `app/pages/3_Library.py`

- [ ] **Step 1: Implement `app/pages/3_Library.py`**

```python
import streamlit as st
from ui.auth import require_auth
from ui.resources import database

st.set_page_config(page_title="Library", layout="wide")
require_auth()
st.title("Library")

db = database()
reports = db.list_reports()
cities = {c["id"]: f'{c["name"]}, {c["state"]}' for c in db.list_cities()}

if not reports:
    st.info("No reports yet. Run one from the Scanner.")
    st.stop()

c1, c2, c3 = st.columns(3)
city_filter = c1.selectbox("City", ["All"] + sorted(set(cities.values())))
status_filter = c2.selectbox("Status", ["All", "ready", "edited"])
tag_filter = c3.text_input("Tag contains")

def keep(r):
    if city_filter != "All" and cities.get(r["city_id"]) != city_filter:
        return False
    if status_filter != "All" and r.get("status") != status_filter:
        return False
    if tag_filter and not any(tag_filter.lower() in t.lower()
                              for t in (r.get("tags") or [])):
        return False
    return True

rows = [r for r in reports if keep(r)]
st.caption(f"{len(rows)} report(s)")
for r in rows:
    with st.container(border=True):
        st.markdown(f'**{cities.get(r["city_id"], "?")}** · {r["scan_date"]} '
                    f'· `{r.get("status")}` · {", ".join(r.get("tags") or [])}')
        if st.button("Open in editor", key=f'open-{r["id"]}'):
            st.session_state["open_report_id"] = r["id"]
            st.switch_page("pages/2_Report_Editor.py")
```

- [ ] **Step 2: Smoke test:** filters narrow the list; "Open in editor" navigates with the right report preselected.
- [ ] **Step 3: Commit.**

---

## Phase 7: Deploy + End-to-End Smoke

### Task 7.1: Push to GitHub

- [ ] **Step 1:** Ensure a GitHub remote exists (`git remote -v`); if not, create the repo and `git remote add origin ...`.
- [ ] **Step 2:** `git push -u origin main` (only when the user authorizes pushing).

### Task 7.2: Deploy to Streamlit Community Cloud

- [ ] **Step 1:** share.streamlit.io -> New app -> point at the repo, branch `main`, main file `app/Home.py`.
- [ ] **Step 2:** In the app's **Secrets** UI, paste the five keys from `.streamlit/secrets.toml.example` with real values.
- [ ] **Step 3:** Deploy; confirm Python 3.12 is selected (matches `.python-version`).

### Task 7.3: End-to-end smoke

- [ ] **Step 1:** Open the deployed URL -> password gate blocks; correct password enters.
- [ ] **Step 2:** Scanner: run a real scan on one city. Verify live status, success, and a `reports` row in Supabase.
- [ ] **Step 3:** Report Editor: edit, regenerate a section, Save; reload and confirm persistence; copy the Markdown.
- [ ] **Step 4:** Library: filter and re-open the report.
- [ ] **Step 5:** Force a failure (temporarily set a bad `PERPLEXITY_API_KEY` secret) and confirm the red `st.status` + `st.error()` banner and that no partial row was written. Restore the key.

---

## Appendix A: Required secrets (`.streamlit/secrets.toml`)

`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `PERPLEXITY_API_KEY`, `ANTHROPIC_API_KEY`, `APP_PASSWORD`. Local `.env` (for `uv run pytest` integration runs, if any) mirrors these; both files are gitignored.

## Appendix B: Engineering principles

- TDD on every `trc/` and `ui/auth.py` pure function; Streamlit pages verified by manual browser smoke (no E2E in v1).
- One responsibility per file; split at ~200 lines.
- DRY / YAGNI: nothing built that the spec did not ask for.
- Numbers are "as reported by Perplexity research", never presented as authoritative.
- A `reports` row is written only on full scan success; failures notify the user in the frontend and persist nothing.
- Verify external API/SDK shapes against live docs before changing client code (Perplexity + Anthropic verified 2026-05-18).

## Appendix C: Skills referenced

- @claude-api — Anthropic SDK forced tool-use, prompt-caching block shape, usage fields (Task 2.6/2.7/2.9).
- superpowers:subagent-driven-development or superpowers:executing-plans — execution.
- superpowers:test-driven-development — Phase 2 discipline.
