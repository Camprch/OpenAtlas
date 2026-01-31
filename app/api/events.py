from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date
from typing import Optional, List
from sqlmodel import Session
from app.database import get_db
from app.api.models_country import CountryEventsResponse
from app.services.country_events_service import get_country_events_service

# Router for country event listings
router = APIRouter()


@router.get(
    "/countries/{country}/all-events",
    response_model=CountryEventsResponse,
)
def get_country_all_events(
    country: str,
    sources: Optional[List[str]] = Query(None),
    labels: Optional[List[str]] = Query(None),
    event_types: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db),
):
    """
    Return all events for a country across all dates (grouped by region/location).
    """
    try:
        # Delegate filtering and grouping to the service layer
        return get_country_events_service(country, target_date=None, sources=sources, labels=labels, event_types=event_types, session=session)
    except Exception as e:
        # Expose service errors as a 400 to the client
        raise HTTPException(status_code=400, detail=str(e))

@router.get(
    "/countries/{country}/events",
    response_model=CountryEventsResponse,
)
def get_country_events(
    country: str,
    target_date: date = Query(..., alias="date"),
    sources: Optional[List[str]] = Query(None),
    labels: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db),
):
    """
    List events for a country on a specific date (grouped by region/location).
    """
    try:
        # Delegate filtering and grouping to the service layer
        return get_country_events_service(country, target_date=target_date, sources=sources, labels=labels, session=session)
    except Exception as e:
        # Expose service errors as a 400 to the client
        raise HTTPException(status_code=400, detail=str(e))
