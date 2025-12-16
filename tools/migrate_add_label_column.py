# Script de migration pour ajouter le champ 'label' à la table message
# Usage : python tools/migrate_add_label_column.py


from sqlmodel import SQLModel, Session
from sqlalchemy import Column, String, text
from app.database import engine
from sqlalchemy.exc import OperationalError


def add_label_column():
    with engine.connect() as conn:
        try:
            conn.execute(text('ALTER TABLE message ADD COLUMN label VARCHAR(255)'))
        except OperationalError as e:
            if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
                print('Colonne label déjà existante, rien à faire.')
            else:
                raise
        else:
            print('Colonne label ajoutée avec succès.')

if __name__ == "__main__":
    add_label_column()
