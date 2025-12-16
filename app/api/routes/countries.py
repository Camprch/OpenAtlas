# Initialisation du router et modèles nécessaires

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlmodel import Session, select
from app.database import get_db
from app.models.message import Message
from app.api.routes.filters import COUNTRY_ALIASES, COUNTRY_COORDS, normalize_country_names

router = APIRouter()

class CountryActivity(BaseModel):
    country: str
    events_count: int

class CountryStatus(BaseModel):
    country: str
    events_count: int
    last_date: date

class ActiveCountriesResponse(BaseModel):
    countries: List[CountryStatus]
    ignored_countries: List[str]

class EventMessage(BaseModel):
    id: int
    telegram_message_id: Optional[int]
    channel: Optional[str]
    title: Optional[str]
    source: Optional[str]
    orientation: Optional[str]
    event_timestamp: Optional[datetime]
    created_at: datetime
    url: Optional[str]
    translated_text: Optional[str] = None
    preview: str

class ZoneEvents(BaseModel):
    region: Optional[str]
    location: Optional[str]
    messages_count: int
    messages: List[EventMessage]

class CountryEventsResponse(BaseModel):
    date: date
    country: str
    zones: List[ZoneEvents]

# --- ROUTES PAYS/EVENTS ---


@router.get("/countries/active", response_model=ActiveCountriesResponse)
def get_active_countries(
    days: int = Query(30, ge=1),
    date_filter: Optional[List[date]] = Query(None, alias="date"),
    session: Session = Depends(get_db),
):
    """
    Renvoie les pays qui ont des messages à une ou plusieurs dates précises (si 'date' fourni une ou plusieurs fois),
    sinon dans les X derniers jours, avec le nombre d'événements et la dernière date d'activité.
    Fournit aussi la liste des pays ignorés (non normalisés).
    """
    if date_filter:
        # Plusieurs dates : on filtre sur toutes les dates sélectionnées
        all_rows = []
        for d in date_filter:
            start_dt = datetime.combine(d, datetime.min.time())
            end_dt = datetime.combine(d, datetime.max.time())
            stmt = select(Message.country, Message.created_at).where(
                Message.created_at >= start_dt,
                Message.created_at <= end_dt,
                Message.country.is_not(None),
            )
            all_rows.extend(session.exec(stmt).all())
        rows = all_rows
    else:
        now = datetime.utcnow()
        start_dt = now - timedelta(days=days)
        stmt = select(Message.country, Message.created_at).where(
            Message.created_at >= start_dt,
            Message.country.is_not(None),
        )
        rows = session.exec(stmt).all()

    stats: Dict[str, Dict[str, object]] = {}
    ignored_countries = set()
    for country, created_at in rows:
        if not country:
            continue
        country = country.strip()
        if not country:
            continue
        # Multi-pays : normalisation multiple
        norm_countries = normalize_country_names(country, COUNTRY_ALIASES)
        if not norm_countries:
            ignored_countries.add(country)
            continue  # ignorer les pays non normalisés
        d = created_at.date()
        for norm_country in norm_countries:
            if norm_country not in stats:
                stats[norm_country] = {"count": 0, "last_date": d}
            stats[norm_country]["count"] += 1
            if d > stats[norm_country]["last_date"]:
                stats[norm_country]["last_date"] = d

    # Ne garder que les pays qui ont une coordonnée (donc normalisés)
    result = [
        CountryStatus(
            country=c,
            events_count=v["count"],
            last_date=v["last_date"],
        )
        for c, v in stats.items() if c in COUNTRY_COORDS
    ]
    # tri optionnel : pays les plus actifs en premier
    result.sort(key=lambda c: c.events_count, reverse=True)
    return ActiveCountriesResponse(countries=result, ignored_countries=sorted(ignored_countries))


@router.get(
    "/countries/{country}/all-events",
    response_model=CountryEventsResponse,
)
def get_country_all_events(
    country: str,
    session: Session = Depends(get_db),
):
    """
    Retourne tous les événements pour un pays, toutes dates confondues (groupés par région/location).
    """
    norm_country = country
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")

    stmt = select(Message).where(
        Message.country.is_not(None)
    )
    msgs = session.exec(stmt).all()
    # Filtrer pour ne garder que ceux qui contiennent ce pays
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
    # Déterminer une date à retourner (par défaut la plus récente, sinon aujourd'hui)
    if msgs:
        # On prend la date du message le plus récent
        latest_date = max(m.created_at for m in msgs).date()
    else:
        latest_date = datetime.utcnow().date()
    return CountryEventsResponse(
        date=latest_date,
        country=country,
        zones=zones_payload,
    )

def get_active_countries(
    days: int = Query(30, ge=1),
    date_filter: Optional[List[date]] = Query(None, alias="date"),
    session: Session = Depends(get_db),
):
    """
    Renvoie les pays qui ont des messages à une ou plusieurs dates précises (si 'date' fourni une ou plusieurs fois),
    sinon dans les X derniers jours, avec le nombre d'événements et la dernière date d'activité.
    Fournit aussi la liste des pays ignorés (non normalisés).
    """
    if date_filter:
        # Plusieurs dates : on filtre sur toutes les dates sélectionnées
        all_rows = []
        for d in date_filter:
            start_dt = datetime.combine(d, datetime.min.time())
            end_dt = datetime.combine(d, datetime.max.time())
            stmt = select(Message.country, Message.created_at).where(
                Message.created_at >= start_dt,
                Message.created_at <= end_dt,
                Message.country.is_not(None),
            )
            all_rows.extend(session.exec(stmt).all())
        rows = all_rows
    else:
        now = datetime.utcnow()
        start_dt = now - timedelta(days=days)
        stmt = select(Message.country, Message.created_at).where(
            Message.created_at >= start_dt,
            Message.country.is_not(None),
        )
        rows = session.exec(stmt).all()

    stats: Dict[str, Dict[str, object]] = {}
    ignored_countries = set()
    for country, created_at in rows:
        if not country:
            continue
        country = country.strip()
        if not country:
            continue
        # Multi-pays : normalisation multiple
        norm_countries = normalize_country_names(country, COUNTRY_ALIASES)
        if not norm_countries:
            ignored_countries.add(country)
            continue  # ignorer les pays non normalisés
        d = created_at.date()
        for norm_country in norm_countries:
            if norm_country not in stats:
                stats[norm_country] = {"count": 0, "last_date": d}
            stats[norm_country]["count"] += 1
            if d > stats[norm_country]["last_date"]:
                stats[norm_country]["last_date"] = d

    # Ne garder que les pays qui ont une coordonnée (donc normalisés)
    result = [
        CountryStatus(
            country=c,
            events_count=v["count"],
            last_date=v["last_date"],
        )
        for c, v in stats.items() if c in COUNTRY_COORDS
    ]
    # tri optionnel : pays les plus actifs en premier
    result.sort(key=lambda c: c.events_count, reverse=True)
    return ActiveCountriesResponse(countries=result, ignored_countries=sorted(ignored_countries))


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
    # 1) On cherche la dernière date pour ce pays
    # On normalise l'identifiant reçu
    norm_country = country
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")

    # On cherche tous les messages qui contiennent ce pays dans la liste normalisée
    # (multi-pays)
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
    # Filtrer pour ne garder que ceux qui contiennent ce pays
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


@router.get("/countries", response_model=List[CountryActivity])
def get_countries_activity(
    target_date: date = Query(..., alias="date"),
    session: Session = Depends(get_db),
):
    """
    Compte les messages par pays pour une date donnée (sur created_at).
    """
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    stmt = select(Message).where(
        Message.created_at >= start_dt,
        Message.created_at <= end_dt,
    )
    msgs = session.exec(stmt).all()

    counts: Dict[str, int] = {}
    for m in msgs:
        if not m.country:
            continue
        country = m.country.strip()
        if not country:
            continue
        counts[country] = counts.get(country, 0) + 1

    result = [
        CountryActivity(country=c, events_count=n)
        for c, n in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return result


@router.get(
    "/countries/{country}/events",
    response_model=CountryEventsResponse,
)
def get_country_events(
    country: str,
    target_date: date = Query(..., alias="date"),
    session: Session = Depends(get_db),
):
    """
    Liste des événements pour un pays + date (groupés par région / location).
    """
    # On utilise la même logique de normalisation/multi-pays que latest-events
    norm_country = country
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    stmt = select(Message).where(
        Message.created_at >= start_dt,
        Message.created_at <= end_dt,
    )
    msgs = session.exec(stmt).all()
    # Filtrer pour ne garder que ceux qui contiennent ce pays
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
