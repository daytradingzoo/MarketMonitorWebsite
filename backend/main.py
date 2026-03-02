"""FastAPI application entry point."""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.routers import overview, movers, sectors, indexes, stocks, repos, system

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Market Monitor API",
    description="Pre-computed stock market breadth and momentum data.",
    version="1.0.0",
)

# CORS — allow the Next.js frontend origin
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(overview.router, prefix="/api")
app.include_router(movers.router,   prefix="/api")
app.include_router(sectors.router,  prefix="/api")
app.include_router(indexes.router,  prefix="/api")
app.include_router(stocks.router,   prefix="/api")
app.include_router(repos.router,    prefix="/api")
app.include_router(system.router,   prefix="/api")


@app.get("/")
def health() -> dict:
    return {"status": "ok"}
