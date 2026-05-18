# Supabase Setup Guide

Audience: the internal team standing up Terra Real Capital Research Tool. No prior
Supabase experience required. Following this gives you the two Supabase values the
app needs, plus the other API keys, all landed in the right places.

> **Time:** ~15 minutes. **You will end up with:** `SUPABASE_URL` and
> `SUPABASE_SERVICE_ROLE_KEY`, the database schema applied, and a working `.env`.

---

## 0. The five secrets this app needs

| Variable | What it is | Where you get it |
|---|---|---|
| `SUPABASE_URL` | Your Supabase project URL | Supabase dashboard (steps below) |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin DB key (server-side only) | Supabase dashboard (steps below) |
| `PERPLEXITY_API_KEY` | City-research API | https://www.perplexity.ai/settings/api |
| `ANTHROPIC_API_KEY` | Report-writing (Claude) API | https://console.anthropic.com/ → API Keys |
| `APP_PASSWORD` | Shared login password for the tool | You choose it |

This guide focuses on the two Supabase values; the rest are quick external signups
linked above. All five go into the same places (see section 5).

---

## 1. Create the Supabase project

1. Go to <https://supabase.com> and sign in (create a free account if needed).
   If the company already has a Supabase **organization**, ask to be added to it
   so the project lives under the company account, not a personal one.
2. Click **New project**.
3. Fill in:
   - **Name:** `trc-research-tool`
   - **Database Password:** click *Generate a password*, then **save it in the
     team password manager immediately**. You will rarely need it again, but it
     cannot be recovered later — only reset.
   - **Region:** `East US (North Virginia)` / `us-east-1`.
   - Plan: Free is fine for this internal tool.
4. Click **Create new project** and wait ~2 minutes for it to provision.

---

## 2. Get `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`

1. In the project, open **Project Settings** (gear icon, bottom-left) → **API**.
2. **Project URL** — copy it. This is `SUPABASE_URL`
   (looks like `https://abcdefghijklmn.supabase.co`).
3. Under **Project API keys**, find **`service_role`** (it is hidden behind a
   *Reveal* / copy button and labelled *secret*). Copy it. This is
   `SUPABASE_SERVICE_ROLE_KEY`.

> ⚠️ **The `service_role` key is an admin key.** It bypasses all row-level
> security. It must live only on the server (our Streamlit backend), never in a
> browser, a public repo, chat, or email. If it ever leaks, rotate it from this
> same page. You do **not** need the `anon` key — this app does not use it.

---

## 3. What you do NOT need to configure

To keep this simple and avoid wasted effort:

- **No Supabase Auth setup.** The app does not use Supabase logins; it uses a
  single shared `APP_PASSWORD`. Leave Authentication settings at defaults.
- **No Row Level Security (RLS) policies.** The app connects with the
  `service_role` key from a trusted server only. Leave RLS off.
- **No Realtime, Storage, or Edge Functions.** Not used in v1.

---

## 4. Apply the database schema

The schema lives in the repo at `supabase/migrations/`
(`0001_initial_schema.sql` then `0002_seed_cities.sql`). Apply them **in order**.

**Option A — Supabase SQL Editor (simplest, no tooling):**

1. In the dashboard, open **SQL Editor** → **New query**.
2. Open `supabase/migrations/0001_initial_schema.sql` from the repo, paste its
   entire contents in, click **Run**. Confirm "Success".
3. Repeat with `supabase/migrations/0002_seed_cities.sql`.
4. Open **Table Editor** → `cities` and confirm **16 rows**.

**Option B — Supabase CLI (if you are also doing the dev setup):** follow Phase 1,
Tasks 1.2–1.4 in `docs/superpowers/plans/2026-05-18-trc-streamlit-research-tool.md`
(`supabase link` then `supabase db push`).

---

## 5. Put the keys where the app reads them

You need the five values from section 0 in the place(s) relevant to how you run it:

**a) Local development / running tests** — create a root `.env`:

```
Copy-Item .env.example .env      # Windows PowerShell
# then edit .env and paste the five real values
```

**b) Running the Streamlit app locally** — create `.streamlit/secrets.toml`
(copy from `.streamlit/secrets.toml.example` once it exists) with the same five
values in TOML form (`KEY = "value"`).

**c) Deploying to Streamlit Community Cloud** — in the deployed app:
**Manage app → Settings → Secrets**, paste the same five `KEY = "value"` lines.

The values are identical everywhere; only the file format differs. `.env` and
`.streamlit/secrets.toml` are git-ignored and must never be committed.

---

## 6. Verification checklist

- [ ] Supabase project `trc-research-tool` exists; DB password saved in password manager.
- [ ] `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` copied.
- [ ] `PERPLEXITY_API_KEY`, `ANTHROPIC_API_KEY` obtained; `APP_PASSWORD` chosen.
- [ ] Both migrations ran; `cities` table shows 16 rows.
- [ ] Five values placed in `.env` (and/or `.streamlit/secrets.toml` / Cloud Secrets).
- [ ] No real key is committed to git (only `.env.example` is tracked).

---

## 7. Security do / don't

- **Do** store the DB password and `service_role` key in the team password manager.
- **Do** rotate the `service_role` key (Project Settings → API) if it is ever exposed.
- **Don't** paste real keys into chat, email, tickets, or screenshots.
- **Don't** use the `service_role` key in any browser-side code.
- **Don't** commit `.env` or `.streamlit/secrets.toml`.
