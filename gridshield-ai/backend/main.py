"""
GridShield AI – FastAPI backend entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from routes import data_router, analysis_router, cases_router, reports_router, agents_router
from services.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s – %(message)s")
logger = logging.getLogger("gridshield")

app = FastAPI(
    title="GridShield AI",
    description="Agentic AI Electricity Fraud Detection & Investigation Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_db()
    logger.info("GridShield AI backend started")

app.include_router(data_router, prefix="/api/data", tags=["Data Ingestion"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(cases_router, prefix="/api/cases", tags=["Case Management"])
app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])
app.include_router(agents_router, prefix="/api/agents", tags=["AI Agents"])

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "GridShield AI"}
