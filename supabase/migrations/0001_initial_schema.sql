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