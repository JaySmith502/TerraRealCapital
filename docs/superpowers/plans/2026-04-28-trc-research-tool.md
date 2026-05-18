> ⚠️ **SUPERSEDED — 2026-05-18.** This React/Node plan is no longer active. The
> project moved to a Streamlit/Python architecture. Do not implement from this file.
> - Active spec: `docs/superpowers/specs/2026-05-18-trc-streamlit-redesign-design.md`
> - Active plan: `docs/superpowers/plans/2026-05-18-trc-streamlit-research-tool.md`
> Kept for historical reference only.
# Terra Real Capital Research Tool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an internal research tool for Danielle + team that scans Midwest cities for multifamily investment signals and produces (a) decision-grade structured reports and (b) Beehiiv-ready newsletter drafts, with full history persisted in Supabase.

**Architecture:** Vite + React SPA hosted on Vercel talks directly to Supabase (Postgres + Auth + Realtime) for all CRUD. A single Node service hosted on Railway exposes `POST /scan` and `POST /regenerate` — it fans out to BLS / Census / HUD / USASpending APIs, calls Claude Sonnet 4.6 with a dual-output prompt (strict JSON metrics + long-form Markdown narrative), writes the result to the `reports` table, and emits progress rows to `report_events` which the SPA subscribes to via Supabase Realtime. External API responses are deduped through an `api_cache` table.

**Tech Stack:**
- **Frontend:** Vite, React 19, TypeScript, Tailwind v4, shadcn/ui, React Router v6, TanStack Query v5, react-hook-form, zod, MDXEditor, sonner, `@supabase/supabase-js`
- **Backend:** Node 20 LTS, TypeScript, Express, Vitest, MSW for HTTP mocks, `@anthropic-ai/sdk`, `@supabase/supabase-js` (service-role)
- **Data:** Supabase (Postgres 15, RLS, Realtime), Supabase Auth (magic link)
- **AI:** Anthropic API, model `claude-sonnet-4-6`, prompt caching on system prompt
- **Hosting:** Vercel (SPA), Railway (scanner), Supabase managed (DB + auth)
- **Tooling:** pnpm, ESLint, Prettier

---

## Reference Spec (locked during brainstorming)

| Decision | Choice |
|---|---|
| Audience | Internal: Danielle + 2-3 analysts |
| Auth | Supabase magic-link |
| Persistence | Supabase Postgres |
| Report shape | Structured JSON + Markdown narrative from one scan |
| External-API caching | `api_cache` table keyed by `(source, geo_id, period, fetched_on)` |
| Section regenerate | Highlight paragraph -> floating button -> Sonnet 4.6 |
| v1 screens | Login, Scanner, Report Editor, Library |
| Out of v1 | Watchlist, Comparison, Diff, Newsletter assembly, Charts, Settings UI, Beehiiv API integration, PDF export |
| Newsletter export | Copy Markdown to clipboard |
| Scan model | `claude-sonnet-4-6` (both scan + regen) |
| Cities v1 | 16 Midwest metros |

---

## File Structure

```
TerraRealCapital/
├── README.md
├── .gitignore
├── .editorconfig
├── docs/superpowers/plans/                    # plan documents
├── supabase/
│   ├── migrations/
│   │   ├── 0001_initial_schema.sql            # cities, reports, api_cache, report_events
│   │   ├── 0002_rls_policies.sql              # RLS for all tables
│   │   └── 0003_seed_cities.sql               # 16 Midwest metros
│   └── config.toml
├── server/                                    # Node scanner microservice
│   ├── package.json
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   ├── .env.example                           # see Appendix A
│   ├── Procfile
│   ├── src/
│   │   ├── index.ts                           # Express boot + buildApp factory
│   │   ├── config.ts                          # zod-validated env loader
│   │   ├── routes/
│   │   │   ├── scan.ts                        # POST /scan handler
│   │   │   └── regenerate.ts                  # POST /regenerate handler
│   │   ├── sources/
│   │   │   ├── bls.ts                         # BLS API client
│   │   │   ├── census.ts                      # Census ACS 5-Year client
│   │   │   ├── hud.ts                         # HUD Fair Market Rents client
│   │   │   └── usaspending.ts                 # Federal awards client
│   │   ├── cache.ts                           # Read-through cache against api_cache
│   │   ├── claude.ts                          # Anthropic dual-output client
│   │   ├── orchestrator.ts                    # Fan-out + Claude + Supabase write
│   │   ├── supabase.ts                        # Service-role client singleton
│   │   ├── progress.ts                        # report_events emitter
│   │   └── prompts/
│   │       ├── system.ts                      # Cached scan system prompt
│   │       └── regenerate.ts                  # Section-rewrite prompt template
│   └── tests/
│       ├── setup.ts
│       ├── handlers.ts
│       ├── config.test.ts
│       ├── sources/{bls,census,hud,usaspending}.test.ts
│       ├── cache.test.ts
│       ├── progress.test.ts
│       ├── claude.test.ts
│       ├── orchestrator.test.ts
│       └── routes.test.ts
└── web/                                       # Vite SPA
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    ├── .env.example
    ├── components.json                        # shadcn/ui config
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── index.css
    │   ├── lib/{supabase,scanner,queryClient,utils}.ts
    │   ├── types/{database,report}.ts
    │   ├── auth/{AuthProvider,LoginPage,AuthCallback,ProtectedRoute}.tsx
    │   ├── components/{ui/*,AppShell,CityPicker,SignalToggles,ScanProgress,StructuredPanel,NarrativeEditor,RegenerateButton,TagInput,CopyMarkdownButton,ReportCard,LibraryFilters,EmptyState}.tsx
    │   ├── pages/{ScannerPage,ReportEditorPage,LibraryPage}.tsx
    │   └── hooks/{useCities,useReports,useReport,useReportEvents,useScan,useRegenerate,useAutosave}.ts
    └── tests/{setup,handlers}.ts
```

**File responsibility rule:** every file does one thing. If a file passes ~200 lines or grows two unrelated responsibilities, split it.

---

## Phase 0: Repo Setup

Goal: working monorepo with `web/` and `server/` skeletons committed.

### Task 0.1: Initialize git repo + root scaffolding

**Files:**
- Create: `.gitignore`
- Create: `.editorconfig`
- Create: `README.md`

- [ ] **Step 1: Initialize git**

```bash
cd "/c/Users/smith/Documents/1 Projects/TerraRealCapital"
git init -b main
```

- [ ] **Step 2: Write `.gitignore`**

```gitignore
node_modules/
.pnpm-store/
dist/
build/
.vite/
*.tsbuildinfo
.env
.env.local
.env.*.local
*.log
.DS_Store
.idea/
.vscode/*
!.vscode/extensions.json
!.vscode/settings.json
Thumbs.db
supabase/.branches/
supabase/.temp/
```

- [ ] **Step 3: Write `.editorconfig`**

```editorconfig
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.md]
trim_trailing_whitespace = false
```

- [ ] **Step 4: Write minimal `README.md`** that points to this plan and explains the `web/` + `server/` + `supabase/` layout. Include a "Quick start" with `pnpm install && pnpm dev` commands per package.

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "chore: initialize repo with editorconfig, gitignore, and README"
```

### Task 0.2: Verify pnpm + Node versions

- [ ] **Step 1:** `node --version` -> v20.x or higher (install via nvm-windows/fnm if lower)
- [ ] **Step 2:** `pnpm --version` -> 9.x or higher (`corepack enable && corepack prepare pnpm@latest --activate`)

---

## Phase 1: Supabase Foundation

Goal: Supabase project provisioned with full schema, RLS, seeded cities, and TypeScript types generated.

### Task 1.1: Create Supabase project (manual)

- [ ] **Step 1:** Dashboard -> "New project". Region `us-east-1`. Project name `trc-research-tool`. Store DB password in 1Password.
- [ ] **Step 2:** From Project Settings -> API, capture: `Project URL`, `anon public` key, `service_role` key. Service-role NEVER ships to the browser.
- [ ] **Step 3:** Auth -> Providers -> Email: enable Magic Link, disable "Confirm email" (internal team).
- [ ] **Step 4:** Auth -> URL Configuration -> Redirect URLs: add `http://localhost:5173/auth/callback`.

### Task 1.2: Install Supabase CLI + link

- [ ] **Step 1:** `pnpm add -g supabase` then `supabase --version` -> 1.x
- [ ] **Step 2:** `supabase init` (creates `supabase/config.toml`)
- [ ] **Step 3:** `supabase link --project-ref <ref>` (project ref is in dashboard URL)
- [ ] **Step 4:** Commit `supabase/config.toml`

### Task 1.3: Initial schema migration

**Files:**
- Create: `supabase/migrations/0001_initial_schema.sql`

- [ ] **Step 1: Write migration**

```sql
-- 0001_initial_schema.sql

create extension if not exists "pgcrypto";

create table public.cities (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  state         text not null,
  fips_county   text not null,
  fips_metro    text not null,
  lat           numeric(9,6),
  lng           numeric(9,6),
  created_at    timestamptz not null default now(),
  unique (name, state)
);

create type report_status as enum ('scanning', 'ready', 'edited', 'published', 'failed');

create table public.reports (
  id                uuid primary key default gen_random_uuid(),
  city_id           uuid not null references public.cities(id) on delete restrict,
  scan_date         date not null default current_date,
  status            report_status not null default 'scanning',
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
  error             text,
  created_by        uuid references auth.users(id),
  edited_by         uuid references auth.users(id),
  created_at        timestamptz not null default now(),
  edited_at         timestamptz
);

create index reports_city_id_idx     on public.reports (city_id);
create index reports_status_idx      on public.reports (status);
create index reports_created_at_desc on public.reports (created_at desc);
create index reports_tags_gin        on public.reports using gin (tags);

create table public.api_cache (
  source        text not null,
  geo_id        text not null,
  period        text not null,
  fetched_on    date not null default current_date,
  payload       jsonb not null,
  created_at    timestamptz not null default now(),
  primary key (source, geo_id, period, fetched_on)
);

create table public.report_events (
  id            bigserial primary key,
  report_id     uuid not null references public.reports(id) on delete cascade,
  event         text not null,
  detail        jsonb,
  created_at    timestamptz not null default now()
);

create index report_events_report_id_idx on public.report_events (report_id, id);

create or replace function public.bump_edited_at() returns trigger language plpgsql as $$
begin
  if (new.narrative_edited is distinct from old.narrative_edited
      or new.tags is distinct from old.tags
      or new.status is distinct from old.status) then
    new.edited_at := now();
  end if;
  return new;
end;
$$;

create trigger reports_bump_edited_at
  before update on public.reports
  for each row execute function public.bump_edited_at();
```

- [ ] **Step 2:** `supabase db push` -> `Finished supabase db push.`
- [ ] **Step 3:** Verify in dashboard -> Database -> Tables: all four tables present.
- [ ] **Step 4:** Commit `git commit -m "feat(db): initial schema"`

### Task 1.4: RLS policies

**Files:**
- Create: `supabase/migrations/0002_rls_policies.sql`

This is an internal team tool. RLS rule: any authenticated user can read/write all rows. Unauthenticated users get nothing.

- [ ] **Step 1: Write migration**

```sql
-- 0002_rls_policies.sql

alter table public.cities         enable row level security;
alter table public.reports        enable row level security;
alter table public.api_cache      enable row level security;
alter table public.report_events  enable row level security;

create policy "cities_read_authenticated"
  on public.cities for select to authenticated using (true);

create policy "reports_all_authenticated"
  on public.reports for all to authenticated
  using (true) with check (true);

create policy "report_events_read_authenticated"
  on public.report_events for select to authenticated using (true);

-- api_cache RLS deliberately not enabled — only service-role scanner reaches it.
```

- [ ] **Step 2:** `supabase db push`
- [ ] **Step 3:** Enable Realtime in dashboard -> Database -> Replication: toggle ON for `report_events` AND `reports`.
- [ ] **Step 4:** Commit.

### Task 1.5: Seed cities

**Files:**
- Create: `supabase/migrations/0003_seed_cities.sql`

- [ ] **Step 1: Write migration**

```sql
-- 0003_seed_cities.sql

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

> FIPS codes verified against Census 2024 MSA delineation files. If any are wrong, the BLS/Census source clients will surface bad-data errors during smoke testing in Task 2.14 — fix them by editing this migration and re-running `supabase db push` after `truncate cities cascade` in dashboard.

- [ ] **Step 2:** `supabase db push`
- [ ] **Step 3:** Verify -> Table Editor -> cities -> 16 rows.
- [ ] **Step 4:** Commit.

### Task 1.6: Generate TypeScript types

- [ ] **Step 1:** `mkdir -p web/src/types && supabase gen types typescript --linked > web/src/types/database.ts`
- [ ] **Step 2:** Commit.
- [ ] **Step 3:** The `db:types` script for re-running this is added in Task 3.1 Step 9; no follow-up needed here.

---

## Phase 2: Node Scanner Service

Goal: a tested Node service that, given `{ city_id, toggled_signals }`, fans out to four external APIs (with caching), calls Claude, writes a complete report row to Supabase, and emits progress events.

**Test discipline:** every source client + cache + claude + orchestrator + routes are written TDD.

### Task 2.1: Scaffold server package

**Files:** `server/package.json`, `server/tsconfig.json`, `server/vitest.config.ts`, `server/.env.example`, `server/Procfile`, `server/src/index.ts` (placeholder)

- [ ] **Step 1:** `mkdir -p server/src server/tests/sources && cd server && pnpm init`
- [ ] **Step 2:** `pnpm add express @anthropic-ai/sdk @supabase/supabase-js zod` then `pnpm add -D typescript tsx vitest @types/node @types/express msw @vitest/coverage-v8 supertest @types/supertest`
- [ ] **Step 3:** Edit `package.json` scripts to: `dev: tsx watch src/index.ts`, `build: tsc -p tsconfig.json`, `start: node dist/index.js`, `test: vitest run`, `test:watch: vitest`. Set `"type": "module"`.
- [ ] **Step 4:** Write `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022", "module": "ES2022", "moduleResolution": "bundler",
    "lib": ["ES2022"], "outDir": "dist", "rootDir": "src",
    "strict": true, "esModuleInterop": true, "skipLibCheck": true,
    "resolveJsonModule": true, "forceConsistentCasingInFileNames": true,
    "noUncheckedIndexedAccess": true
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 5:** Write `vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config';
export default defineConfig({
  test: { environment: 'node', setupFiles: ['./tests/setup.ts'], include: ['tests/**/*.test.ts'] },
});
```

- [ ] **Step 6:** `.env.example` (see Appendix A for full list)
- [ ] **Step 7:** `Procfile`: single line `web: node dist/index.js`
- [ ] **Step 8:** `src/index.ts` placeholder: `console.log('TRC scanner starting...');`
- [ ] **Step 9:** `pnpm dev` -> prints message; Ctrl+C.
- [ ] **Step 10:** Commit.

### Task 2.2: Config + env validation (TDD)

**Files:** `server/src/config.ts`, `server/tests/config.test.ts`, `server/tests/setup.ts`

- [ ] **Step 1:** Empty `tests/setup.ts` (populated next task).
- [ ] **Step 2:** Failing test asserting (a) throws when key env vars missing, (b) returns parsed config when complete. Use `loadConfig` accepting an env object.
- [ ] **Step 3:** Run `pnpm test` -> FAIL.
- [ ] **Step 4:** Implement `src/config.ts` with a zod schema covering: `PORT` (coerced int, default 8787), `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `BLS_API_KEY`, `CENSUS_API_KEY`, `ALLOWED_ORIGIN`. Export `Config` type and `loadConfig(env=process.env): Config`.
- [ ] **Step 5:** PASS. **Step 6:** Commit.

### Task 2.3: MSW test setup

**Files:** Modify `server/tests/setup.ts`, create `server/tests/handlers.ts`

- [ ] **Step 1:** `tests/handlers.ts` exports `handlers: []` (per-test handlers added via `server.use(...)`)
- [ ] **Step 2:** `tests/setup.ts`:

```ts
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { handlers } from './handlers';
export const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

- [ ] **Step 3:** `pnpm test` -> still passes.
- [ ] **Step 4:** Commit.

---

### Task 2.4: BLS source client (TDD)

**Files:** `server/src/sources/bls.ts`, `server/tests/sources/bls.test.ts`

- [ ] **Step 1: Failing test** — uses MSW `http.post` to mock `https://api.bls.gov/publicAPI/v2/timeseries/data/`. Returns 2 data points (current month + same month a year ago). Asserts result has `unemployment_pct` (3.6), `unemployment_yoy_delta_pct` (~-0.3), `as_of` ('2026-02').
- [ ] **Step 2:** `pnpm test bls` -> FAIL
- [ ] **Step 3: Implement**

```ts
// src/sources/bls.ts
export type BlsUnemployment = {
  unemployment_pct: number;
  unemployment_yoy_delta_pct: number;
  as_of: string;
};

export async function fetchBlsUnemployment(p: { countyFips: string; apiKey: string }): Promise<BlsUnemployment> {
  const seriesId = `LAUCN${p.countyFips}0000000003`;
  const res = await fetch('https://api.bls.gov/publicAPI/v2/timeseries/data/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seriesid: [seriesId], registrationkey: p.apiKey }),
  });
  const json = await res.json() as any;
  if (json.status !== 'REQUEST_SUCCEEDED') throw new Error(`BLS error: ${JSON.stringify(json)}`);
  const data = json.Results.series[0].data as Array<{ year: string; period: string; value: string }>;
  const latest = data[0];
  const yearAgo = data.find(d => d.year === String(Number(latest.year) - 1) && d.period === latest.period);
  const latestVal = parseFloat(latest.value);
  return {
    unemployment_pct: latestVal,
    unemployment_yoy_delta_pct: yearAgo ? latestVal - parseFloat(yearAgo.value) : 0,
    as_of: `${latest.year}-${latest.period.slice(1)}`,
  };
}
```

- [ ] **Step 4:** PASS. **Step 5:** Commit.

### Task 2.5: Census source client (TDD)

**Files:** `server/src/sources/census.ts`, `server/tests/sources/census.test.ts`

- [ ] **Step 1: Failing test** mocks `https://api.census.gov/data/2023/acs/acs5`. Returns header row and one data row (population 1326063, renter-occupied 350000, total occupied 720000, MHI 78000). Asserts the parsed result.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: Implement**

```ts
// src/sources/census.ts
export type CensusBasics = { population: number; renter_pct: number; median_household_income: number };

export async function fetchCensusBasics(p: { countyFips: string; apiKey: string }): Promise<CensusBasics> {
  const state = p.countyFips.slice(0, 2);
  const county = p.countyFips.slice(2);
  const vars = ['B01003_001E', 'B25003_003E', 'B25003_001E', 'B19013_001E'].join(',');
  const url = `https://api.census.gov/data/2023/acs/acs5?get=${vars}&for=county:${county}&in=state:${state}&key=${p.apiKey}`;
  const res = await fetch(url);
  const rows = await res.json() as string[][];
  const [headers, values] = rows;
  if (!values) throw new Error('Census returned no data');
  const idx = (k: string) => headers.indexOf(k);
  const pop = parseInt(values[idx('B01003_001E')]!);
  const renter = parseInt(values[idx('B25003_003E')]!);
  const totalOcc = parseInt(values[idx('B25003_001E')]!);
  const mhi = parseInt(values[idx('B19013_001E')]!);
  return { population: pop, renter_pct: (renter / totalOcc) * 100, median_household_income: mhi };
}
```

- [ ] **Step 4:** PASS. **Step 5:** Commit.

### Task 2.6: HUD FMR client (TDD)

**Important runtime note:** HUD's real API requires a Bearer token. Add `HUD_TOKEN` to `Config` (optional). If approval pending at smoke time, the implementation falls back to nulls and Claude handles them.

**Files:** `server/src/sources/hud.ts`, `server/tests/sources/hud.test.ts`

- [ ] **Step 1:** Test (a) happy path returns 1BR/2BR/3BR FMR, (b) 401 returns `{fmr_1br: null, fmr_2br: null, fmr_3br: null}`.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: Implement**

```ts
// src/sources/hud.ts
export type HudFmr = { fmr_1br: number | null; fmr_2br: number | null; fmr_3br: number | null };

export async function fetchHudFmr(p: { metroCbsa: string; countyFips: string; token?: string }): Promise<HudFmr> {
  const id = `METRO${p.metroCbsa}M${p.countyFips}`;
  const headers: Record<string, string> = {};
  if (p.token) headers['Authorization'] = `Bearer ${p.token}`;
  const res = await fetch(`https://www.huduser.gov/hudapi/public/fmr/data/${id}`, { headers });
  if (!res.ok) return { fmr_1br: null, fmr_2br: null, fmr_3br: null };
  const json = await res.json() as any;
  const b = json?.data?.basicdata ?? {};
  return {
    fmr_1br: b['One-Bedroom'] ?? null,
    fmr_2br: b['Two-Bedroom'] ?? null,
    fmr_3br: b['Three-Bedroom'] ?? null,
  };
}
```

- [ ] **Step 4:** PASS. **Step 5:** Commit.

### Task 2.7: USASpending client (TDD)

**Files:** `server/src/sources/usaspending.ts`, `server/tests/sources/usaspending.test.ts`

- [ ] **Step 1:** Test mocks `https://api.usaspending.gov/api/v2/search/spending_by_award/`. Returns 2 awards. Asserts `total_committed_usd` is the sum and `top[0].recipient` is the largest.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: Implement**

```ts
// src/sources/usaspending.ts
export type UsaAward = { recipient: string; amount: number; award_id: string; description: string };
export type UsaSpending = { total_committed_usd: number; top: UsaAward[] };

export async function fetchUsaSpendingTopAwards(p: {
  countyFips: string; months: number; limit: number;
}): Promise<UsaSpending> {
  const start = new Date();
  start.setMonth(start.getMonth() - p.months);
  const state = p.countyFips.slice(0, 2);
  const county = p.countyFips.slice(2);
  const res = await fetch('https://api.usaspending.gov/api/v2/search/spending_by_award/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filters: {
        time_period: [{ start_date: start.toISOString().slice(0, 10), end_date: new Date().toISOString().slice(0, 10) }],
        place_of_performance_locations: [{ country: 'USA', state, county }],
        award_type_codes: ['A', 'B', 'C', 'D', '02', '03', '04', '05'],
      },
      fields: ['Recipient Name', 'Award Amount', 'Award ID', 'Description'],
      sort: 'Award Amount', order: 'desc', limit: p.limit,
    }),
  });
  const json = await res.json() as any;
  const top: UsaAward[] = (json.results ?? []).map((r: any) => ({
    recipient: r['Recipient Name'], amount: r['Award Amount'],
    award_id: r['Award ID'], description: r['Description'] ?? '',
  }));
  return { total_committed_usd: top.reduce((s, a) => s + a.amount, 0), top };
}
```

- [ ] **Step 4:** PASS. **Step 5:** Commit.

---

### Task 2.8: Cache layer + Supabase service client (TDD)

**Files:** `server/src/supabase.ts`, `server/src/cache.ts`, `server/tests/cache.test.ts`

- [ ] **Step 1: Failing test** — two cases: (a) returns cached payload when row exists, (b) calls fetcher + inserts when no row.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: Implement**

```ts
// src/supabase.ts
import { createClient } from '@supabase/supabase-js';
import type { Config } from './config';
export function createServiceClient(c: Config) {
  return createClient(c.supabaseUrl, c.supabaseServiceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}
export type ServiceClient = ReturnType<typeof createServiceClient>;
```

```ts
// src/cache.ts
import type { ServiceClient } from './supabase';
export async function withCache<T>(client: ServiceClient, opts: {
  source: string; geo_id: string; period: string; fetcher: () => Promise<T>;
}): Promise<T> {
  const today = new Date().toISOString().slice(0, 10);
  const { data } = await client.from('api_cache').select('payload')
    .eq('source', opts.source).eq('geo_id', opts.geo_id)
    .eq('period', opts.period).eq('fetched_on', today).maybeSingle();
  if (data?.payload) return data.payload as T;
  const fresh = await opts.fetcher();
  await client.from('api_cache').insert({
    source: opts.source, geo_id: opts.geo_id, period: opts.period, fetched_on: today, payload: fresh,
  });
  return fresh;
}
```

- [ ] **Step 4:** PASS. **Step 5:** Commit.

### Task 2.9: Progress emitter (TDD)

**Files:** `server/src/progress.ts`, `server/tests/progress.test.ts`

- [ ] **Step 1:** Failing test asserting `from('report_events').insert({report_id, event, detail})`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement:

```ts
// src/progress.ts
import type { ServiceClient } from './supabase';
export type ProgressEmitter = (event: string, detail?: Record<string, unknown>) => Promise<void>;
export function createProgressEmitter(client: ServiceClient, reportId: string): ProgressEmitter {
  return async (event, detail) => {
    await client.from('report_events').insert({ report_id: reportId, event, detail: detail ?? null });
  };
}
```

- [ ] **Step 4:** PASS. **Step 5:** Commit.

### Task 2.10: Claude client + system prompt (TDD)

**Files:** `server/src/prompts/system.ts`, `server/src/claude.ts`, `server/tests/claude.test.ts`

This is the heart of the tool: ONE call returns ONE JSON object containing both structured fields AND `narrative_markdown`. Prompt caching on system prompt.

- [ ] **Step 1: Write `src/prompts/system.ts`**

```ts
export const SYSTEM_PROMPT = `You are a multifamily real estate research analyst for Terra Real Capital, a Midwest-focused syndication.

Given evidence from BLS (employment), Census (population, rent burden), HUD (Fair Market Rents), and USASpending (federal capital flows), produce a SINGLE JSON object combining (a) strict structured metrics suitable for cross-city comparison and (b) a long-form newsletter-grade Markdown narrative grounded in the same evidence.

Output schema (return EXACTLY this JSON, no preamble, no code fences):

{
  "score": 0-100 integer,
  "buy_signal": "strong_buy" | "buy" | "hold" | "caution" | "avoid",
  "metrics": {
    "cap_rate_pct": number | null,
    "vacancy_pct": number | null,
    "rent_growth_yoy_pct": number | null,
    "median_rent_2br": number | null,
    "supply_pipeline_units": number | null,
    "deliveries_ttm": number | null,
    "unemployment_pct": number,
    "job_growth_yoy_pct": number | null,
    "gdp_growth_yoy_pct": number | null,
    "population": number,
    "population_growth_yoy_pct": number | null
  },
  "signals": [{ "category": string, "severity": "green"|"amber"|"red", "label": string, "source": string }],
  "capital_flows": {
    "federal_committed_usd": number,
    "private_committed_usd": number | null,
    "notable_projects": [{ "name": string, "size_usd": number | null, "jobs": number | null, "eta": string | null }]
  },
  "submarkets": [{ "name": string, "thesis": string, "vintage_pref": string, "hold_years": string }],
  "lp_takeaway": string,
  "narrative_markdown": string,
  "metrics_extra": object
}

Rules:
- Use null when evidence is insufficient. Never fabricate.
- The narrative_markdown must be 800-1500 words for an LP newsletter, with H2/H3 structure. Cite specific numbers from the evidence ("Franklin County unemployment fell to 3.6% in February 2026" not "unemployment is low").
- The narrative must address ONLY the signals the user toggled on. Skip categories they did not request.
- The lp_takeaway is one paragraph for a passive investor (not an operator), 80-120 words.
- metrics_extra is for AI-discovered numbers not fitting the schema. Use it freely; never use it to omit fields from metrics.
- Output is JSON only. No markdown wrappers, no commentary.`;
```

- [ ] **Step 2: Failing test** — mocks `anthropic.messages.create`, asserts (a) parsed payload, (b) call args include `model: 'claude-sonnet-4-6'` and `system[0].cache_control: { type: 'ephemeral' }`, (c) throws on invalid JSON.
- [ ] **Step 3:** FAIL.
- [ ] **Step 4: Implement `src/claude.ts`**

```ts
import Anthropic from '@anthropic-ai/sdk';
import { SYSTEM_PROMPT } from './prompts/system';

export type ScanReportPayload = {
  score: number;
  buy_signal: 'strong_buy' | 'buy' | 'hold' | 'caution' | 'avoid';
  metrics: Record<string, number | null>;
  signals: Array<{ category: string; severity: 'green'|'amber'|'red'; label: string; source: string }>;
  capital_flows: {
    federal_committed_usd: number;
    private_committed_usd: number | null;
    notable_projects: Array<{ name: string; size_usd: number | null; jobs: number | null; eta: string | null }>;
  };
  submarkets: Array<{ name: string; thesis: string; vintage_pref: string; hold_years: string }>;
  lp_takeaway: string;
  narrative_markdown: string;
  metrics_extra: Record<string, unknown>;
};

export class ScanGenerationError extends Error {}

export async function runScanGeneration(args: {
  anthropic: Anthropic;
  city: { name: string; state: string };
  toggledSignals: string[];
  evidence: Record<string, unknown>;
}): Promise<ScanReportPayload> {
  const userMessage = `City: ${args.city.name}, ${args.city.state}\nUser-toggled signals: ${JSON.stringify(args.toggledSignals)}\n\nEvidence:\n${JSON.stringify(args.evidence, null, 2)}\n\nReturn the JSON object now.`;
  const response = await args.anthropic.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 8000,
    system: [{ type: 'text', text: SYSTEM_PROMPT, cache_control: { type: 'ephemeral' } }],
    messages: [{ role: 'user', content: userMessage }],
  });
  const text = response.content
    .filter((c: any) => c.type === 'text').map((c: any) => c.text).join('');
  try {
    return JSON.parse(text) as ScanReportPayload;
  } catch (err) {
    throw new ScanGenerationError(`Failed to parse Claude JSON: ${(err as Error).message}\nRaw: ${text.slice(0, 500)}`);
  }
}
```

- [ ] **Step 5:** PASS. **Step 6:** Commit.

---

### Task 2.11: Orchestrator (TDD)

**Files:** `server/src/orchestrator.ts`, `server/tests/orchestrator.test.ts`

The orchestrator runs the full scan: parallel fan-out through cache, calls Claude, writes the final row, emits progress along the way.

- [ ] **Step 1: Failing test** — two cases: (a) happy path: fans out 4 source calls, calls generate, writes update with `status: 'ready'`. (b) Claude throws -> writes update with `status: 'failed'` and emits `failed` event; rethrows.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: Implement**

```ts
// src/orchestrator.ts
import type { ServiceClient } from './supabase';
import type { ScanReportPayload } from './claude';
import { createProgressEmitter } from './progress';

export type ScanCity = { id: string; name: string; state: string; fips_county: string; fips_metro: string };
export type ScanSources = {
  bls: (c: ScanCity) => Promise<unknown>;
  census: (c: ScanCity) => Promise<unknown>;
  hud: (c: ScanCity) => Promise<unknown>;
  usa: (c: ScanCity) => Promise<unknown>;
};
export type GenerateFn = (input: {
  city: { name: string; state: string };
  toggledSignals: string[];
  evidence: Record<string, unknown>;
}) => Promise<ScanReportPayload>;

export async function runScan(args: {
  supabase: ServiceClient; sources: ScanSources; generate: GenerateFn;
  reportId: string; city: ScanCity; toggledSignals: string[];
}): Promise<void> {
  const emit = createProgressEmitter(args.supabase, args.reportId);
  await emit('started');
  try {
    await emit('fetching_external');
    const [bls, census, hud, usa] = await Promise.all([
      args.sources.bls(args.city).then(r => (emit('fetched_bls'), r)),
      args.sources.census(args.city).then(r => (emit('fetched_census'), r)),
      args.sources.hud(args.city).then(r => (emit('fetched_hud'), r)),
      args.sources.usa(args.city).then(r => (emit('fetched_usaspending'), r)),
    ]);
    await emit('calling_claude');
    const evidence = { bls, census, hud, usaspending: usa };
    const payload = await args.generate({
      city: { name: args.city.name, state: args.city.state },
      toggledSignals: args.toggledSignals, evidence,
    });
    await args.supabase.from('reports').update({
      status: 'ready',
      metrics: { ...payload.metrics, score: payload.score, buy_signal: payload.buy_signal },
      signals: payload.signals,
      capital_flows: payload.capital_flows,
      submarkets: payload.submarkets,
      evidence, metrics_extra: payload.metrics_extra,
      narrative_raw: payload.narrative_markdown,
      narrative_edited: payload.narrative_markdown,
    }).eq('id', args.reportId);
    await emit('ready');
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    await args.supabase.from('reports').update({ status: 'failed', error: msg }).eq('id', args.reportId);
    await emit('failed', { error: msg });
    throw err;
  }
}
```

- [ ] **Step 4:** PASS. **Step 5:** Commit.

### Task 2.12: Express app + /scan route (TDD)

**Files:** `server/src/routes/scan.ts`, `server/tests/routes.test.ts`, modify `server/src/index.ts`

- [ ] **Step 1: Failing test** with `supertest`: (a) POST /scan with valid body returns 202 + `{report_id}`, then orchestrator called once. (b) POST /scan with empty body returns 400.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: Implement `src/routes/scan.ts`**

```ts
import type { Request, Response } from 'express';
import type { ServiceClient } from '../supabase';
import { z } from 'zod';

const Body = z.object({
  city_id: z.string().uuid(),
  toggled_signals: z.array(z.string()).default([]),
});

// SECURITY NOTE: this route does NOT trust any user identity from the request.
// `created_by` is set to null here. After the scan kicks off, the SPA's `useScan`
// hook does an authenticated Supabase update from the browser to fill in
// `created_by` using the real session JWT (see Task 4.3).

export function buildScanRoute(deps: {
  supabase: ServiceClient;
  orchestrator: (args: { reportId: string; city: any; toggledSignals: string[] }) => Promise<void>;
}) {
  return async (req: Request, res: Response) => {
    const parsed = Body.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });
    const { data: city } = await deps.supabase.from('cities').select('*').eq('id', parsed.data.city_id).single();
    if (!city) return res.status(404).json({ error: 'city not found' });
    const { data: report, error } = await deps.supabase.from('reports').insert({
      city_id: city.id, status: 'scanning', toggled_signals: parsed.data.toggled_signals,
    }).select('id').single();
    if (error || !report) return res.status(500).json({ error: error?.message });
    deps.orchestrator({ reportId: report.id, city, toggledSignals: parsed.data.toggled_signals })
      .catch(() => { /* logged via progress emitter */ });
    res.status(202).json({ report_id: report.id });
  };
}
```

- [ ] **Step 4: Update `src/index.ts`** to expose `buildApp({supabase, orchestrator, allowedOrigin, anthropic})` factory plus `main()` that wires real deps. CORS middleware allows `ALLOWED_ORIGIN`. Health endpoint at `/health`. POSTs at `/scan` and `/regenerate`.
- [ ] **Step 5:** PASS. **Step 6:** Commit.

### Task 2.13: /regenerate route (TDD)

**Files:** `server/src/prompts/regenerate.ts`, `server/src/routes/regenerate.ts`, append to `server/tests/routes.test.ts`

- [ ] **Step 1: Prompt template (`src/prompts/regenerate.ts`)**

```ts
export function buildRegeneratePrompt(args: {
  fullDocument: string; selection: string; instruction: string;
}): string {
  return `Below is the full Markdown document. Then a HIGHLIGHTED SECTION the editor wants rewritten. Then an instruction.

Return ONLY the rewritten section as Markdown. Do not include the surrounding context. Do not add a header unless the original highlighted section had one. Match tone, voice, and length of the original unless the instruction explicitly says otherwise.

=== FULL DOCUMENT ===
${args.fullDocument}

=== HIGHLIGHTED SECTION ===
${args.selection}

=== INSTRUCTION ===
${args.instruction || 'Rewrite this section while keeping the same factual claims.'}

Return the rewritten section now:`;
}
```

- [ ] **Step 2:** Failing test: POST /regenerate with body returns `{text: ...}`.
- [ ] **Step 3:** FAIL.
- [ ] **Step 4: Implement `src/routes/regenerate.ts`**

```ts
import type { Request, Response } from 'express';
import type Anthropic from '@anthropic-ai/sdk';
import { z } from 'zod';
import { buildRegeneratePrompt } from '../prompts/regenerate';

const Body = z.object({
  full_document: z.string().min(1),
  selection: z.string().min(1),
  instruction: z.string().default(''),
});

export function buildRegenerateRoute(deps: { anthropic: Anthropic }) {
  return async (req: Request, res: Response) => {
    const parsed = Body.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });
    const response = await deps.anthropic.messages.create({
      model: 'claude-sonnet-4-6', max_tokens: 2000,
      messages: [{ role: 'user', content: buildRegeneratePrompt({
        fullDocument: parsed.data.full_document,
        selection: parsed.data.selection,
        instruction: parsed.data.instruction,
      }) }],
    });
    const text = response.content
      .filter((c: any) => c.type === 'text').map((c: any) => c.text).join('').trim();
    res.json({ text });
  };
}
```

- [ ] **Step 5:** PASS. **Step 6:** Commit.

### Task 2.14: Live smoke test

- [ ] **Step 1:** Sign up for keys: BLS (instant), Census (instant), USASpending (none), HUD (~1 day).
- [ ] **Step 2:** Fill `server/.env`. Run `pnpm dev`.
- [ ] **Step 3:** Get a city UUID from Supabase Table Editor. Trigger scan via curl with toggled_signals `["jobs","government_investment","multifamily"]`. Expect HTTP 202 in ~200ms.
- [ ] **Step 4:** Watch `report_events` table — events appear in order: started, fetching_external, fetched_bls, fetched_census, fetched_hud, fetched_usaspending, calling_claude, ready. Total ~30-60s.
- [ ] **Step 5:** Inspect report row — `status=ready`, `metrics`, `narrative_raw`, `narrative_edited` populated.
- [ ] **Step 6:** Re-trigger same scan — `api_cache` rows DO NOT increase. Scan still ~10-20s (Claude isn't cached, just APIs).
- [ ] **Step 7: Smoke gate.** Do not advance past Phase 2 until smoke passes.

---

## Phase 3: SPA Shell + Auth

Goal: Vite app with shadcn UI, magic-link auth, protected routes, app shell, and Supabase client wired in. Smoke test: log in via magic link and see an empty placeholder dashboard.

### Task 3.1: Scaffold Vite + Tailwind v4 + shadcn

**Files:** `web/package.json`, `web/tsconfig.json`, `web/vite.config.ts`, `web/index.html`, `web/src/{main,App}.tsx`, `web/src/index.css`, `web/components.json`

- [ ] **Step 1:** From repo root: `pnpm create vite@latest web -- --template react-ts`
- [ ] **Step 2:** `cd web && pnpm install`
- [ ] **Step 3:** Install Tailwind v4: `pnpm add tailwindcss @tailwindcss/vite`
- [ ] **Step 4:** Update `web/vite.config.ts`:

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: { port: 5173 },
});
```

- [ ] **Step 5:** Replace `web/src/index.css`:

```css
@import "tailwindcss";

@theme {
  --color-bg: oklch(0.18 0.01 250);
  --color-fg: oklch(0.95 0.01 250);
  --color-muted: oklch(0.55 0.01 250);
  --color-accent: oklch(0.7 0.15 200);
  --color-amber: oklch(0.78 0.15 80);
  --color-red: oklch(0.62 0.20 25);
  --color-green: oklch(0.72 0.18 145);
}

html, body, #root { height: 100%; background: var(--color-bg); color: var(--color-fg); }
```

- [ ] **Step 6:** Add path alias to `web/tsconfig.json` `compilerOptions`: `"baseUrl": "."`, `"paths": { "@/*": ["./src/*"] }`. Mirror in `tsconfig.app.json` if present.
- [ ] **Step 7:** Initialize shadcn: `pnpm dlx shadcn@latest init` — accept defaults except select "New York" style, base color "Neutral".
- [ ] **Step 8:** Install initial shadcn components: `pnpm dlx shadcn@latest add button input label dialog dropdown-menu select badge card tabs separator scroll-area sheet sonner skeleton`
- [ ] **Step 9:** Add scripts to `web/package.json`: `"db:types": "supabase gen types typescript --linked > src/types/database.ts"`, `"test": "vitest run"`, `"test:watch": "vitest"`.
- [ ] **Step 10:** `pnpm dev` -> visit http://localhost:5173 -> see Vite default page on dark background.
- [ ] **Step 11:** Commit.

### Task 3.2: Supabase + scanner clients + QueryClient

**Files:** `web/src/lib/{supabase,scanner,queryClient,utils}.ts`, `web/.env.example`

- [ ] **Step 1:** `cd web && pnpm add @supabase/supabase-js @tanstack/react-query react-router-dom`
- [ ] **Step 2:** `web/.env.example`:

```
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_SCANNER_URL=http://localhost:8787
```

- [ ] **Step 3:** `web/src/lib/supabase.ts`:

```ts
import { createClient } from '@supabase/supabase-js';
import type { Database } from '@/types/database';
export const supabase = createClient<Database>(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
);
```

- [ ] **Step 4:** `web/src/lib/scanner.ts`:

```ts
const base = import.meta.env.VITE_SCANNER_URL;

export async function postScan(input: { city_id: string; toggled_signals: string[] }): Promise<{ report_id: string }> {
  const res = await fetch(`${base}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Scan failed: ${res.status}`);
  return res.json();
}

export async function postRegenerate(input: {
  full_document: string; selection: string; instruction: string;
}): Promise<{ text: string }> {
  const res = await fetch(`${base}/regenerate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Regenerate failed: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 5:** `web/src/lib/queryClient.ts`:

```ts
import { QueryClient } from '@tanstack/react-query';
export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000, retry: 1, refetchOnWindowFocus: false } },
});
```

- [ ] **Step 6:** Commit.

### Task 3.3: Auth provider + magic-link login

**Files:** `web/src/auth/{AuthProvider,LoginPage,AuthCallback,ProtectedRoute}.tsx`

- [ ] **Step 1:** `AuthProvider.tsx`:

```tsx
import { createContext, useContext, useEffect, useState } from 'react';
import type { Session } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';

type Ctx = { session: Session | null; loading: boolean };
const AuthCtx = createContext<Ctx>({ session: null, loading: true });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setLoading(false); });
    const { data: sub } = supabase.auth.onAuthStateChange((_, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);
  return <AuthCtx.Provider value={{ session, loading }}>{children}</AuthCtx.Provider>;
}
export const useAuth = () => useContext(AuthCtx);
```

- [ ] **Step 2:** `LoginPage.tsx` — react-hook-form + zod for the email field. On submit: `supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: window.location.origin + '/auth/callback' } })`. Show success toast via sonner: "Check your inbox for the magic link." If error, show error toast.

- [ ] **Step 3:** `AuthCallback.tsx`:

```tsx
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/lib/supabase';

export function AuthCallback() {
  const navigate = useNavigate();
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      navigate(data.session ? '/library' : '/login', { replace: true });
    });
  }, [navigate]);
  return <div className="p-8 text-muted">Signing you in…</div>;
}
```

- [ ] **Step 4:** `ProtectedRoute.tsx`:

```tsx
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthProvider';

export function ProtectedRoute() {
  const { session, loading } = useAuth();
  if (loading) return <div className="p-8 text-muted">Loading…</div>;
  return session ? <Outlet /> : <Navigate to="/login" replace />;
}
```

- [ ] **Step 5:** Commit.

### Task 3.4: App shell + routing

**Files:** `web/src/App.tsx`, `web/src/main.tsx`, `web/src/components/AppShell.tsx`

- [ ] **Step 1:** `main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/sonner';
import { queryClient } from '@/lib/queryClient';
import { AuthProvider } from '@/auth/AuthProvider';
import App from './App';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <App />
          <Toaster />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </StrictMode>,
);
```

- [ ] **Step 2:** `App.tsx`:

```tsx
import { Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from '@/auth/ProtectedRoute';
import { LoginPage } from '@/auth/LoginPage';
import { AuthCallback } from '@/auth/AuthCallback';
import { AppShell } from '@/components/AppShell';
import { ScannerPage } from '@/pages/ScannerPage';
import { ReportEditorPage } from '@/pages/ReportEditorPage';
import { LibraryPage } from '@/pages/LibraryPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/library" replace />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/scanner" element={<ScannerPage />} />
          <Route path="/reports/:id" element={<ReportEditorPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
```

- [ ] **Step 3:** `AppShell.tsx` — header with logo "TRC Research" + sign-out button (calls `supabase.auth.signOut()`), left nav with two links: "Library", "New scan". `<Outlet />` for the page content.
- [ ] **Step 4:** Stub `ScannerPage`, `ReportEditorPage`, `LibraryPage` files in `web/src/pages/` returning a single `<div>` placeholder with the page name.
- [ ] **Step 5:** Smoke: `pnpm dev`. Visit `/`. Expected redirect to `/login`. Submit your email. Click the magic link in inbox. Land on `/library` with the placeholder shown.
- [ ] **Step 6:** Commit.

---

## Phase 4: Scanner Screen

Goal: pick city + signals, fire scan, watch live progress, navigate to report when ready.

### Task 4.1: useCities hook

**Files:** `web/src/hooks/useCities.ts`, `web/src/types/report.ts`

- [ ] **Step 1:** `web/src/types/report.ts` — hand-written narrow types matching the JSON shape Claude returns:

```ts
export type SignalSeverity = 'green' | 'amber' | 'red';
export type BuySignal = 'strong_buy' | 'buy' | 'hold' | 'caution' | 'avoid';
export type ReportStatus = 'scanning' | 'ready' | 'edited' | 'published' | 'failed';

export type Metrics = {
  score?: number;
  buy_signal?: BuySignal;
  cap_rate_pct: number | null;
  vacancy_pct: number | null;
  rent_growth_yoy_pct: number | null;
  median_rent_2br: number | null;
  supply_pipeline_units: number | null;
  deliveries_ttm: number | null;
  unemployment_pct: number;
  job_growth_yoy_pct: number | null;
  gdp_growth_yoy_pct: number | null;
  population: number;
  population_growth_yoy_pct: number | null;
};

export type Signal = { category: string; severity: SignalSeverity; label: string; source: string };

export type CapitalFlows = {
  federal_committed_usd: number;
  private_committed_usd: number | null;
  notable_projects: Array<{ name: string; size_usd: number | null; jobs: number | null; eta: string | null }>;
};

export type Submarket = { name: string; thesis: string; vintage_pref: string; hold_years: string };
```

- [ ] **Step 2:** Hook:

```ts
// hooks/useCities.ts
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

export function useCities() {
  return useQuery({
    queryKey: ['cities'],
    queryFn: async () => {
      const { data, error } = await supabase.from('cities').select('*').order('name');
      if (error) throw error;
      return data;
    },
  });
}
```

- [ ] **Step 3:** Commit.

### Task 4.2: SignalToggles + CityPicker components

**Files:** `web/src/components/{SignalToggles,CityPicker}.tsx`

- [ ] **Step 1:** Define the canonical signal list (constant):

```ts
// web/src/lib/signals.ts
export const SIGNAL_OPTIONS = [
  { id: 'jobs',                  label: 'Jobs & employment' },
  { id: 'government_investment', label: 'Government investment' },
  { id: 'private_investment',    label: 'Private investment' },
  { id: 'healthcare',            label: 'Healthcare' },
  { id: 'population',            label: 'Population & demographics' },
  { id: 'multifamily',           label: 'Multifamily fundamentals' },
  { id: 'risk',                  label: 'Risk flags' },
] as const;
export type SignalId = typeof SIGNAL_OPTIONS[number]['id'];
```

- [ ] **Step 2:** `SignalToggles.tsx` — controlled component, renders 7 shadcn `<Checkbox>` rows from `SIGNAL_OPTIONS`. Props: `{value: string[], onChange: (next: string[]) => void}`.
- [ ] **Step 3:** `CityPicker.tsx` — shadcn `<Select>` driven by `useCities()`. Props: `{value: string | null, onChange: (id: string) => void}`.
- [ ] **Step 4:** Commit.

### Task 4.3: useScan mutation hook

**Files:** `web/src/hooks/useScan.ts`

- [ ] **Step 1:** Implement:

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';
import { supabase } from '@/lib/supabase';
import { postScan } from '@/lib/scanner';

export function useScan() {
  const qc = useQueryClient();
  const nav = useNavigate();
  const { session } = useAuth();
  return useMutation({
    mutationFn: async (input: { city_id: string; toggled_signals: string[] }) => {
      const { report_id } = await postScan(input);
      // Authenticated update sets created_by from the real session, not a header.
      // RLS allows authenticated users to update reports.
      if (session?.user.id) {
        await supabase.from('reports').update({ created_by: session.user.id }).eq('id', report_id);
      }
      return { report_id };
    },
    onSuccess: ({ report_id }) => {
      qc.invalidateQueries({ queryKey: ['reports'] });
      nav(`/reports/${report_id}`);
    },
  });
}
```

- [ ] **Step 2:** Commit.

### Task 4.4: ScannerPage

**Files:** `web/src/pages/ScannerPage.tsx`

- [ ] **Step 1:** Implement the page:

```tsx
import { useState } from 'react';
import { CityPicker } from '@/components/CityPicker';
import { SignalToggles } from '@/components/SignalToggles';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useScan } from '@/hooks/useScan';

export function ScannerPage() {
  const [cityId, setCityId] = useState<string | null>(null);
  const [signals, setSignals] = useState<string[]>(['jobs', 'multifamily']);
  const scan = useScan();
  return (
    <div className="mx-auto max-w-2xl p-6 space-y-6">
      <Card>
        <CardHeader><CardTitle>New scan</CardTitle></CardHeader>
        <CardContent className="space-y-6">
          <CityPicker value={cityId} onChange={setCityId} />
          <SignalToggles value={signals} onChange={setSignals} />
          <Button
            disabled={!cityId || signals.length === 0 || scan.isPending}
            onClick={() => scan.mutate({ city_id: cityId!, toggled_signals: signals })}
          >
            {scan.isPending ? 'Starting...' : 'Run scan'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2:** Smoke: load `/scanner`, pick a city, toggle a signal, click "Run scan". Should navigate to `/reports/<id>` (the placeholder editor).
- [ ] **Step 3:** Commit.

### Task 4.5: useReportEvents Realtime hook + ScanProgress component

**Files:** `web/src/hooks/useReportEvents.ts`, `web/src/components/ScanProgress.tsx`

- [ ] **Step 1: Hook**

```ts
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export type ReportEvent = { id: number; report_id: string; event: string; detail: any; created_at: string };

export function useReportEvents(reportId: string | undefined) {
  const [events, setEvents] = useState<ReportEvent[]>([]);
  useEffect(() => {
    if (!reportId) return;
    let cancelled = false;
    supabase.from('report_events').select('*').eq('report_id', reportId).order('id').then(({ data }) => {
      if (!cancelled && data) setEvents(data as ReportEvent[]);
    });
    const channel = supabase.channel(`report:${reportId}`)
      .on('postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'report_events', filter: `report_id=eq.${reportId}` },
        (payload) => setEvents(prev => [...prev, payload.new as ReportEvent]))
      .subscribe();
    return () => { cancelled = true; supabase.removeChannel(channel); };
  }, [reportId]);
  return events;
}
```

- [ ] **Step 2: ScanProgress**

```tsx
// components/ScanProgress.tsx
import { useReportEvents } from '@/hooks/useReportEvents';

const STEPS = [
  ['started', 'Starting scan'],
  ['fetched_bls', 'Pulled BLS unemployment data'],
  ['fetched_census', 'Pulled Census demographics'],
  ['fetched_hud', 'Pulled HUD rent benchmarks'],
  ['fetched_usaspending', 'Pulled federal capital flows'],
  ['calling_claude', 'Generating report with Claude'],
  ['ready', 'Report ready'],
] as const;

export function ScanProgress({ reportId }: { reportId: string }) {
  const events = useReportEvents(reportId);
  const seen = new Set(events.map(e => e.event));
  return (
    <ul className="space-y-2 text-sm">
      {STEPS.map(([key, label]) => (
        <li key={key} className={seen.has(key) ? 'text-fg' : 'text-muted'}>
          {seen.has(key) ? '✓' : '○'} {label}
        </li>
      ))}
      {seen.has('failed') && <li className="text-red">✗ Scan failed</li>}
    </ul>
  );
}
```

- [ ] **Step 3:** Commit.

---

## Phase 5: Report Editor Screen

> **Realtime prerequisite:** Before this phase, confirm in the Supabase dashboard (Database -> Replication) that BOTH `report_events` AND `reports` have replication toggled ON. This was set in Task 1.4 Step 3 but is easy to forget if the project was re-initialized. The Realtime subscriptions in Tasks 4.5 and 5.1 silently produce zero updates if either is off.

Goal: Read-only structured panel + editable Markdown narrative side-by-side. Highlight-to-regenerate. Tagging. Copy-to-Beehiiv. Live progress while still scanning.

### Task 5.1: useReport hook + Realtime subscription on report row

**Files:** `web/src/hooks/useReport.ts`

- [ ] **Step 1:** Implement (combines initial fetch + Realtime UPDATEs):

```ts
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export function useReport(id: string | undefined) {
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    supabase.from('reports').select('*, cities(name, state, fips_county, fips_metro)').eq('id', id).single()
      .then(({ data }) => { if (!cancelled) { setData(data); setLoading(false); } });
    const channel = supabase.channel(`reports:${id}`)
      .on('postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'reports', filter: `id=eq.${id}` },
        (payload) => setData((prev: any) => ({ ...prev, ...payload.new })))
      .subscribe();
    return () => { cancelled = true; supabase.removeChannel(channel); };
  }, [id]);
  return { data, loading };
}
```

- [ ] **Step 2:** Commit.

### Task 5.2: StructuredPanel component (read-only metrics + signals + capital flows)

**Files:** `web/src/components/StructuredPanel.tsx`

- [ ] **Step 1:** Implement. Renders:
  - **Header:** city name + state + scan date + status badge
  - **Score:** big number 0–100 + buy_signal pill (green for buy/strong_buy, amber for hold/caution, red for avoid)
  - **Metrics grid** (2 cols × 5 rows): cap_rate, vacancy, rent_growth, median_rent_2br, supply_pipeline, deliveries_ttm, unemployment, job_growth, population, population_growth. Each cell shows the value (formatted: % vs $ vs raw int) and label. Null values render as `—` in muted color.
  - **Signals:** chip list grouped by category, colored dot per severity.
  - **Capital flows:** federal_committed_usd big number + private_committed_usd next to it; notable_projects as compact list rows (name, size, jobs, eta).
  - **Submarkets:** small table — name, thesis, vintage_pref, hold_years.

Pure presentation. No autosave logic here. Use shadcn `Card`, `Badge`, `Separator`. Keep file under 200 lines.

- [ ] **Step 2:** Commit.

### Task 5.3: Install MDXEditor + NarrativeEditor wrapper

**Files:** `web/src/components/NarrativeEditor.tsx`

- [ ] **Step 1:** `cd web && pnpm add @mdxeditor/editor`
- [ ] **Step 2:** Implement:

```tsx
import { useEffect, useRef } from 'react';
import {
  MDXEditor, headingsPlugin, listsPlugin, quotePlugin, markdownShortcutPlugin,
  thematicBreakPlugin, linkPlugin, tablePlugin, toolbarPlugin,
  UndoRedo, BoldItalicUnderlineToggles, BlockTypeSelect, ListsToggle, CreateLink, InsertTable,
  type MDXEditorMethods,
} from '@mdxeditor/editor';
import '@mdxeditor/editor/style.css';

export function NarrativeEditor({ markdown, onChange }: {
  markdown: string;
  onChange: (md: string) => void;
}) {
  const ref = useRef<MDXEditorMethods>(null);
  // Re-sync when an external update arrives (e.g., regenerate)
  useEffect(() => { if (ref.current && ref.current.getMarkdown() !== markdown) ref.current.setMarkdown(markdown); }, [markdown]);
  return (
    <MDXEditor
      ref={ref}
      markdown={markdown}
      onChange={onChange}
      contentEditableClassName="prose prose-invert max-w-none p-6"
      plugins={[
        headingsPlugin(), listsPlugin(), quotePlugin(), thematicBreakPlugin(),
        linkPlugin(), tablePlugin(), markdownShortcutPlugin(),
        toolbarPlugin({
          toolbarContents: () => (
            <>
              <UndoRedo />
              <BoldItalicUnderlineToggles />
              <BlockTypeSelect />
              <ListsToggle />
              <CreateLink />
              <InsertTable />
            </>
          ),
        }),
      ]}
    />
  );
}
```

- [ ] **Step 3:** Commit.

### Task 5.4: Autosave hook

**Files:** `web/src/hooks/useAutosave.ts`

Debounced save that writes `narrative_edited` (and optionally `tags`/`status`) to Supabase. Uses 1.2s debounce.

- [ ] **Step 1:** Implement:

```ts
import { useEffect, useRef } from 'react';
import { supabase } from '@/lib/supabase';
import { useAuth } from '@/auth/AuthProvider';
import { toast } from 'sonner';

export function useAutosave(reportId: string | undefined, patch: Record<string, unknown>) {
  const { session } = useAuth();
  const timer = useRef<number | null>(null);
  const last = useRef<string>('');
  useEffect(() => {
    if (!reportId) return;
    const serialized = JSON.stringify(patch);
    if (serialized === last.current) return;
    last.current = serialized;
    if (timer.current) clearTimeout(timer.current);
    timer.current = window.setTimeout(async () => {
      const { error } = await supabase
        .from('reports')
        .update({ ...patch, edited_by: session?.user.id ?? null })
        .eq('id', reportId);
      if (error) toast.error('Save failed');
    }, 1200);
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [reportId, JSON.stringify(patch)]);
}
```

- [ ] **Step 2:** Commit.

### Task 5.5: TagInput + CopyMarkdownButton

**Files:** `web/src/components/{TagInput,CopyMarkdownButton}.tsx`

- [ ] **Step 1:** `TagInput.tsx` — controlled chip input. On Enter or comma, push value to `tags`. Backspace on empty input removes last tag. Suggestions popover queries `select('tags').eq('user has any')` — for v1 just dedupe from user's recent reports loaded via TanStack Query; if too slow, just allow free text and skip autocomplete.
- [ ] **Step 2:** `CopyMarkdownButton.tsx` — shadcn button; on click `await navigator.clipboard.writeText(markdown)`, then `toast.success('Markdown copied. Paste into Beehiiv.')`.
- [ ] **Step 3:** Commit.

### Task 5.6: RegenerateButton (highlight-to-regenerate)

**Files:** `web/src/components/RegenerateButton.tsx`, `web/src/hooks/useRegenerate.ts`

- [ ] **Step 1: Hook**

```ts
import { useMutation } from '@tanstack/react-query';
import { postRegenerate } from '@/lib/scanner';
export function useRegenerate() {
  return useMutation({
    mutationFn: (input: { full_document: string; selection: string; instruction: string }) => postRegenerate(input),
  });
}
```

- [ ] **Step 2: Component** — listens to `selectionchange` on document. When the selection lies inside the editor's container AND length > 20 chars, position a small floating popover near the selection's bounding rect with: an `<input>` for instruction (placeholder "Make it more cautious") and a "Regenerate" button. On click, call `useRegenerate().mutate({ full_document, selection, instruction })`. On success, do a string replace on the parent's markdown state (`markdown.replace(selection, response.text)`).

```tsx
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useRegenerate } from '@/hooks/useRegenerate';

export function RegenerateButton({ markdown, onApply }: {
  markdown: string;
  onApply: (next: string) => void;
}) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const [selection, setSelection] = useState('');
  const [instruction, setInstruction] = useState('');
  const regenerate = useRegenerate();

  useEffect(() => {
    const handler = () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) { setPos(null); return; }
      const text = sel.toString().trim();
      if (text.length < 20) { setPos(null); return; }
      const editor = document.querySelector('.mdxeditor');
      if (!editor || !editor.contains(sel.anchorNode)) { setPos(null); return; }
      const rect = sel.getRangeAt(0).getBoundingClientRect();
      setPos({ x: rect.left, y: rect.bottom + window.scrollY + 8 });
      setSelection(text);
    };
    document.addEventListener('selectionchange', handler);
    return () => document.removeEventListener('selectionchange', handler);
  }, []);

  if (!pos) return null;
  return (
    <div style={{ position: 'absolute', left: pos.x, top: pos.y }}
         className="z-50 flex gap-2 rounded-md bg-bg shadow-lg border p-2">
      <Input value={instruction} onChange={e => setInstruction(e.target.value)} placeholder="Rewrite instruction..." className="w-64" />
      <Button
        size="sm"
        disabled={regenerate.isPending}
        onClick={async () => {
          const occurrences = markdown.split(selection).length - 1;
          if (occurrences === 0) {
            toast.error('Could not locate the highlighted text in the source markdown.');
            return;
          }
          if (occurrences > 1) {
            toast.error('Highlighted text appears more than once in the document. Edit one occurrence to make it unique, then re-select.');
            return;
          }
          const r = await regenerate.mutateAsync({ full_document: markdown, selection, instruction });
          onApply(markdown.replace(selection, r.text));
          setPos(null);
        }}
      >
        {regenerate.isPending ? 'Rewriting...' : 'Regenerate'}
      </Button>
    </div>
  );
}
```

- [ ] **Step 3:** Commit.

### Task 5.7: ReportEditorPage — assemble everything

**Files:** `web/src/pages/ReportEditorPage.tsx`

- [ ] **Step 1:** Implement:

```tsx
import { useParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useReport } from '@/hooks/useReport';
import { useAutosave } from '@/hooks/useAutosave';
import { ScanProgress } from '@/components/ScanProgress';
import { StructuredPanel } from '@/components/StructuredPanel';
import { NarrativeEditor } from '@/components/NarrativeEditor';
import { RegenerateButton } from '@/components/RegenerateButton';
import { TagInput } from '@/components/TagInput';
import { CopyMarkdownButton } from '@/components/CopyMarkdownButton';

export function ReportEditorPage() {
  const { id } = useParams<{ id: string }>();
  const { data: report, loading } = useReport(id);
  const [markdown, setMarkdown] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  useEffect(() => {
    if (report?.narrative_edited) setMarkdown(report.narrative_edited);
    if (report?.tags) setTags(report.tags);
  }, [report?.narrative_edited, report?.tags]);

  useAutosave(id, {
    narrative_edited: markdown,
    tags,
    status: report?.status === 'ready' ? 'edited' : report?.status,
  });

  if (loading || !report) return <div className="p-6 text-muted">Loading…</div>;
  if (report.status === 'scanning' || report.status === 'failed') {
    return (
      <div className="p-6 max-w-md mx-auto space-y-4">
        <h1 className="text-lg font-semibold">{report.cities.name}, {report.cities.state}</h1>
        <ScanProgress reportId={report.id} />
      </div>
    );
  }
  return (
    <div className="grid grid-cols-12 gap-6 p-6">
      <aside className="col-span-4 space-y-4">
        <StructuredPanel report={report} />
      </aside>
      <main className="col-span-8 space-y-4">
        <div className="flex items-center justify-between gap-4">
          <TagInput value={tags} onChange={setTags} />
          <CopyMarkdownButton markdown={markdown} />
        </div>
        <div className="rounded-md border bg-bg/50 relative">
          <NarrativeEditor markdown={markdown} onChange={setMarkdown} />
          <RegenerateButton markdown={markdown} onApply={setMarkdown} />
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 2:** Smoke: trigger a scan from `/scanner`, watch progress in editor, see structured panel + editable narrative once `ready`. Edit a paragraph -> wait 1.2s -> see `edited_at` change in Supabase. Highlight a paragraph -> regenerate popover appears -> click "Regenerate" -> selection replaced with new text. Click "Copy Markdown" -> paste into a text editor, looks clean.
- [ ] **Step 3:** Commit.

---

## Phase 6: Library Screen

Goal: filter + browse all reports. Click a card -> editor.

### Task 6.1: useReports hook with filters

**Files:** `web/src/hooks/useReports.ts`

- [ ] **Step 1:** Implement:

```ts
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

export type ReportFilters = { city_id?: string; status?: string; tag?: string };

export function useReports(filters: ReportFilters) {
  return useQuery({
    queryKey: ['reports', filters],
    queryFn: async () => {
      let q = supabase.from('reports')
        .select('id, city_id, scan_date, status, metrics, tags, created_at, edited_at, cities(name, state)')
        .order('created_at', { ascending: false }).limit(100);
      if (filters.city_id) q = q.eq('city_id', filters.city_id);
      if (filters.status) q = q.eq('status', filters.status);
      if (filters.tag) q = q.contains('tags', [filters.tag]);
      const { data, error } = await q;
      if (error) throw error;
      return data;
    },
  });
}
```

- [ ] **Step 2:** Commit.

### Task 6.2: ReportCard + LibraryFilters + EmptyState components

**Files:** `web/src/components/{ReportCard,LibraryFilters,EmptyState}.tsx`

- [ ] **Step 1:** `ReportCard.tsx` — clickable card showing city/state, score (big), buy_signal badge, scan date, top 3 signals as small dots+labels, tag chips. `Link` to `/reports/:id`. Uses shadcn Card.
- [ ] **Step 2:** `LibraryFilters.tsx` — three controls in a row: city Select (uses `useCities`), status Select (`scanning` | `ready` | `edited` | `published` | `failed` | `all`), tag Input. Controlled via parent state.
- [ ] **Step 3:** `EmptyState.tsx` — generic empty state with title, body, CTA button. Used in Library when no reports match filters.
- [ ] **Step 4:** Commit.

### Task 6.3: LibraryPage

**Files:** `web/src/pages/LibraryPage.tsx`

- [ ] **Step 1:** Implement:

```tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { LibraryFilters } from '@/components/LibraryFilters';
import { ReportCard } from '@/components/ReportCard';
import { EmptyState } from '@/components/EmptyState';
import { useReports, type ReportFilters } from '@/hooks/useReports';

export function LibraryPage() {
  const [filters, setFilters] = useState<ReportFilters>({});
  const { data: reports, isLoading } = useReports(filters);
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Library</h1>
        <Button asChild><Link to="/scanner">New scan</Link></Button>
      </div>
      <LibraryFilters value={filters} onChange={setFilters} />
      {isLoading ? <div className="text-muted">Loading…</div> :
        reports && reports.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {reports.map(r => <ReportCard key={r.id} report={r} />)}
          </div>
        ) : (
          <EmptyState title="No reports yet" body="Run your first scan to populate the library." cta={<Link to="/scanner"><Button>Run a scan</Button></Link>} />
        )}
    </div>
  );
}
```

- [ ] **Step 2:** Smoke: visit `/library` -> see all scans run so far. Filter by city -> list narrows. Click a card -> editor opens.
- [ ] **Step 3:** Commit.

---

## Phase 7: Deploy + End-to-End Smoke

### Task 7.1: Deploy SPA to Vercel

- [ ] **Step 1:** Push repo to GitHub (private).
- [ ] **Step 2:** Vercel: New Project -> import the repo. Set root directory to `web/`. Framework: Vite.
- [ ] **Step 3:** Add env vars in Vercel project settings: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_SCANNER_URL` (placeholder, will be set after Railway). Deploy.
- [ ] **Step 4:** Add the production Vercel domain to Supabase Auth -> URL Configuration -> Redirect URLs: `https://<vercel-domain>/auth/callback`.
- [ ] **Step 5:** Confirm production SPA loads, magic-link login works, library page renders.

### Task 7.2: Deploy scanner to Railway

- [ ] **Step 1:** railway.app -> New Project -> Deploy from GitHub. Set root to `server/`.
- [ ] **Step 2:** Set env vars: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `BLS_API_KEY`, `CENSUS_API_KEY`, optional `HUD_TOKEN`, `ALLOWED_ORIGIN=https://<vercel-domain>`, `PORT=8787` (Railway will inject `PORT` itself; the config defaults to 8787 if absent).
- [ ] **Step 3:** Build command: `pnpm install --frozen-lockfile && pnpm build`. Start command: `node dist/index.js`.
- [ ] **Step 4:** Wait for deploy. Get the Railway public URL.
- [ ] **Step 5:** Set Vercel `VITE_SCANNER_URL` to the Railway URL. Redeploy SPA.
- [ ] **Step 6:** `curl https://<railway-url>/health` -> `{"ok":true}`.

### Task 7.3: End-to-end smoke

- [ ] **Step 1:** Open production SPA. Sign in via magic link.
- [ ] **Step 2:** Run a scan on Columbus with all 7 signals. Watch live progress.
- [ ] **Step 3:** When ready, edit a paragraph in the narrative. Wait 2 seconds. Reload — edits persisted.
- [ ] **Step 4:** Highlight a paragraph -> "Regenerate" with instruction "more cautious" -> selection replaced with new text.
- [ ] **Step 5:** Click "Copy Markdown". Paste into a Beehiiv post draft. Headings, lists, links render.
- [ ] **Step 6:** Tag the report `q2-2026, columbus-deep-dive`. Visit `/library`. Filter by tag `columbus-deep-dive` -> the report appears. Click -> back to editor with content intact.
- [ ] **Step 7:** Tag git: `git tag v1.0.0 && git push origin v1.0.0`. Final commit message: "release: v1.0.0 — internal research tool MVP".

---

## Definition of Done (v1)

- [ ] Magic-link login works in production
- [ ] All 16 cities are scannable
- [ ] A full scan completes in under 90s and produces both structured metrics AND a 800-1500 word narrative
- [ ] Cache prevents repeat external calls within the same day
- [ ] Realtime progress visible during scan
- [ ] Narrative is editable with autosave
- [ ] Highlight-to-regenerate works on paragraphs of 20+ chars
- [ ] Copy Markdown button puts clean Beehiiv-pasteable Markdown on the clipboard
- [ ] Tags can be added; Library filter narrows by tag
- [ ] Library shows all reports created by all team members
- [ ] No service role key is ever shipped to the browser (verify by inspecting bundled JS)
- [ ] All TDD-tagged tasks have passing tests; `cd server && pnpm test` is green
- [ ] Deployed: Vercel SPA + Railway scanner + Supabase managed DB

---

## Out of v1 (build later)

- Watchlist dashboard with metric tiles
- 2-3 city Comparison view (charts via Tremor)
- Diff view: same city across two scans
- Newsletter Assembly: pick N reports -> single Beehiiv-bound draft
- Settings UI for team invites
- Beehiiv API direct publishing
- PDF export
- Mobile-optimized layout
- E2E Playwright tests

---

## Appendix A: Server `.env.example` keys

The following keys are required by `server/src/config.ts`. Each is validated by zod at boot — the server will refuse to start if any are missing.

| Key | Source | Notes |
|---|---|---|
| `PORT` | local | Default 8787; Railway injects its own |
| `ANTHROPIC_API_KEY` | console.anthropic.com | Server-side only — never commit |
| `SUPABASE_URL` | Supabase dashboard | Project Settings -> API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase dashboard | Project Settings -> API. Server-only. NEVER ship to browser |
| `BLS_API_KEY` | data.bls.gov | Free, instant |
| `CENSUS_API_KEY` | api.census.gov | Free, instant |
| `HUD_TOKEN` (optional) | huduser.gov | ~1 day approval; nullable in v1 |
| `ALLOWED_ORIGIN` | local/Railway | `http://localhost:5173` in dev; `https://<vercel-domain>` in prod |

## Appendix B: Web `.env.example` keys

| Key | Source | Notes |
|---|---|---|
| `VITE_SUPABASE_URL` | Supabase dashboard | Project Settings -> API |
| `VITE_SUPABASE_ANON_KEY` | Supabase dashboard | Public anon key — safe to ship to browser |
| `VITE_SCANNER_URL` | Railway | `http://localhost:8787` in dev; `https://<railway-domain>` in prod |

## Appendix C: Engineering principles for this build

- **DRY** — one source of truth for each concept. Signal IDs in `web/src/lib/signals.ts`, types in `web/src/types/report.ts`, system prompt in `server/src/prompts/system.ts`. Don't duplicate.
- **YAGNI** — if it's listed in "Out of v1," do not build hooks for it now. The point of cutting scope is to stop thinking about it.
- **TDD where it matters** — every server-side module is RED -> GREEN -> COMMIT. UI components rely on smoke testing in the browser; do not write Vitest/RTL tests for purely visual components in v1.
- **Frequent commits** — every task ends in a commit. Each commit message follows Conventional Commits (`feat`, `fix`, `chore`, `docs`, `test`).
- **No premature abstraction** — three similar lines beats a wrong abstraction. If two clients share 90% structure, leave them as two clients until a third one shows the pattern.
- **No over-engineering of error handling** — show a toast, log to console, move on. Internal tool, 5 users; we are not building Stripe.

## Appendix D: Skills referenced

- @superpowers:test-driven-development — for every TDD task in Phase 2
- @superpowers:subagent-driven-development — recommended execution path
- @superpowers:executing-plans — alternative inline execution
- @superpowers:verification-before-completion — mandatory before marking any phase complete
- @superpowers:requesting-code-review — recommended after Phases 2, 5, and 7

---

*End of plan.*
