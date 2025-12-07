from fastapi import APIRouter

from app.api.v1 import routers as v1_routers
from app.api.v2 import routers as v2_routers

api_router_v1 = APIRouter()
api_router_v2 = APIRouter()

api_router_v1.include_router(v1_routers.api_router)
api_router_v2.include_router(v2_routers.api_router)
