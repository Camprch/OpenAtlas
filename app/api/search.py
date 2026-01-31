from fastapi import APIRouter, Query
from typing import List
from app.models.message import Message
from app.database import get_session
from sqlmodel import select
import unicodedata

# Router for search endpoints
router = APIRouter()


def normalize_text(text: str) -> str:
    # Lowercase, remove accents, and trim whitespace
    text = text.lower().strip()
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    return text


@router.get("/search/events", response_model=List[Message])
def search_events(q: str = Query(..., min_length=1)):
    # Use DB filtering first, then normalize text for accent-insensitive matching
    norm_q = normalize_text(q)
    with get_session() as session:
        # Broad SQL filters to reduce the candidate set
        results = session.exec(
            select(Message).where(
                (Message.translated_text != None) & (
                    (Message.translated_text.ilike(f"%{q}%")) |
                    (Message.country.ilike(f"%{q}%")) |
                    (Message.country_norm.ilike(f"%{q}%")) |
                    (Message.region.ilike(f"%{q}%")) |
                    (Message.location.ilike(f"%{q}%")) |
                    (Message.label.ilike(f"%{q}%")) |
                    (Message.event_type.ilike(f"%{q}%")) |
                    (Message.source.ilike(f"%{q}%"))
                )
            ).limit(100)
        ).all()
        # In-memory pass to enforce normalized substring matching
        filtered = [
            m for m in results
            if norm_q in normalize_text(m.translated_text)
            or (m.country and norm_q in normalize_text(m.country))
            or (m.country_norm and norm_q in normalize_text(m.country_norm))
            or (m.region and norm_q in normalize_text(m.region))
            or (m.location and norm_q in normalize_text(m.location))
            or (m.label and norm_q in normalize_text(m.label))
            or (m.event_type and norm_q in normalize_text(m.event_type))
            or (m.source and norm_q in normalize_text(m.source))
        ]
        return filtered
