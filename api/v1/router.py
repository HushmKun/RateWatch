from fastapi import APIRouter

from api.v1.routes.history import router as history_router
from api.v1.routes.rates import router as rates_router
from api.v1.routes.sources import router as sources_router


router = APIRouter()
router.include_router(rates_router)
router.include_router(history_router)
router.include_router(sources_router)
