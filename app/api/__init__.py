from fastapi import APIRouter

# Router principal
router = APIRouter()

# Import et inclusion des sous-routeurs
from app.api.countries import router as countries_router
router.include_router(countries_router)
from app.api.env import router as env_router
router.include_router(env_router)
from app.api.pipeline import router as pipeline_router
router.include_router(pipeline_router)
from app.api.filters import router as filters_router
router.include_router(filters_router)

from app.api.events import router as events_router
router.include_router(events_router)

from app.api.session_wizard import router as session_wizard_router
router.include_router(session_wizard_router)

# Ajout du routeur de recherche
from app.api.search import router as search_router
router.include_router(search_router)
