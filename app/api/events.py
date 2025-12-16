from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date, datetime
from typing import Optional, Dict, Tuple, List
from sqlmodel import Session, select
from app.database import get_db
from app.models.message import Message
from app.api.filters import COUNTRY_ALIASES, COUNTRY_COORDS, normalize_country_names
from app.api.models_country import EventMessage, ZoneEvents, CountryEventsResponse
from app.services.country_events_service import get_country_events_service

router = APIRouter()


@router.get(
    "/countries/{country}/all-events",
    response_model=CountryEventsResponse,
)
def get_country_all_events(
    country: str,
    sources: Optional[List[str]] = Query(None),
    session: Session = Depends(get_db),
):
    """
    Retourne tous les événements pour un pays, toutes dates confondues (groupés par région/location).
    """
    try:
        return get_country_events_service(country, target_date=None, sources=sources, session=session)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get(
    "/countries/{country}/latest-events",
    response_model=CountryEventsResponse,
)
def get_country_latest_events(
    country: str,
    session: Session = Depends(get_db),
):
    """
    Liste les événements pour un pays à la date la plus récente (sur created_at).
    """
    norm_country = country
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")

    stmt_last = (
        select(Message.created_at, Message.country)
        .order_by(Message.created_at.desc())
    )
    rows = session.exec(stmt_last).all()
    last_date = None
    for created_at, raw_country in rows:
        norm_countries = normalize_country_names(raw_country, COUNTRY_ALIASES)
        if norm_country in norm_countries:
            last_date = created_at
            break
    if not last_date:
        raise HTTPException(status_code=404, detail="Aucun événement pour ce pays")

    target_date = last_date.date()

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    stmt = select(Message).where(
        Message.created_at >= start_dt,
        Message.created_at <= end_dt,
    )
    msgs = session.exec(stmt).all()
    msgs = [m for m in msgs if norm_country in normalize_country_names(m.country, COUNTRY_ALIASES)]

    buckets: Dict[Tuple[Optional[str], Optional[str]], List[Message]] = {}
    for m in msgs:
        key = (m.region, m.location)
        buckets.setdefault(key, []).append(m)

    zones_payload: List[ZoneEvents] = []
    for (region, location), items in buckets.items():
        event_messages: List[EventMessage] = []
        for m in items:
            url = None
            if m.channel and m.telegram_message_id:
                url = f"https://t.me/{m.channel}/{m.telegram_message_id}"
            full_text = (m.translated_text or m.raw_text or "").strip()
            preview = full_text[:277] + "..." if len(full_text) > 280 else full_text
            event_messages.append(
                EventMessage(
                    id=m.id,
                    telegram_message_id=m.telegram_message_id,
                    channel=m.channel,
                    title=m.title,
                    source=m.source,
                    orientation=m.orientation,
                    event_timestamp=m.event_timestamp,
                    created_at=m.created_at,
                    url=url,
                    translated_text=full_text,
                    preview=preview,
                )
            )
        zones_payload.append(
            ZoneEvents(
                region=region,
                location=location,
                messages_count=len(items),
                messages=event_messages,
            )
        )
    zones_payload.sort(key=lambda z: z.messages_count, reverse=True)
    return CountryEventsResponse(
        date=target_date,
        country=country,
        zones=zones_payload,
    )


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
    """
    Liste des événements pour un pays + date (groupés par région / location).
    """
    try:
        return get_country_events_service(country, target_date=target_date, sources=sources, session=session)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
