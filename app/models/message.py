# app/models/message.py
from datetime import datetime

from sqlmodel import SQLModel, Field
from sqlalchemy import Index, Column, String




class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    telegram_message_id: int | None = Field(default=None, index=True)
    source: str = Field(sa_column=Column(String(128)))
    channel: str | None = Field(default=None, index=True)

    raw_text: str
    translated_text: str | None = None

    country: str | None = Field(default=None, index=True)
    country_norm: str | None = Field(default=None, description="Nom canonique du pays, ou None si inconnu/non géoréférencé.")
    region: str | None = Field(default=None, index=True)
    location: str | None = Field(default=None, index=True)

    title: str | None = Field(default=None)
    event_type: str | None = Field(default=None, index=True)  # Ajouté
    event_timestamp: datetime | None = Field(default=None, index=True)

    orientation: str | None = Field(default=None, index=True)

    label: str | None = Field(default=None, sa_column=Column(String(255)), description="Label dynamique pour filtrage.")

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_message_country_created", "country", "created_at"),
        Index("ix_message_country_norm", "country_norm"),
        Index("ix_message_created_at_country_norm", "created_at", "country_norm"),
        Index("ix_message_country_norm_created_at", "country_norm", "created_at"),
    )
