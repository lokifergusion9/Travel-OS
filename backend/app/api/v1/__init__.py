"""Version 1 API router aggregation."""
from fastapi import APIRouter

from app.api.v1 import auth
from app.modules.analytics.router import router as analytics_router
from app.modules.approvals.router import router as approvals_router
from app.modules.creative.router import router as creative_router
from app.modules.crm.public import router as public_router
from app.modules.crm.router import router as crm_router
from app.modules.publishing.router import router as publishing_router
from app.modules.sourcing.router import router as sourcing_router
from app.modules.trips.router import router as trips_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(trips_router)
api_router.include_router(creative_router)
api_router.include_router(crm_router)
api_router.include_router(public_router)
api_router.include_router(sourcing_router)
api_router.include_router(publishing_router)
api_router.include_router(analytics_router)
api_router.include_router(approvals_router)
