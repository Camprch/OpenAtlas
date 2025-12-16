
from fastapi import APIRouter

# Router principal
router = APIRouter()

# Import et inclusion des sous-routeurs
from app.api.routes.countries import router as countries_router
router.include_router(countries_router)
from app.api.routes.env import router as env_router
router.include_router(env_router)
from app.api.routes.pipeline import router as pipeline_router
router.include_router(pipeline_router)
from app.api.routes.filters import router as filters_router
router.include_router(filters_router)
from app.api.session_wizard import router as session_wizard_router
router.include_router(session_wizard_router)
