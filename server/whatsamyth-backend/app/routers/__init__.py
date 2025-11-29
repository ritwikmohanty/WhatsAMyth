"""
API Routers Package
Contains all FastAPI router definitions for the WhatsAMyth API.
"""

from app.routers.messages import router as messages_router
from app.routers.claims import router as claims_router
from app.routers.stats import router as stats_router

__all__ = ["messages_router", "claims_router", "stats_router"]
