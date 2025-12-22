# tools/run_pipeline.py

import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Ajout pour charger le .env
from dotenv import load_dotenv
load_dotenv()

import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.database import init_db, get_session
from app.models.message import Message
from app.utils.country_norm import compute_country_norm
from sqlmodel import select

from app.services.fetch import fetch_raw_messages_24h
from app.services.translation import translate_messages
from app.services.enrichment import enrich_messages
from app.services.dedupe import dedupe_messages


def store_messages(messages: list[dict]) -> None:
    """
    Enregistre les messages dans SQLite.
    """
    with get_session() as session:
        for msg in messages:
            raw_country = msg.get("country")
            country_norm = compute_country_norm(raw_country)
            if country_norm is None and raw_country:
                print(f"[ALERTE] country inconnu/non géoréférencé: '{raw_country}' (id: {msg.get('telegram_message_id')})")
            m = Message(
                source=msg.get("source") or "unknown",
                channel=msg.get("channel"),
                raw_text=msg.get("text", ""),
                translated_text=msg.get("translated_text"),
                country=raw_country,
                country_norm=country_norm,
                region=msg.get("region"),
                location=msg.get("location"),
                title=msg.get("title"),
                event_type=msg.get("event_type"),
                event_timestamp=msg.get("date"),
                telegram_message_id=msg.get("telegram_message_id"),
                orientation=msg.get("orientation"),
                label=msg.get("label"),
            )
            session.add(m)
        session.commit()
    print(f"[pipeline] {len(messages)} messages stockés.")


def filter_existing_messages(messages: list[dict]) -> list[dict]:
    """
    Filtre les messages déjà présents en base (par channel + telegram_message_id).
    """
    if not messages:
        return []
    keys = [(m.get("channel"), m.get("telegram_message_id")) for m in messages]
    channels = set(k[0] for k in keys if k[0] is not None)
    ids = set(k[1] for k in keys if k[1] is not None)
    if not channels or not ids:
        return messages
    with get_session() as session:
        stmt = select(Message.channel, Message.telegram_message_id).where(
            Message.channel.in_(channels),
            Message.telegram_message_id.in_(ids)
        )
        existing = set((row[0], row[1]) for row in session.exec(stmt).all())
    filtered = [m for m in messages if (m.get("channel"), m.get("telegram_message_id")) not in existing]
    print(f"[pipeline] {len(messages)-len(filtered)} messages déjà en base ignorés.")
    return filtered


def delete_old_messages(days: int = 10) -> None:
    """
    Supprime les messages dont l'event_timestamp est plus vieux que X jours.
    """
    from datetime import timezone
    from app.config import get_settings
    settings = get_settings()
    days = settings.auto_delete_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with get_session() as session:
        from sqlmodel import delete

        # On supprime directement en SQL, pas besoin de charger les objets en mémoire
        stmt = delete(Message).where(Message.event_timestamp < cutoff)
        result = session.exec(stmt)
        session.commit()

    deleted = getattr(result, "rowcount", None)
    print(f"[pipeline] Messages plus vieux que {days} jours supprimés ({deleted}).")


async def run_pipeline_once():
    from app.config import get_settings
    settings = get_settings()
    print(f"[pipeline] Fenêtre de collecte (FETCH_WINDOW_HOURS) utilisée : {settings.fetch_window_hours}")
    sys.stdout.flush()
    print("[pipeline] init_db()")
    sys.stdout.flush()
    init_db()

    print("fetch_raw_messages_24h")
    sys.stdout.flush()
    print("[pipeline] fetch_raw_messages_24h()")
    sys.stdout.flush()
    raw_messages = await fetch_raw_messages_24h()
    print(f"[pipeline] [FETCH] Terminé : {len(raw_messages)} messages collectés.")
    sys.stdout.flush()
    if not raw_messages:
        print("[pipeline] Aucun message à traiter.")
        sys.stdout.flush()
        return
    print("dedupe_messages")
    sys.stdout.flush()
    print("[pipeline] [DÉDUP] Début filtrage doublons...")
    sys.stdout.flush()
    raw_messages = filter_existing_messages(raw_messages)
    if not raw_messages:
        print("[pipeline] Tous les messages sont déjà en base. Rien à faire.")
        sys.stdout.flush()
        return
    print("translate_messages")
    sys.stdout.flush()
    print("[pipeline] [TRAD] Traduction des messages par lot...")
    sys.stdout.flush()
    translate_messages(raw_messages)
    print("enrich_messages")
    sys.stdout.flush()
    print("[pipeline] [ENRICH] Enrichissement des messages...")
    sys.stdout.flush()
    enrich_messages(raw_messages)
    print("dedupe_messages")
    sys.stdout.flush()
    print("[pipeline] [DÉDUP] Déduplication des messages...")
    sys.stdout.flush()
    deduped = dedupe_messages(raw_messages)
    print(f"[pipeline] [ENRICH] Après déduplication : {len(deduped)} messages.")
    sys.stdout.flush()
    print("store_messages")
    sys.stdout.flush()
    print("[pipeline] [STOCKAGE] Stockage en base...")
    sys.stdout.flush()
    store_messages(deduped)

    print("delete_old_messages")
    sys.stdout.flush()
    print("[pipeline] delete_old_messages()")
    sys.stdout.flush()
    delete_old_messages(days=10)
    print("Pipeline terminé")
    sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(run_pipeline_once())
