from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date, datetime
from typing import List, Optional
from sqlmodel import Session, select
from app.database import get_db
from app.models.message import Message
import json
from pathlib import Path

# Router for filter metadata endpoints
router = APIRouter()

@router.get("/event_types", response_model=List[str])
def get_event_types(session: Session = Depends(get_db)):
    # Return distinct, non-null event types found in the DB
    stmt = select(Message.event_type).where(Message.event_type.is_not(None)).distinct().order_by(Message.event_type)
    rows = session.exec(stmt).all()
    return [row for row in rows if row]

@router.get("/labels", response_model=List[str])
def get_labels(session: Session = Depends(get_db)):
    # Return distinct, non-null labels found in the DB
    stmt = select(Message.label).where(Message.label.is_not(None)).distinct().order_by(Message.label)
    rows = session.exec(stmt).all()
    labels = []
    for row in rows:
        if row:
            labels.append(row)
    return sorted(set(labels))

@router.get("/sources", response_model=List[str])
def get_sources(session: Session = Depends(get_db)):
    # Return distinct, non-null human-readable sources found in the DB
    stmt = select(Message.source).where(Message.source.is_not(None)).distinct().order_by(Message.source)
    rows = session.exec(stmt).all()
    sources = [row for row in rows if row]
    return sorted(set(sources))

# Load country aliases and coordinates from static data
BASE_DIR = Path(__file__).resolve().parent.parent.parent
COUNTRIES_JSON_PATH = BASE_DIR / "static" / "data" / "countries.json"
with open(COUNTRIES_JSON_PATH, encoding='utf-8') as f:
    _countries_data = json.load(f)
    COUNTRY_ALIASES = _countries_data.get('aliases', {})
    COUNTRY_COORDS = _countries_data.get('coordinates', {})

def normalize_country_names(name: str, aliases: dict) -> list:
    # Normalize comma-separated country names using the aliases mapping
    if not name:
        return []
    names = [n.strip().lower() for n in name.split(',') if n.strip()]
    result = []
    for n in names:
        norm = aliases.get(n, None)
        if norm:
            result.append(norm)
    return result

@router.get("/countries/{country}/sources", response_model=List[str])
def get_country_sources(
    country: str,
    target_date: Optional[date] = Query(None, alias="date"),
    session: Session = Depends(get_db),
):
    norm_country = country
    # Validate the country against available coordinates
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")
    stmt = select(Message).where(Message.country_norm == norm_country)
    if target_date:
        # Limit to a single day when a date filter is provided
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        stmt = stmt.where(Message.event_timestamp >= start_dt, Message.event_timestamp <= end_dt)
    msgs = session.exec(stmt).all()
    sources = sorted(set(m.source for m in msgs if m.source))
    return sources

@router.get("/countries/{country}/labels", response_model=List[str])
def get_country_labels(
    country: str,
    target_date: Optional[date] = Query(None, alias="date"),
    session: Session = Depends(get_db),
):
    norm_country = country
    # Validate the country against available coordinates
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")
    stmt = select(Message).where(Message.country_norm == norm_country)
    if target_date:
        # Limit to a single day when a date filter is provided
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        stmt = stmt.where(Message.event_timestamp >= start_dt, Message.event_timestamp <= end_dt)
    msgs = session.exec(stmt).all()
    labels = set()
    for m in msgs:
        if hasattr(m, 'label') and m.label:
            if isinstance(m.label, list):
                labels.update(m.label)
            else:
                labels.add(m.label)
    return sorted(labels)

@router.get("/countries/{country}/event_types", response_model=List[str])
def get_country_event_types(
    country: str,
    target_date: Optional[date] = Query(None, alias="date"),
    session: Session = Depends(get_db),
):
    norm_country = country
    # Validate the country against available coordinates
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")
    stmt = select(Message).where(Message.country_norm == norm_country)
    if target_date:
        # Limit to a single day when a date filter is provided
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        stmt = stmt.where(Message.event_timestamp >= start_dt, Message.event_timestamp <= end_dt)
    msgs = session.exec(stmt).all()
    event_types = set()
    for m in msgs:
        if hasattr(m, 'event_type') and m.event_type:
            if isinstance(m.event_type, list):
                event_types.update(m.event_type)
            else:
                event_types.add(m.event_type)
    return sorted(event_types)

@router.get("/dates", response_model=List[date])
def get_available_dates(session: Session = Depends(get_db)):
    # Use the actual event timestamp to build a recent dates list
    stmt = select(Message.event_timestamp).where(Message.event_timestamp != None).order_by(Message.event_timestamp.desc())
    rows = session.exec(stmt).all()
    seen = set()
    dates_list = []
    for dt in rows:
        d = dt.date()
        if d not in seen:
            seen.add(d)
            dates_list.append(d)
        if len(dates_list) >= 10:
            break
    return dates_list
