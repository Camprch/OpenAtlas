import os
from fastapi import APIRouter, Body
from dotenv import dotenv_values, set_key

# Router for reading/updating .env values
router = APIRouter()

@router.get("/env")
def get_env_vars():
    """
    Return variables from .env or .env.example as a dict.
    """
    # Prefer .env when present, otherwise fall back to .env.example
    env_path = os.path.join(os.path.dirname(__file__), '../../.env')
    example_path = os.path.join(os.path.dirname(__file__), '../../.env.example')
    if os.path.exists(env_path):
        return dotenv_values(env_path)
    elif os.path.exists(example_path):
        return dotenv_values(example_path)
    else:
        return {}

@router.post("/env")
def update_env_vars(
    updates: dict = Body(..., example={"OPENAI_API_KEY": "nouvelle_valeur"})
):
    """
    Update one or more variables in .env.
    """
    env_path = os.path.join(os.path.dirname(__file__), '../../.env')
    if not os.path.exists(env_path):
        # If .env is missing, copy from .env.example or create an empty file
        example_path = os.path.join(os.path.dirname(__file__), '../../.env.example')
        if os.path.exists(example_path):
            import shutil
            shutil.copy(example_path, env_path)
        else:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write('')
    # Apply updates atomically per key
    for key, value in updates.items():
        set_key(env_path, key, str(value))
    return {"success": True, "updated": list(updates.keys())}
