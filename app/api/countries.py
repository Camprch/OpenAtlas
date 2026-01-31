from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date
from typing import List, Optional
from sqlmodel import Session
from app.database import get_db
from app.api.models_country import CountryActivity, CountryStatus, ActiveCountriesResponse, CountryEventsResponse
from app.services.country_events_service import (
    get_active_countries_service,
    get_country_latest_events_service,
    get_countries_activity_service,
    get_country_events_service,
)

# Router for country/event endpoints
router = APIRouter()

# Country activity and events endpoints

@router.get("/countries/active", response_model=ActiveCountriesResponse)
def get_active_countries(
    days: Optional[int] = Query(None, ge=1),
    date_filter: Optional[List[date]] = Query(None, alias="date"),
    sources: Optional[List[str]] = Query(None),
    labels: Optional[List[str]] = Query(None),
    event_types: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db),
):
    # Forward filters to the service layer
    return get_active_countries_service(days=days, date_filter=date_filter, sources=sources, labels=labels, event_types=event_types, session=session)


@router.get(
    "/countries/{country}/latest-events",
    response_model=CountryEventsResponse,
)
def get_country_latest_events(
    country: str,
    sources: Optional[List[str]] = Query(None),
    labels: Optional[List[str]] = Query(None),
    event_types: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db),
):
    try:
        # Service raises ValueError when the country is invalid or missing
        return get_country_latest_events_service(country=country, sources=sources, labels=labels, event_types=event_types, session=session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



@router.get("/countries", response_model=List[CountryActivity])
def get_countries_activity(
    target_date: date = Query(..., alias="date"),
    session: Session = Depends(get_db),
):
    # Fetch per-country activity for a given date
    return get_countries_activity_service(target_date=target_date, session=session)



@router.get(
    "/countries/{country}/events",
    response_model=CountryEventsResponse,
)
def get_country_events(
    country: str,
    target_date: date = Query(..., alias="date"),
    sources: Optional[List[str]] = Query(None),
    labels: Optional[List[str]] = Query(None),
    event_types: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db),
):
    try:
        # Service raises ValueError when the country is invalid or missing
        return get_country_events_service(country=country, target_date=target_date, sources=sources, labels=labels, event_types=event_types, session=session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
