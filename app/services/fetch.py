# app/services/fetch.py
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import os  # 👈 ajouté

from telethon import TelegramClient
from telethon.errors import UsernameInvalidError, UsernameNotOccupiedError
from telethon.sessions import StringSession  # 👈 ajouté

from app.config import get_settings

# Load settings once for fetch configuration
settings = get_settings()


def _parse_sources_env() -> Dict[str, str | None]:
    """
    Safe parsing of SOURCES_TELEGRAM from .env.

    Expected format:
        SOURCES_TELEGRAM="channel1:label1,channel2:label2,channel3"
    """
    raw = (settings.sources_telegram or "").strip()

    if not raw:
        return {}

    mapping: Dict[str, str | None] = {}

    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue

        # Strip '@' prefixes to avoid leaking full Telegram handles
        if part.startswith("@"):
            part = part[1:].strip()

        # Split channel / label if provided
        if ":" in part:
            chan, label = part.split(":", 1)
        else:
            chan, label = part, None

        # Sanitize channel name to allowed characters
        import re
        chan = re.sub(r"[^A-Za-z0-9_]", "", chan)
        if not chan:
            continue

        mapping[chan] = (label.strip() if label else None)

    return mapping


async def fetch_raw_messages_24h() -> List[Dict]:
    """
    Fetch messages from the configurable window (FETCH_WINDOW_HOURS) with a per-channel cap.
    """
    sources_map = _parse_sources_env()
    if not sources_map:
        print("[fetch] Aucun canal dans SOURCES_TELEGRAM.")
        return []

    # Build channel -> label lookup for downstream tagging
    channel_to_label = {chan: label for chan, label in sources_map.items()}

    max_per_channel = settings.max_messages_per_channel
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.fetch_window_hours)

    # Resolve Telegram session string from env or settings
    session_str = os.environ.get("TG_SESSION") or settings.telegram_session
    if session_str and session_str.strip():
        client = TelegramClient(
            StringSession(session_str.strip()),
            settings.telegram_api_id,
            settings.telegram_api_hash,
        )
    else:
        raise RuntimeError("Aucune string session Telegram trouvée. Renseignez TELEGRAM_SESSION dans le .env ou TG_SESSION dans les variables d'environnement.")

    results: List[Dict] = []

    # Connect to Telegram and pull recent messages for each configured channel
    async with client:
        for chan, orient in sources_map.items():
            try:
                entity = await client.get_entity(chan)
            except (UsernameInvalidError, UsernameNotOccupiedError) as e:
                print(f"[fetch] Canal invalide ou introuvable : {chan} ({e})")
                continue
            except Exception as e:
                print(f"[fetch] Erreur get_entity({chan}) : {e}")
                continue

            try:
                msgs = await client.get_messages(entity, limit=max_per_channel)
            except Exception as e:
                print(f"[fetch] Erreur get_messages({chan}) : {e}")
                continue

            for m in msgs:
                dt = getattr(m, "date", None)
                if dt is None:
                    continue
                if dt < cutoff:
                    continue

                # Skip empty messages
                text = getattr(m, "message", "") or ""
                if not text.strip():
                    continue

                # Prefer channel title for source label, fallback to username
                real_source = getattr(entity, "title", None) or getattr(entity, "username", chan)
                label = channel_to_label.get(chan)

                # Normalize message fields for the pipeline
                results.append(
                    {
                        "source": real_source,
                        "channel": chan,
                        "orientation": (orient or "inconnu").lower(),
                        "text": text,
                        "date": dt,
                        "telegram_message_id": m.id,
                        "label": label,
                    }
                )

    print(f"[fetch] Total messages 24h récupérés : {len(results)}")
    return results
