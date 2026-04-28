# Dropshipping Product Opportunity Finder — Demo

An offline demo of a pipeline that surfaces trending product categories and
ranks dropshipping product candidates by margin and supplier reliability.
No external APIs, no database, no LLM — everything is driven by a single
`backend/demo_input.yaml` file you edit by hand.

## Layout

```
backend/    FastAPI app (single file) + demo_input.yaml
frontend/   Next.js + Tailwind + Recharts dashboard
```

## How to run the demo

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --app-dir ..
```

The pipeline runs once on startup, so the dashboard will already have data
when you open it. Server runs on `http://localhost:8000`.

### 2. Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

### 3. Editing the data

Open `backend/demo_input.yaml`, change the `trends` or `products` lists,
then either restart the backend or hit:

```bash
curl -X POST http://localhost:8000/run-pipeline
```

The dashboard refreshes on its next fetch.

## What the pipeline does

The five steps (visible in the backend logs) are:

1. **Trends** — read trending categories (replaces Google Trends + LLM).
2. **Config** — load filter thresholds and scoring rates.
3. **Products** — load CJ-style product candidates (replaces CJ search).
4. **Enrich** — compute `platform_fee` (15%), `net_margin` (minus 2% return
   reserve), `margin_pct`, and `supplier_risk_score`.
5. **Recommend** — assign `PURSUE / MONITOR / AVOID`:
   - PURSUE — `margin_pct > 20` AND `supplier_risk_score > 70`
   - AVOID — `margin_pct < 10` OR `supplier_risk_score < 40`
   - MONITOR — anything in between

Each product gets a generated explanation that reads like an LLM response.

You can override the verdict on a specific product by adding
`recommendation:` and `explanation:` to its entry in `demo_input.yaml`.
