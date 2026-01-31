from fastapi import APIRouter, HTTPException
from sqlmodel import SQLModel
from app.database import init_db, engine, is_sqlite, DB_PATH

router = APIRouter()

@router.post("/admin/clear-db")
def clear_db():
    try:
        if is_sqlite:
            # Remove the file if it exists, then recreate an empty schema
            if DB_PATH.exists():
                DB_PATH.unlink()
            init_db()
        else:
            # Drop and recreate tables for non-SQLite backends
            SQLModel.metadata.drop_all(engine)
            init_db()
        return {"success": True, "message": "Base de données effacée et réinitialisée."}
    except Exception as e:
        # Surface filesystem/DB failures as a 500 with context
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'effacement de la base : {e}")
