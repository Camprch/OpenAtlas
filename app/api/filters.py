from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date, datetime
from typing import List, Optional
from sqlmodel import Session, select
from app.database import get_db
from app.models.message import Message
from app.services.fetch import _parse_sources_env


import json
import re
from pathlib import Path

router = APIRouter()

@router.get("/event_types")
def get_event_types():
    return [
        "Protest", "Conflict", "Political", "Natural disaster", "Crime",
        "Cyber Attack", "Public health", "Economic", "Security Alert", "Other"
    ]

@router.get("/labels", response_model=List[str])
def get_labels():
    # Retourne les labels du mapping settings (.env)
    labels = set()
    with open('.env') as f:
        for line in f:
            if line.strip().startswith('SOURCES_TELEGRAM'):
                value = line.split('=', 1)[-1].strip().strip("'\"")
                pairs = re.split(r',\s*', value)
                for pair in pairs:
                    if ':' in pair:
                        _, label = pair.split(':', 1)
                        labels.add(label.strip())
    return sorted(labels)

@router.get("/sources", response_model=List[str])
def get_sources():
    # Retourne les sources du mapping settings (.env)
    sources = []
    with open('.env') as f:
        for line in f:
            if line.strip().startswith('SOURCES_TELEGRAM'):
                value = line.split('=', 1)[-1].strip().strip("'\"")
                pairs = re.split(r',\s*', value)
                for pair in pairs:
                    if ':' in pair:
                        src, _ = pair.split(':', 1)
                        sources.append(src.strip())
    return sorted(sources)

# Charger les alias et coordonnées pays (chemin absolu depuis la racine du projet)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
COUNTRIES_JSON_PATH = BASE_DIR / "static" / "data" / "countries.json"
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
    # Utilise la date d'événement réelle (event_timestamp)
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
