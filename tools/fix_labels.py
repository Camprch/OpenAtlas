# tools/fix_labels.py
"""
Script pour ajouter les labels manquants dans la base, selon le mapping SOURCES_TELEGRAM du .env
"""
import os
from dotenv import load_dotenv
from sqlmodel import Session, select
from app.database import engine
from app.models.message import Message
from app.config import get_settings

load_dotenv()
settings = get_settings()

def parse_sources_env():
    raw = (settings.sources_telegram or "").strip()
    mapping = {}
    if not raw:
        return mapping
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if part.startswith("@"):  # Nettoyage
            part = part[1:].strip()
        if ":" in part:
            chan, label = part.split(":", 1)
        else:
            chan, label = part, None
        import re
        chan = re.sub(r"[^A-Za-z0-9_]", "", chan)
        if not chan:
            continue
        mapping[chan] = label.strip() if label else None
    return mapping

def main():
    mapping = parse_sources_env()
    if not mapping:
        print("Aucun mapping SOURCES_TELEGRAM trouvé.")
        return
    with Session(engine) as session:
        msgs = session.exec(select(Message).where(Message.label == None)).all()
        print(f"{len(msgs)} messages sans label à corriger...")
        count = 0
        for m in msgs:
            chan = m.channel
            label = mapping.get(chan)
            if label:
                m.label = label
                count += 1
        session.commit()
        print(f"{count} messages mis à jour avec un label.")

if __name__ == "__main__":
    main()
