from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date, datetime
from typing import List, Optional
from sqlmodel import Session, select
from app.database import get_db
from app.models.message import Message
import os
import json

router = APIRouter()

# Charger les alias et coordonnées pays
COUNTRIES_JSON_PATH = os.path.join(os.path.dirname(__file__), '../../../static/data/countries.json')
with open(COUNTRIES_JSON_PATH, encoding='utf-8') as f:
    _countries_data = json.load(f)
    COUNTRY_ALIASES = _countries_data.get('aliases', {})
    COUNTRY_COORDS = _countries_data.get('coordinates', {})

def normalize_country_names(name: str, aliases: dict) -> list:
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
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")
    stmt = select(Message)
    if target_date:
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        stmt = stmt.where(Message.created_at >= start_dt, Message.created_at <= end_dt)
    msgs = session.exec(stmt).all()
    msgs = [m for m in msgs if norm_country in normalize_country_names(m.country, COUNTRY_ALIASES)]
    sources = sorted(set(m.source for m in msgs if m.source))
    return sources

@router.get("/countries/{country}/labels", response_model=List[str])
def get_country_labels(
    country: str,
    target_date: Optional[date] = Query(None, alias="date"),
    session: Session = Depends(get_db),
):
    norm_country = country
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")
    stmt = select(Message)
    if target_date:
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        stmt = stmt.where(Message.created_at >= start_dt, Message.created_at <= end_dt)
    msgs = session.exec(stmt).all()
    msgs = [m for m in msgs if norm_country in normalize_country_names(m.country, COUNTRY_ALIASES)]
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
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")
    stmt = select(Message)
    if target_date:
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())
        stmt = stmt.where(Message.created_at >= start_dt, Message.created_at <= end_dt)
    msgs = session.exec(stmt).all()
    msgs = [m for m in msgs if norm_country in normalize_country_names(m.country, COUNTRY_ALIASES)]
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
    stmt = select(Message.created_at).order_by(Message.created_at.desc())
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
