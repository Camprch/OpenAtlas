from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlmodel import Session, select
from app.models.message import Message
from app.api.filters import COUNTRY_ALIASES, COUNTRY_COORDS, normalize_country_names
from app.api.models_country import CountryStatus, ActiveCountriesResponse, CountryActivity, CountryEventsResponse, EventMessage, ZoneEvents


def get_active_countries_service(
    days: Optional[int] = None,
    date_filter: Optional[List[date]] = None,
    sources: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
    event_types: Optional[List[str]] = None,
    session: Session = None,
) -> ActiveCountriesResponse:
    from sqlmodel import func
    ignored_countries = set()
    # Helper to apply optional filters consistently

    def add_ignored_country(raw_country: Optional[str]) -> None:
        if not raw_country:
            return
        country = str(raw_country).strip()
        if len(country) == 1:
            return
        norm_list = normalize_country_names(country, COUNTRY_ALIASES)
        if norm_list:
            ignored_countries.add(f"{country} → {norm_list[0]}")
        else:
            # Country not in aliases/coords: mark as non-georeferenced
            ignored_countries.add(country)

    def add_sources_labels_filter(stmt):
        if sources:
            stmt = stmt.where(Message.source.in_(sources))
        if labels:
            stmt = stmt.where(Message.label.in_(labels))
        if event_types:
            stmt = stmt.where(Message.event_type.in_(event_types))
        return stmt

    if date_filter:
        # Aggregate counts and last dates per country for each requested day
        all_stats = {}
        for d in date_filter:
            start_dt = datetime.combine(d, datetime.min.time())
            end_dt = datetime.combine(d, datetime.max.time())
            stmt = (
                select(
                    Message.country_norm,
                    func.count().label("count"),
                    func.max(Message.event_timestamp).label("last_date")
                )
                .where(
                    Message.event_timestamp >= start_dt,
                    Message.event_timestamp <= end_dt,
                    Message.country_norm.is_not(None)
                )
            )
            stmt = add_sources_labels_filter(stmt).group_by(Message.country_norm)
            for country_norm, count, last_date in session.exec(stmt):
                if country_norm in COUNTRY_COORDS:
                    if country_norm not in all_stats:
                        all_stats[country_norm] = {"count": 0, "last_date": last_date}
                    all_stats[country_norm]["count"] += count
                    if last_date and (all_stats[country_norm]["last_date"] is None or last_date > all_stats[country_norm]["last_date"]):
                        all_stats[country_norm]["last_date"] = last_date
        # Track non-normalized countries for those dates (same day window)
        date_ranges = []
        for d in date_filter:
            start_dt = datetime.combine(d, datetime.min.time())
            end_dt = datetime.combine(d, datetime.max.time())
            date_ranges.append((start_dt, end_dt))
        stmt_ignored = select(Message.country).where(
            Message.country_norm.is_(None),
            Message.country.is_not(None)
        )
        if date_ranges:
            date_clauses = [
                (Message.event_timestamp >= start_dt) & (Message.event_timestamp <= end_dt)
                for start_dt, end_dt in date_ranges
            ]
            stmt_ignored = stmt_ignored.where(*date_clauses)
        stmt_ignored = add_sources_labels_filter(stmt_ignored)
        for row in session.exec(stmt_ignored):
            add_ignored_country(row[0])
        stats = all_stats
    else:
        if days is None:
            # No date filter: aggregate across all available events
            stmt = (
                select(
                    Message.country_norm,
                    func.count().label("count"),
                    func.max(Message.event_timestamp).label("last_date")
                )
                .where(
                    Message.event_timestamp.is_not(None),
                    Message.country_norm.is_not(None)
                )
            )
            stmt = add_sources_labels_filter(stmt).group_by(Message.country_norm)
            stats = {}
            for country_norm, count, last_date in session.exec(stmt):
                if country_norm in COUNTRY_COORDS:
                    stats[country_norm] = {"count": count, "last_date": last_date.date() if last_date else None}
            stmt_ignored = (
                select(Message.country)
                .where(
                    Message.event_timestamp.is_not(None),
                    Message.country_norm.is_(None),
                    Message.country.is_not(None)
                )
            )
            stmt_ignored = add_sources_labels_filter(stmt_ignored)
            for row in session.exec(stmt_ignored):
                add_ignored_country(row[0])
        else:
            # Aggregate counts and last dates within a rolling window
            now = datetime.utcnow()
            start_dt = now - timedelta(days=days)
            stmt = (
                select(
                    Message.country_norm,
                    func.count().label("count"),
                    func.max(Message.event_timestamp).label("last_date")
                )
                .where(
                    Message.event_timestamp >= start_dt,
                    Message.country_norm.is_not(None)
                )
            )
            stmt = add_sources_labels_filter(stmt).group_by(Message.country_norm)
            stats = {}
            for country_norm, count, last_date in session.exec(stmt):
                if country_norm in COUNTRY_COORDS:
                    stats[country_norm] = {"count": count, "last_date": last_date.date() if last_date else None}
            # Track non-normalized countries in the same window
            stmt_ignored = (
                select(Message.country)
                .where(
                    Message.event_timestamp >= start_dt,
                    Message.country_norm.is_(None),
                    Message.country.is_not(None)
                )
            )
            stmt_ignored = add_sources_labels_filter(stmt_ignored)
            for row in session.exec(stmt_ignored):
                add_ignored_country(row[0])

    # Format and sort the response payload
    result = [
        CountryStatus(
            country=c,
            events_count=v["count"],
            last_date=v["last_date"].date() if isinstance(v["last_date"], datetime) else v["last_date"],
        )
        for c, v in stats.items() if c in COUNTRY_COORDS
    ]
    result.sort(key=lambda c: c.events_count, reverse=True)
    return ActiveCountriesResponse(countries=result, ignored_countries=sorted(ignored_countries))


def get_country_latest_events_service(
    country: str,
    sources: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
    event_types: Optional[List[str]] = None,
    session: Session = None
) -> CountryEventsResponse:
    norm_country = country
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise ValueError("Pays non normalisé ou non géoréférencé")
    # Find the most recent event date for the normalized country
    from sqlmodel import func
    stmt_last = (
        select(func.max(Message.event_timestamp))
        .where(Message.country_norm == norm_country)
    )
    if sources:
        stmt_last = stmt_last.where(Message.source.in_(sources))
    if labels:
        stmt_last = stmt_last.where(Message.label.in_(labels))
    if event_types:
        stmt_last = stmt_last.where(Message.event_type.in_(event_types))
    last_date = session.exec(stmt_last).one()
    if not last_date:
        raise ValueError("Aucun événement pour ce pays")
    # Build a full-day range for the latest date
    target_date = last_date.date()
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    # Fetch events for that day with optional filters
    stmt = select(Message).where(
        Message.event_timestamp >= start_dt,
        Message.event_timestamp <= end_dt,
        Message.country_norm == norm_country
    )
    if sources:
        stmt = stmt.where(Message.source.in_(sources))
    if labels:
        stmt = stmt.where(Message.label.in_(labels))
    if event_types:
        stmt = stmt.where(Message.event_type.in_(event_types))
    msgs = session.exec(stmt).all()
    # Bucket events by region/location for the response
    buckets: Dict[Tuple[Optional[str], Optional[str]], List[Message]] = {}
    for m in msgs:
        key = (m.region, m.location)
        buckets.setdefault(key, []).append(m)
    # Build the ZoneEvents payload with previews and URLs
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
    # Count events by raw country name for a specific date
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    stmt = select(Message).where(
        Message.event_timestamp >= start_dt,
        Message.event_timestamp <= end_dt,
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


def get_non_georef_events_service(
    target_date: Optional[date],
    sources: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
    event_types: Optional[List[str]] = None,
    session: Session = None,
) -> CountryEventsResponse:
    # Return events with no country assigned (country is None or empty).
    if target_date is not None:
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        stmt = select(Message).where(
            ((Message.country.is_(None)) | (Message.country == "")),
            Message.event_timestamp >= start_dt,
            Message.event_timestamp <= end_dt,
        )
    else:
        stmt = select(Message).where((Message.country.is_(None)) | (Message.country == ""))
    if sources:
        stmt = stmt.where(Message.source.in_(sources))
    if labels:
        stmt = stmt.where(Message.label.in_(labels))
    if event_types:
        stmt = stmt.where(Message.event_type.in_(event_types))
    msgs = session.exec(stmt).all()
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
    if target_date is not None:
        date_value = target_date
    elif msgs:
        date_value = max(m.created_at for m in msgs).date()
    else:
        date_value = datetime.utcnow().date()
    return CountryEventsResponse(
        date=date_value,
        country="Sans pays",
        zones=zones_payload,
    )


def get_country_events_service(
    country: str,
    target_date: Optional[date],
    sources: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
    event_types: Optional[List[str]] = None,
    session: Session = None
) -> CountryEventsResponse:
    norm_country = country
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise ValueError("Pays non normalisé ou non géoréférencé")
    if target_date is not None:
        # Limit to a single day when a date is provided
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        stmt = select(Message).where(
            Message.event_timestamp >= start_dt,
            Message.event_timestamp <= end_dt,
            Message.country_norm == norm_country
        )
    else:
        # Otherwise return all events for the normalized country
        stmt = select(Message).where(
            Message.country_norm == norm_country
        )
    if sources:
        stmt = stmt.where(Message.source.in_(sources))
    if labels:
        stmt = stmt.where(Message.label.in_(labels))
    if event_types:
        stmt = stmt.where(Message.event_type.in_(event_types))
    msgs = session.exec(stmt).all()
    # Bucket events by region/location for the response
    buckets: Dict[Tuple[Optional[str], Optional[str]], List[Message]] = {}
    for m in msgs:
        key = (m.region, m.location)
        buckets.setdefault(key, []).append(m)
    # Build the ZoneEvents payload with previews and URLs
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
    # Pick a date for the response when no target_date is supplied
    if target_date is not None:
        date_value = target_date
    elif msgs:
        date_value = max(m.created_at for m in msgs).date()
    else:
        date_value = datetime.utcnow().date()
    return CountryEventsResponse(
        date=date_value,
        country=country,
        zones=zones_payload,
    )
