### FICHIER MIGRÉ. Voir app/api/env.py
import os
from fastapi import APIRouter, Body
from dotenv import dotenv_values, set_key

router = APIRouter()

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
    if not os.path.exists(env_path):
        # Si .env n'existe pas, on tente de copier .env.example ou créer un fichier vide
        example_path = os.path.join(os.path.dirname(__file__), '../../.env.example')
        if os.path.exists(example_path):
            import shutil
            shutil.copy(example_path, env_path)
        else:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write('')
    for key, value in updates.items():
        set_key(env_path, key, str(value))
    return {"success": True, "updated": list(updates.keys())}
