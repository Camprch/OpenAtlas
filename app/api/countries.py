# Initialisation du router et modèles nécessaires

from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlmodel import Session, select
from app.database import get_db
from app.models.message import Message
from app.api.filters import COUNTRY_ALIASES, COUNTRY_COORDS, normalize_country_names
from app.api.models_country import CountryActivity, CountryStatus, ActiveCountriesResponse, CountryEventsResponse
from app.services.country_events_service import (
    get_active_countries_service,
    get_country_latest_events_service,
    get_countries_activity_service,
    get_country_events_service,
)

router = APIRouter()

# --- ROUTES PAYS/EVENTS ---

@router.get("/countries/active", response_model=ActiveCountriesResponse)
def get_active_countries(
    days: int = Query(30, ge=1),
    date_filter: Optional[List[date]] = Query(None, alias="date"),
    sources: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db),
):
    return get_active_countries_service(days=days, date_filter=date_filter, sources=sources, session=session)


@router.get(
    "/countries/{country}/latest-events",
    response_model=CountryEventsResponse,
)
def get_country_latest_events(
    country: str,
    sources: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db),
):
    try:
        return get_country_latest_events_service(country=country, sources=sources, session=session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



@router.get("/countries", response_model=List[CountryActivity])
def get_countries_activity(
    target_date: date = Query(..., alias="date"),
    session: Session = Depends(get_db),
):
    return get_countries_activity_service(target_date=target_date, session=session)



@router.get(
    "/countries/{country}/events",
    response_model=CountryEventsResponse,
)
def get_country_events(
    country: str,
    target_date: date = Query(..., alias="date"),
    sources: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db),
):
    try:
        return get_country_events_service(country=country, target_date=target_date, sources=sources, session=session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
