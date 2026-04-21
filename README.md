# Dropshipping Product Opportunity Finder

An automated agent that identifies profitable dropshipping products by pulling
trending categories from Google Trends, finding matching products on CJ
Dropshipping, calculating estimated margins using CJ's suggested retail price,
and presenting ranked recommendations on a Next.js dashboard.

## Layout

```
/backend    FastAPI app, APScheduler, pipeline steps 1-5, CJ client
/frontend   Next.js + Tailwind + Recharts dashboard
/supabase   Postgres schema
```

## Quick start

### 1. Verify the CJ API first

Before wiring anything else up, run the smoke test to confirm CJ's product
search is returning `sellPrice` (the suggested retail price we rely on):

```bash
cd backend
cp .env.example .env
# fill in CJ_API_EMAIL, CJ_API_KEY, ANTHROPIC_API_KEY
python -m backend.scripts.verify_cj_sellprice
```

If that prints non-zero `sellPrice` values, the pipeline is good to build on.

### 2. Run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload
# trigger a run manually:
curl -X POST http://localhost:8000/run-pipeline
```

Set `MOCK_MODE=true` in `.env` to read/write JSON fixtures in
`backend/mock_data/` instead of calling pytrends / CJ / Claude / Supabase.
Ideal while iterating on the frontend.

### 3. Run the frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

With `NEXT_PUBLIC_USE_MOCK=true` the frontend reads `lib/mockData.js` directly
so you don't need the backend running.

### 4. Supabase schema

Apply `supabase/schema.sql` in the Supabase SQL editor (or via `psql`).

## Pipeline

1. **Trends** – pytrends rising queries → one Claude call → 10 product categories.
2. **Config** – `config.yaml` supplies filter thresholds (min orders 100, rating 4.5, stock 50).
3. **Products** – CJ product search per category; normalize `sellPrice` (est. retail)
   and `supplyPrice` (our cost); apply filters; only keep `sellPrice > supplyPrice`.
4. **Enrich** – compute `supplier_risk_score`, `platform_fee` (15%),
   `net_margin` (minus 2% return reserve), and `margin_pct`.
5. **Recommend** – Claude returns `PURSUE / MONITOR / AVOID` + 1–2 sentence reason
   (batched up to 10 products per call). Rules:
   - PURSUE: margin_pct > 20 AND risk > 70
   - AVOID: margin_pct < 10 OR risk < 40
   - MONITOR: everything else

APScheduler runs the pipeline daily at 06:00 local time. `POST /run-pipeline`
triggers a manual run. All writes are upserts keyed by `(cj_product_id, run_date)`
so repeated runs are idempotent.

## Important notes

- `sellPrice` from CJ is CJ's **suggested retail**, not a verified Amazon price.
  The UI labels it `Est. Retail (CJ)` and the product detail page repeats the
  warning.
- v2 path: swap `sell_price` for real Amazon data via Rainforest API — the
  schema and UI already treat it as "estimated retail" so no migration needed.
