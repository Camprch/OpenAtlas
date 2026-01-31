from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional

# Summary counts for country activity endpoints
class CountryActivity(BaseModel):
    country: str
    events_count: int

# Country status including last active date
class CountryStatus(BaseModel):
    country: str
    events_count: int
    last_date: date

# Response payload for the active countries endpoint
class ActiveCountriesResponse(BaseModel):
    countries: List[CountryStatus]
    ignored_countries: List[str]

# Flattened event message used in API responses
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

# Group of events for a specific region/location
class ZoneEvents(BaseModel):
    region: Optional[str]
    location: Optional[str]
    messages_count: int
    messages: List[EventMessage]

# Full response for country event listings
class CountryEventsResponse(BaseModel):
    date: date
    country: str
    zones: List[ZoneEvents]
