# tools/backfill_country_norm.py
"""
Script de backfill pour remplir le champ country_norm sur les anciens messages.
Sûr, batché, sans perte de données.
"""
from app.models.message import Message
from app.utils.country_norm import compute_country_norm
from app.database import get_session
from sqlmodel import select
import sys

BATCH_SIZE = 500

def backfill_country_norm():
    with get_session() as session:
        all_msgs = session.exec(select(Message).where(Message.country_norm == None)).all()
        total_count = len(all_msgs)
        print(f"[backfill] {total_count} messages à mettre à jour.")
        offset = 0
        while True:
            msgs = session.exec(
                select(Message)
                .where(Message.country_norm == None)
                .offset(offset)
                .limit(BATCH_SIZE)
            ).all()
            if not msgs:
                break
            for m in msgs:
                norm = compute_country_norm(m.country)
                m.country_norm = norm
                if norm is None and m.country:
                    print(f"[ALERTE] country inconnu/non géoréférencé: '{m.country}' (id: {m.id})")
            session.commit()
            print(f"[backfill] {min(offset+BATCH_SIZE, total_count)}/{total_count} messages traités.")
            offset += BATCH_SIZE
    print("[backfill] Terminé.")

if __name__ == "__main__":
    backfill_country_norm()
