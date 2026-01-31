# app/models/message.py
from datetime import datetime

from sqlmodel import SQLModel, Field
from sqlalchemy import Index, Column, String


# Core message entity for ingested events (stored in SQLModel/SQLAlchemy)
class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    telegram_message_id: int | None = Field(default=None, index=True)
    # Source/channel metadata used for filtering and attribution
    source: str = Field(sa_column=Column(String(128)))
    channel: str | None = Field(default=None, index=True)

    # Raw and translated content (translated_text may be null)
    raw_text: str
    translated_text: str | None = None

    # Geographic metadata derived from NLP/normalization
    country: str | None = Field(default=None, index=True)
    country_norm: str | None = Field(default=None, description="Nom canonique du pays, ou None si inconnu/non géoréférencé.")
    region: str | None = Field(default=None, index=True)
    location: str | None = Field(default=None, index=True)

    # Event classification fields
    title: str | None = Field(default=None)
    event_type: str | None = Field(default=None, index=True)
    event_timestamp: datetime | None = Field(default=None, index=True)

    # Optional directional/contextual tag
    orientation: str | None = Field(default=None, index=True)

    # Dynamic label used for UI filtering
    label: str | None = Field(default=None, sa_column=Column(String(255)), description="Label dynamique pour filtrage.")

    # Ingestion timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Common access patterns used by API queries
    __table_args__ = (
        Index("ix_message_country_created", "country", "created_at"),
        Index("ix_message_country_norm", "country_norm"),
        Index("ix_message_created_at_country_norm", "created_at", "country_norm"),
        Index("ix_message_country_norm_created_at", "country_norm", "created_at"),
    )
