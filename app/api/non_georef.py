from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date
from typing import Optional, List
from sqlmodel import Session
from app.database import get_db
from app.api.models_country import CountryEventsResponse
from app.services.country_events_service import get_non_georef_events_service

# Router for non-georeferenced event listings (country == None)
router = APIRouter()


@router.get(
    "/non-georef/all-events",
    response_model=CountryEventsResponse,
)
def get_non_georef_all_events(
    sources: Optional[List[str]] = Query(None),
    labels: Optional[List[str]] = Query(None),
    event_types: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db),
):
    """
    Return all events without a country across all dates (grouped by region/location).
    """
    try:
        return get_non_georef_events_service(
            target_date=None,
            sources=sources,
            labels=labels,
            event_types=event_types,
            session=session,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/non-georef/events",
    response_model=CountryEventsResponse,
)
def get_non_georef_events(
    target_date: date = Query(..., alias="date"),
    sources: Optional[List[str]] = Query(None),
    labels: Optional[List[str]] = Query(None),
    event_types: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db),
):
    """
    List events without a country on a specific date (grouped by region/location).
    """
    try:
        return get_non_georef_events_service(
            target_date=target_date,
            sources=sources,
            labels=labels,
            event_types=event_types,
            session=session,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
