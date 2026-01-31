# tools/run_pipeline.py

import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Load .env values before importing settings
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


RUN_ID = datetime.utcnow().strftime("%Y%m%d-%H%M%S")


def log(message: str) -> None:
    # Log with a timestamp and run identifier for grouping
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[pipeline] {timestamp} | run={RUN_ID} | {message}")
    sys.stdout.flush()


def mask_secret(value: str | None, keep: int = 4) -> str:
    # Mask secrets before printing to logs
    if not value:
        return "MISSING"
    value = str(value)
    if len(value) <= keep:
        return "*" * len(value)
    return f"{value[:keep]}***"


def summarize_messages(messages: list[dict], label: str) -> None:
    # Emit counts and field coverage for a batch of messages
    if not messages:
        log(f"[{label}] 0 messages.")
        return
    channels = {m.get("channel") for m in messages if m.get("channel")}
    sources = {m.get("source") for m in messages if m.get("source")}
    with_text = sum(1 for m in messages if (m.get("text") or "").strip())
    with_translated = sum(1 for m in messages if (m.get("translated_text") or "").strip())
    with_country = sum(1 for m in messages if (m.get("country") or "").strip())
    with_region = sum(1 for m in messages if (m.get("region") or "").strip())
    with_location = sum(1 for m in messages if (m.get("location") or "").strip())
    with_title = sum(1 for m in messages if (m.get("title") or "").strip())
    with_event_type = sum(1 for m in messages if (m.get("event_type") or "").strip())
    log(
        f"[{label}] total={len(messages)} | channels={len(channels)} | sources={len(sources)} | "
        f"text={with_text} | translated={with_translated} | country={with_country} | "
        f"region={with_region} | location={with_location} | title={with_title} | event_type={with_event_type}"
    )
    if channels:
        # Summarize top channels to spot noisy sources quickly
        channel_counts: dict[str, int] = {}
        for m in messages:
            c = m.get("channel")
            if not c:
                continue
            channel_counts[c] = channel_counts.get(c, 0) + 1
        top_channels = sorted(channel_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
        top_str = ", ".join(f"{c}:{n}" for c, n in top_channels)
        log(f"[{label}] top_channels={top_str}")


async def check_telegram_connection(settings) -> None:
    # Validate Telegram credentials and session by connecting and fetching self
    log("[CHECK][TELEGRAM] Starting connection check...")
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except Exception as e:
        log(f"[CHECK][TELEGRAM][ERROR] Telethon import failed: {e}")
        return
    if not settings.telegram_session or not settings.telegram_api_id or not settings.telegram_api_hash:
        log("[CHECK][TELEGRAM][ERROR] Missing Telegram credentials; aborting.")
        raise RuntimeError("Telegram settings missing")
    try:
        client = TelegramClient(
            StringSession(settings.telegram_session),
            settings.telegram_api_id,
            settings.telegram_api_hash,
        )
        await asyncio.wait_for(client.connect(), timeout=10)
        if not await asyncio.wait_for(client.is_user_authorized(), timeout=10):
            log("[CHECK][TELEGRAM][ERROR] Session not authorized.")
            raise RuntimeError("Telegram session not authorized")
        else:
            me = await asyncio.wait_for(client.get_me(), timeout=10)
            username = getattr(me, "username", None) or "unknown"
            log(f"[CHECK][TELEGRAM][OK] Connected as {username}.")
        await asyncio.wait_for(client.disconnect(), timeout=10)
    except asyncio.TimeoutError:
        log("[CHECK][TELEGRAM][ERROR] Connection check timed out.")
        raise
    except Exception as e:
        log(f"[CHECK][TELEGRAM][ERROR] {e}")
        raise


def check_openai_connection(settings) -> None:
    # Validate OpenAI connectivity with a lightweight ping
    log("[CHECK][OPENAI] Starting connection check...")
    if not settings.openai_api_key or not settings.openai_model:
        log("[CHECK][OPENAI][ERROR] Missing OpenAI settings; aborting.")
        raise RuntimeError("OpenAI settings missing")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.responses.create(
            model=settings.openai_model,
            input="ping",
            timeout=10,
        )
        _ = resp.output_text if hasattr(resp, "output_text") else str(resp)
        log("[CHECK][OPENAI][OK] Response received.")
    except Exception as e:
        log(f"[CHECK][OPENAI][ERROR] {e}")
        raise


def store_messages(messages: list[dict]) -> None:
    """
    Enregistre les messages dans SQLite.
    """
    # Persist messages and report unknown countries once per run
    unknown_countries: list[str] = []
    with get_session() as session:
        for msg in messages:
            raw_country = msg.get("country")
            country_norm = compute_country_norm(raw_country)
            if country_norm is None and raw_country:
                unknown_countries.append(str(raw_country))
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
    if unknown_countries:
        unique_unknowns = sorted(set(unknown_countries))
        sample = ", ".join(unique_unknowns[:10])
        log(f"[ALERT] Unknown/non-geocoded countries: {len(unique_unknowns)} (sample: {sample})")
    log(f"[STORE] Stored {len(messages)} messages.")


def filter_existing_messages(messages: list[dict]) -> list[dict]:
    """
    Filtre les messages déjà présents en base (par channel + telegram_message_id).
    """
    # Drop messages that already exist in the database
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
    log(f"[DEDUP] Existing in DB: {len(messages)-len(filtered)} skipped.")
    return filtered


def delete_old_messages(days: int = 10) -> None:
    """
    Supprime les messages dont l'event_timestamp est plus vieux que X jours.
    """
    # Use settings to delete old rows by event_timestamp
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
    log(f"[CLEAN] Deleted messages older than {days} days ({deleted}).")


async def run_pipeline_once():
    # Orchestrate the full pipeline with connectivity checks and step logging
    from app.config import get_settings
    try:
        settings = get_settings()
    except Exception as e:
        log(f"[CONFIG] Failed to load settings: {e}")
        raise

    log("[CONFIG] Settings loaded.")
    log(f"[CONFIG] fetch_window_hours={settings.fetch_window_hours} | auto_delete_days={settings.auto_delete_days} | batch_size={settings.batch_size}")
    log(f"[CONFIG] openai_api_key={mask_secret(settings.openai_api_key)} | openai_model={settings.openai_model}")
    log(f"[CONFIG] telegram_api_id={'SET' if settings.telegram_api_id else 'MISSING'} | telegram_api_hash={mask_secret(settings.telegram_api_hash)}")
    log(f"[CONFIG] telegram_session={'SET' if settings.telegram_session else 'MISSING'}")
    if not settings.telegram_api_id or not settings.telegram_api_hash or not settings.telegram_session:
        log("[CONFIG][WARN] Telegram credentials are incomplete; fetch will likely fail.")
    if not settings.openai_api_key or not settings.openai_model:
        log("[CONFIG][WARN] OpenAI settings are incomplete; translation/enrichment will likely fail.")

    await check_telegram_connection(settings)
    check_openai_connection(settings)

    log("init_db()")
    init_db()

    log("fetch_raw_messages_24h")
    log("[FETCH] Starting...")
    try:
        raw_messages = await fetch_raw_messages_24h()
    except Exception as e:
        log(f"[FETCH][ERROR] {e}")
        raise
    summarize_messages(raw_messages, "FETCH")
    if not raw_messages:
        log("[FETCH] No messages to process.")
        return

    log("dedupe_messages")
    log("[DEDUP] Filtering already-stored messages...")
    raw_messages = filter_existing_messages(raw_messages)
    if not raw_messages:
        log("[DEDUP] All messages already in DB. Nothing to do.")
        return

    log("translate_messages")
    log("[TRAD] Translating messages...")
    try:
        translate_messages(raw_messages)
    except Exception as e:
        log(f"[TRAD][ERROR] {e}")
        raise
    summarize_messages(raw_messages, "TRAD")

    log("enrich_messages")
    log("[ENRICH] Enriching messages...")
    try:
        enrich_messages(raw_messages)
    except Exception as e:
        log(f"[ENRICH][ERROR] {e}")
        raise
    summarize_messages(raw_messages, "ENRICH")

    log("dedupe_messages")
    log("[DEDUP] De-duplicating messages...")
    deduped = dedupe_messages(raw_messages)
    log(f"[DEDUP] After dedupe: {len(deduped)} messages.")

    log("store_messages")
    log("[STORE] Writing to DB...")
    store_messages(deduped)

    log("delete_old_messages")
    delete_old_messages(days=10)
    log("Pipeline terminé")


if __name__ == "__main__":
    try:
        asyncio.run(run_pipeline_once())
    except Exception as e:
        log(f"[ABORTED] {e}")
        raise
