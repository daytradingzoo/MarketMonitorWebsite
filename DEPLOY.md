# Deployment Guide — Market Monitor Website

## Prerequisites

- GitHub account with the repo: `https://github.com/daytradingzoo/MarketMonitorWebsite`
- Render account: https://render.com
- Polygon.io API key (Stocks Advanced + Indices Basic plan)

---

## One-Time Setup

### 1. Connect GitHub to Render

1. Go to https://dashboard.render.com
2. Click **New → Blueprint** (or use the render.yaml auto-deploy)
3. Connect your GitHub account and select the `MarketMonitorWebsite` repo
4. Render will read `render.yaml` and create all services automatically

### 2. Set Secret Environment Variables

For each service, go to **Settings → Environment** in the Render dashboard:

**market-monitor-api** and **market-monitor-pipeline:**
```
POLYGON_API_KEY=your_polygon_api_key_here
ALLOWED_ORIGINS=https://market-monitor-frontend.onrender.com
```

**market-monitor-frontend:**
```
NEXT_PUBLIC_API_URL=https://market-monitor-api.onrender.com
```

> Never commit these to git. They live only in Render's environment variable store.

### 3. Apply the Database Schema

After Render creates the PostgreSQL database, run migrations once:

```bash
# From your local terminal with DATABASE_URL set in .env
cd c:\Trading\Python\MarketMonitorWebsite
python -m backend.migrate
```

Or via Render Shell on the API service:
```bash
python -m backend.migrate
```

### 4. Run the Historical Backfill

This downloads all historical data from Polygon S3. Run once manually — it takes several hours.

```bash
# From the jobs/ folder with DATABASE_URL and POLYGON_API_KEY set
python -m jobs.backfill --start-year 2004 --end-year 2024
```

Run this from Render Shell on the cron job service, or locally.

---

## Daily Operations (Automatic)

The Render cron job runs automatically at 4:30 PM ET Mon–Fri:

```
ingest.py → calculate.py → aggregate.py → job_runs log
```

Check job status in the API:
```
GET https://market-monitor-api.onrender.com/api/status
```

---

## Development Workflow

```bash
# Work on dev branch — no auto-deploy
git checkout dev
# ... make changes ...
git add .
git commit -m "Add new metric"
git push origin dev

# When ready to deploy
git checkout main
git merge dev
git push origin main   # triggers Render auto-deploy (~2 min)
```

---

## Service URLs (after deploy)

| Service | URL |
|---|---|
| Frontend | https://market-monitor-frontend.onrender.com |
| API | https://market-monitor-api.onrender.com |
| API Docs | https://market-monitor-api.onrender.com/docs |

---

## Estimated Costs

| Service | Plan | Cost/mo |
|---|---|---|
| FastAPI web service | Starter | $7 |
| Next.js web service | Starter | $7 |
| Daily cron job | Starter | $1 |
| Managed PostgreSQL | Starter | $7 |
| **Total** | | **~$22/mo** |

---

## Adding a New Metric

1. Add the Python calculation in `jobs/calculate.py`
2. Add the aggregation in `jobs/aggregate.py`
3. Add the column in `backend/migrations/00N_add_metric.sql`
4. Register it in `METRIC_CATALOG` in `frontend/app/lib/metrics.ts`
5. Add a `BlockConfig` entry to the relevant page in `frontend/app/page.tsx`
6. Commit and merge to `main`

Zero new API code needed — the generic `/api/repos/{id}/data` endpoint serves it automatically.
