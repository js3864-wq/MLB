-- Schema for the dropshipping product opportunity finder.
-- Apply with: psql $SUPABASE_DB_URL -f supabase/schema.sql
-- or paste into the Supabase SQL editor.

create extension if not exists "pgcrypto";

create table if not exists trend_categories (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    run_date date not null,
    created_at timestamptz not null default now(),
    unique (name, run_date)
);

create table if not exists products (
    id uuid primary key default gen_random_uuid(),
    category_id uuid references trend_categories(id) on delete cascade,
    cj_product_id text not null,
    title text,
    image_url text,
    supply_price numeric,          -- CJ cost
    sell_price numeric,            -- CJ suggested retail = estimated retail
    shipping_cost numeric,
    platform_fee numeric,
    net_margin numeric,
    margin_pct numeric,
    supplier_risk_score numeric,
    sold_count integer,
    stock integer,
    supplier_rating numeric,
    recommendation text check (recommendation in ('PURSUE','MONITOR','AVOID')),
    explanation text,
    run_date date not null,
    created_at timestamptz not null default now(),
    unique (cj_product_id, run_date)
);

create index if not exists idx_products_run_date on products(run_date);
create index if not exists idx_products_recommendation on products(recommendation);
create index if not exists idx_products_margin_pct on products(margin_pct desc);
