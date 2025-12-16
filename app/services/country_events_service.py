from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlmodel import Session, select
from app.models.message import Message
from app.api.filters import COUNTRY_ALIASES, COUNTRY_COORDS, normalize_country_names
from app.api.models_country import CountryStatus, ActiveCountriesResponse, CountryActivity, CountryEventsResponse, EventMessage, ZoneEvents


def get_active_countries_service(
    days: int = 30,
    date_filter: Optional[List[date]] = None,
    session: Session = None,
) -> ActiveCountriesResponse:
    if date_filter:
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
        norm_countries = normalize_country_names(country, COUNTRY_ALIASES)
        if not norm_countries:
            ignored_countries.add(country)
            continue
        d = created_at.date()
        for norm_country in norm_countries:
            if norm_country not in stats:
                stats[norm_country] = {"count": 0, "last_date": d}
            stats[norm_country]["count"] += 1
            if d > stats[norm_country]["last_date"]:
                stats[norm_country]["last_date"] = d

    result = [
        CountryStatus(
            country=c,
            events_count=v["count"],
            last_date=v["last_date"],
        )
        for c, v in stats.items() if c in COUNTRY_COORDS
    ]
    result.sort(key=lambda c: c.events_count, reverse=True)
    return ActiveCountriesResponse(countries=result, ignored_countries=sorted(ignored_countries))


def get_country_latest_events_service(
    country: str,
    session: Session
) -> CountryEventsResponse:
    norm_country = country
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise ValueError("Pays non normalisé ou non géoréférencé")

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
        raise ValueError("Aucun événement pour ce pays")

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


def get_countries_activity_service(
    target_date: date,
    session: Session
) -> List[CountryActivity]:
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


def get_country_events_service(
    country: str,
    target_date: date,
    session: Session
) -> CountryEventsResponse:
    norm_country = country
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise ValueError("Pays non normalisé ou non géoréférencé")
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
