# Met à jour le champ label des messages selon la correspondance source:label du .env



import unicodedata
import os
import re
from sqlmodel import Session, select
from app.database import engine
from app.models.message import Message


def norm(s):
    # Pour les usernames Telegram, on garde minuscule et on retire les @ éventuels
    return (s or '').lower().replace('@', '').strip()


# Récupère le mapping channel->label depuis le .env
def get_mapping_from_env(env_path):
    with open(env_path) as f:
        for line in f:
            if line.strip().startswith('SOURCES_TELEGRAM'):
                value = line.split('=', 1)[-1].strip().strip("'\"")
                pairs = re.split(r',\s*', value)
                mapping = {}
                for pair in pairs:
                    if ':' in pair:
                        channel, label = pair.split(':', 1)
                        mapping[norm(channel)] = label.strip()
                return mapping
    return {}

MAPPING = get_mapping_from_env('.env')
LABELS_ALLOWED = set(MAPPING.values())


with Session(engine) as session:
    messages = session.exec(select(Message)).all()
    n = 0
    for m in messages:
        channel = m.channel or ''
        channel_norm = norm(channel)
        label = MAPPING.get(channel_norm)
        m.label = label  # label=None si le channel n'est pas dans le mapping
        n += 1
    session.commit()
print(f"{n} messages mis à jour avec un label (mapping par channel Telegram).")
