import os
from fastapi import APIRouter, HTTPException
from app.database import init_db

router = APIRouter()

@router.post("/admin/clear-db")
def clear_db():
    # Resolve the SQLite DB path relative to this file
    db_path = os.path.join(os.path.dirname(__file__), '../../data/osint.db')
    try:
        # Remove the file if it exists, then recreate an empty schema
        if os.path.exists(db_path):
            os.remove(db_path)
        init_db()
        return {"success": True, "message": "Base de données effacée et réinitialisée."}
    except Exception as e:
        # Surface filesystem/DB failures as a 500 with context
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'effacement de la base : {e}")
