"""Routes package – import all routers here for main.py."""
from routes.data import router as data_router
from routes.analysis import router as analysis_router
from routes.cases import router as cases_router
from routes.reports import router as reports_router
from routes.agents import router as agents_router

__all__ = ["data_router", "analysis_router", "cases_router", "reports_router", "agents_router"]
