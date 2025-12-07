from fastapi import APIRouter

from app.api.v1.routers import api_router as v1_router
from app.api.v2.routers import api_router as v2_router

VERSIONED_ROUTERS = {
    "v1": v1_router,
    "v2": v2_router,
}

api_routers = {version: APIRouter() for version in VERSIONED_ROUTERS}

for version, router in api_routers.items():
    router.include_router(VERSIONED_ROUTERS[version])
