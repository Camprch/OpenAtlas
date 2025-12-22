import os
from fastapi import APIRouter, HTTPException
from app.database import init_db

router = APIRouter()

@router.post("/admin/clear-db")
def clear_db():
    db_path = os.path.join(os.path.dirname(__file__), '../../data/osint.db')
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        # Réinitialise le schéma (recrée la base vide)
        init_db()
        return {"success": True, "message": "Base de données effacée et réinitialisée."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'effacement de la base : {e}")
