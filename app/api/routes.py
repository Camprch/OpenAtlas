import subprocess
import json
import os
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Tuple
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from starlette.responses import StreamingResponse
from dotenv import dotenv_values, set_key
from pydantic import BaseModel
from sqlmodel import Session, select
from app.database import get_db
from app.models.message import Message
from app.api.session_wizard import router as session_wizard_router

router = APIRouter()
router.include_router(session_wizard_router)


# Nouvelle route pour lancer le vrai pipeline
import threading
import sys
from pathlib import Path


import threading

router = APIRouter()
router.include_router(session_wizard_router)


# --- Pipeline Progress Tracking & Annulation ---
pipeline_status = {
    "percent": 0,
    "step": "En attente",
    "running": False
}

# Stocke le process du pipeline pour pouvoir l'annuler
pipeline_process = {"proc": None}

def set_pipeline_status(percent, step):
    pipeline_status["percent"] = percent
    pipeline_status["step"] = step
    pipeline_status["running"] = percent < 100

@router.get("/pipeline-status")
def get_pipeline_status():
    return pipeline_status


@router.post("/run-pipeline")
def run_pipeline_real():
    """
    Lance réellement le pipeline Python (tools/run_pipeline.py) dans un thread et met à jour le statut en temps réel.
    """
    def target():
        import subprocess
        import os
        import sys
        from pathlib import Path
        import time

        set_pipeline_status(0, "Initialisation")
        project_root = Path(__file__).resolve().parent.parent.parent
        script_path = project_root / "tools" / "run_pipeline.py"

        proc = subprocess.Popen([
            sys.executable,
            str(script_path)
        ], cwd=str(project_root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        pipeline_process["proc"] = proc
        try:
            # Suivi des étapes par analyse de la sortie du script
            step_map = {
                "fetch_raw_messages_24h": (20, "Collecte"),
                "translate_messages": (50, "Traduction"),
                "enrich_messages": (70, "Enrichissement"),
                "dedupe_messages": (80, "Traitement"),
                "store_messages": (90, "Stockage"),
                "delete_old_messages": (95, "Nettoyage"),
                "Pipeline terminé": (100, "Terminé")
            }
            current_percent = 0
            current_step = "Initialisation"
            for line in proc.stdout:
                line = line.strip()
                for key, (percent, step) in step_map.items():
                    if key in line:
                        set_pipeline_status(percent, step)
                        current_percent = percent
                        current_step = step
                        break
                # Si annulé, on sort
                if pipeline_process["proc"] is None:
                    set_pipeline_status(100, "Annulé")
                    proc.terminate()
                    return
            proc.wait()
            set_pipeline_status(100, "Terminé")
        finally:
            pipeline_process["proc"] = None

    t = threading.Thread(target=target, daemon=True)
    t.start()
    return {"status": "started"}

# Route pour annuler le pipeline
@router.post("/stop-pipeline")
def stop_pipeline():
    proc = pipeline_process.get("proc")
    if proc and proc.poll() is None:
        proc.terminate()
        pipeline_process["proc"] = None
        set_pipeline_status(100, "Annulé")
        return {"status": "stopped"}
    return {"status": "no-process"}


class DatesResponse(BaseModel):
    dates: List[date]


class CountryActivity(BaseModel):
    country: str
    events_count: int


class CountryStatus(BaseModel):
    country: str
    events_count: int
    last_date: date


# Nouveau modèle pour exposer les pays ignorés
class ActiveCountriesResponse(BaseModel):
    countries: List[CountryStatus]
    ignored_countries: List[str]


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


class ZoneEvents(BaseModel):
    region: Optional[str]
    location: Optional[str]
    messages_count: int
    messages: List[EventMessage]


class CountryEventsResponse(BaseModel):
    date: date
    country: str
    zones: List[ZoneEvents]


# Fonction utilitaire pour charger les alias depuis countries.json et normaliser les noms de pays
def normalize_country_names(name: str, aliases: dict) -> list:
    if not name:
        return []
    # Sépare par virgule ou point-virgule, retire espaces, met en minuscules
    names = [n.strip().lower() for n in name.split(',') if n.strip()]
    result = []
    for n in names:
        norm = aliases.get(n, None)
        if norm:
            result.append(norm)
    return result

@router.get("/env")
def get_env_vars():
    """
    Retourne les variables du .env sous forme de dict.
    """
    env_path = os.path.join(os.path.dirname(__file__), '../../.env')
    if not os.path.exists(env_path):
        return {}
    return dotenv_values(env_path)

@router.post("/env")
def update_env_vars(
    updates: dict = Body(..., example={"OPENAI_API_KEY": "nouvelle_valeur"})
):
    """
    Met à jour une ou plusieurs variables dans le .env.
    """
    env_path = os.path.join(os.path.dirname(__file__), '../../.env')
    print(f"[DEBUG] Writing to .env at: {os.path.abspath(env_path)}")
    if not os.path.exists(env_path):
        # Si .env n'existe pas, on tente de copier .env.example ou créer un fichier vide
        example_path = os.path.join(os.path.dirname(__file__), '../../.env.example')
        if os.path.exists(example_path):
            import shutil
            shutil.copy(example_path, env_path)
            print(f"[DEBUG] .env créé à partir de .env.example")
        else:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write('')
            print(f"[DEBUG] .env créé vide")
    for key, value in updates.items():
        set_key(env_path, key, str(value))
    return {"success": True, "updated": list(updates.keys())}
# Charger les alias une seule fois au démarrage
COUNTRIES_JSON_PATH = os.path.join(os.path.dirname(__file__), '../../static/data/countries.json')
with open(COUNTRIES_JSON_PATH, encoding='utf-8') as f:
    _countries_data = json.load(f)
    COUNTRY_ALIASES = _countries_data.get('aliases', {})
    COUNTRY_COORDS = _countries_data.get('coordinates', {})



@router.get("/dates", response_model=DatesResponse)
def get_available_dates(session: Session = Depends(get_db)):
    """
    Renvoie les 10 dernières dates (sur created_at) où il y a des messages.
    """
    stmt = select(Message.created_at).order_by(Message.created_at.desc())
    rows = session.exec(stmt).all()

    seen = set()
    dates_list: List[date] = []
    for dt in rows:
        d = dt.date()
        if d not in seen:
            seen.add(d)
            dates_list.append(d)
        if len(dates_list) >= 10:
            break

    return DatesResponse(dates=dates_list)



@router.get("/countries/active", response_model=ActiveCountriesResponse)
def get_active_countries(
    days: int = Query(30, ge=1),
    date_filter: Optional[date] = Query(None, alias="date"),
    session: Session = Depends(get_db),
):
    """
    Renvoie les pays qui ont des messages à une date précise (si 'date' fourni),
    sinon dans les X derniers jours, avec le nombre d'événements et la dernière date d'activité.
    Fournit aussi la liste des pays ignorés (non normalisés).
    """
    if date_filter:
        # Filtre exact sur la date
        start_dt = datetime.combine(date_filter, datetime.min.time())
        end_dt = datetime.combine(date_filter, datetime.max.time())
        stmt = select(Message.country, Message.created_at).where(
            Message.created_at >= start_dt,
            Message.created_at <= end_dt,
            Message.country.is_not(None),
        )
    else:
        now = datetime.utcnow()
        start_dt = now - timedelta(days=days)
        stmt = select(Message.country, Message.created_at).where(
            Message.created_at >= start_dt,
            Message.country.is_not(None),
        )
    rows = session.exec(stmt).all()

    stats: Dict[str, Dict[str, object]] = {}
    ignored_countries = set()
    for country, created_at in rows:
        if not country:
            continue
        country = country.strip()
        if not country:
            continue
        # Multi-pays : normalisation multiple
        norm_countries = normalize_country_names(country, COUNTRY_ALIASES)
        if not norm_countries:
            ignored_countries.add(country)
            continue  # ignorer les pays non normalisés
        d = created_at.date()
        for norm_country in norm_countries:
            if norm_country not in stats:
                stats[norm_country] = {"count": 0, "last_date": d}
            stats[norm_country]["count"] += 1
            if d > stats[norm_country]["last_date"]:
                stats[norm_country]["last_date"] = d

    # Ne garder que les pays qui ont une coordonnée (donc normalisés)
    result = [
        CountryStatus(
            country=c,
            events_count=v["count"],
            last_date=v["last_date"],
        )
        for c, v in stats.items() if c in COUNTRY_COORDS
    ]
    # tri optionnel : pays les plus actifs en premier
    result.sort(key=lambda c: c.events_count, reverse=True)
    return ActiveCountriesResponse(countries=result, ignored_countries=sorted(ignored_countries))

@router.get(
    "/countries/{country}/latest-events",
    response_model=CountryEventsResponse,
)
def get_country_latest_events(
    country: str,
    session: Session = Depends(get_db),
):
    """
    Liste les événements pour un pays à la date la plus récente (sur created_at).
    """
    # 1) On cherche la dernière date pour ce pays
    # On normalise l'identifiant reçu
    norm_country = country
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")

    # On cherche tous les messages qui contiennent ce pays dans la liste normalisée
    # (multi-pays)
    stmt_last = (
        select(Message.created_at, Message.country)
        .order_by(Message.created_at.desc())
    )
    rows = session.exec(stmt_last).all()
    last_date = None
    for created_at, raw_country in rows:
        norm_countries = normalize_country_names(raw_country, COUNTRY_ALIASES)
        if norm_country in norm_countries:
            last_date = created_at
            break
    if not last_date:
        raise HTTPException(status_code=404, detail="Aucun événement pour ce pays")

    target_date = last_date.date()

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    stmt = select(Message).where(
        Message.created_at >= start_dt,
        Message.created_at <= end_dt,
    )
    msgs = session.exec(stmt).all()
    # Filtrer pour ne garder que ceux qui contiennent ce pays
    msgs = [m for m in msgs if norm_country in normalize_country_names(m.country, COUNTRY_ALIASES)]

    buckets: Dict[Tuple[Optional[str], Optional[str]], List[Message]] = {}
    for m in msgs:
        key = (m.region, m.location)
        buckets.setdefault(key, []).append(m)

    zones_payload: List[ZoneEvents] = []

    for (region, location), items in buckets.items():
        event_messages: List[EventMessage] = []
        for m in items:
            url = None
            if m.channel and m.telegram_message_id:
                url = f"https://t.me/{m.channel}/{m.telegram_message_id}"

            full_text = (m.translated_text or m.raw_text or "").strip()
            preview = full_text[:277] + "..." if len(full_text) > 280 else full_text

            event_messages.append(
                EventMessage(
                    id=m.id,
                    telegram_message_id=m.telegram_message_id,
                    channel=m.channel,
                    title=m.title,
                    source=m.source,
                    orientation=m.orientation,
                    event_timestamp=m.event_timestamp,
                    created_at=m.created_at,
                    url=url,
                    translated_text=full_text,
                    preview=preview,
                )
            )

        zones_payload.append(
            ZoneEvents(
                region=region,
                location=location,
                messages_count=len(items),
                messages=event_messages,
            )
        )

    zones_payload.sort(key=lambda z: z.messages_count, reverse=True)

    return CountryEventsResponse(
        date=target_date,
        country=country,
        zones=zones_payload,
    )


@router.get("/countries", response_model=List[CountryActivity])
def get_countries_activity(
    target_date: date = Query(..., alias="date"),
    session: Session = Depends(get_db),
):
    """
    Compte les messages par pays pour une date donnée (sur created_at).
    """
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    stmt = select(Message).where(
        Message.created_at >= start_dt,
        Message.created_at <= end_dt,
    )
    msgs = session.exec(stmt).all()

    counts: Dict[str, int] = {}
    for m in msgs:
        if not m.country:
            continue
        country = m.country.strip()
        if not country:
            continue
        counts[country] = counts.get(country, 0) + 1

    result = [
        CountryActivity(country=c, events_count=n)
        for c, n in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return result


@router.get(
    "/countries/{country}/events",
    response_model=CountryEventsResponse,
)
def get_country_events(
    country: str,
    target_date: date = Query(..., alias="date"),
    session: Session = Depends(get_db),
):
    """
    Liste des événements pour un pays + date (groupés par région / location).
    """
    # On utilise la même logique de normalisation/multi-pays que latest-events
    norm_country = country
    if not norm_country or norm_country not in COUNTRY_COORDS:
        raise HTTPException(status_code=404, detail="Pays non normalisé ou non géoréférencé")

    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    stmt = select(Message).where(
        Message.created_at >= start_dt,
        Message.created_at <= end_dt,
    )
    msgs = session.exec(stmt).all()
    # Filtrer pour ne garder que ceux qui contiennent ce pays
    msgs = [m for m in msgs if norm_country in normalize_country_names(m.country, COUNTRY_ALIASES)]

    buckets: Dict[Tuple[Optional[str], Optional[str]], List[Message]] = {}
    for m in msgs:
        key = (m.region, m.location)
        buckets.setdefault(key, []).append(m)

    zones_payload: List[ZoneEvents] = []

    for (region, location), items in buckets.items():
        event_messages: List[EventMessage] = []
        for m in items:
            url = None
            if m.channel and m.telegram_message_id:
                url = f"https://t.me/{m.channel}/{m.telegram_message_id}"

            full_text = (m.translated_text or m.raw_text or "").strip()
            preview = full_text[:277] + "..." if len(full_text) > 280 else full_text

            event_messages.append(
                EventMessage(
                    id=m.id,
                    telegram_message_id=m.telegram_message_id,
                    channel=m.channel,
                    title=m.title,
                    source=m.source,
                    orientation=m.orientation,
                    event_timestamp=m.event_timestamp,
                    created_at=m.created_at,
                    url=url,
                    translated_text=full_text,
                    preview=preview,
                )
            )

        zones_payload.append(
            ZoneEvents(
                region=region,
                location=location,
                messages_count=len(items),
                messages=event_messages,
            )
        )

    zones_payload.sort(key=lambda z: z.messages_count, reverse=True)

    return CountryEventsResponse(
        date=target_date,
        country=country,
        zones=zones_payload,
    )
