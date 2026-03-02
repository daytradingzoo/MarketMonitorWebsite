# Market Monitor Website

A public-facing stock market breadth dashboard powered by Polygon.io data, FastAPI, PostgreSQL, and Next.js.

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Database | PostgreSQL (Render Managed) |
| Frontend | Next.js + TypeScript + Tremor + Tailwind CSS |
| Data source | Polygon.io (Stocks Advanced + Indices Basic) |
| Hosting | Render (~$22/mo) |
| CI/CD | GitHub → Render auto-deploy |

## Project Structure

```
backend/     FastAPI API server
jobs/        Daily data pipeline (ingest, calculate, aggregate, backfill)
frontend/    Next.js dashboard
.cursor/rules/  AI coding rules for consistent development
```

## Environment Variables

Set these in Render dashboard (never commit to git):

```
POLYGON_API_KEY=...
DATABASE_URL=postgresql://...
NEXT_PUBLIC_API_URL=https://your-api.onrender.com
```

## Development Workflow

1. Work on `dev` branch in Cursor
2. Push to `dev` — no auto-deploy
3. Merge `dev` → `main` — Render auto-deploys all services

## Initial Data Load

Run once manually after DB is provisioned:

```bash
cd jobs
python backfill.py
```

This downloads Polygon flat files and builds the full historical `market_summary`.

## Daily Pipeline

Runs automatically via Render Cron Job at 4:30 PM ET:

```
ingest.py → calculate.py → aggregate.py → job_runs log
```

## Data Model

- `daily_bars` / `daily_metrics`: rolling 252-day window (purged after use)
- `market_summary`: full history, one row per trading day per universe
- `repos` / `repo_columns`: metadata registry for the block system
