# Script pour insérer des messages de test avec label = source
from sqlmodel import Session
from app.database import engine
from app.models.message import Message
from datetime import datetime

sources = ["Telegram", "Twitter", "Facebook", "Signal"]

with Session(engine) as session:
    for i, src in enumerate(sources):
        msg = Message(
            telegram_message_id=1000 + i,
            source=src,
            channel=f"chan_{src.lower()}",
            raw_text=f"Message test {src}",
            translated_text=None,
            country="FR",
            country_norm="FR",
            region="Europe",
            location="Paris",
            title=f"Titre {src}",
            event_type="Test",
            event_timestamp=datetime.utcnow(),
            orientation=None,
            label=src,
            created_at=datetime.utcnow(),
        )
        session.add(msg)
    session.commit()
print("Messages de test insérés avec label = source.")
