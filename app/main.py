# app/main.py
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from app.database import init_db
init_db()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import router as api_router

app = FastAPI(title="OSINT Dashboard (from scratch)")

BASE_DIR = Path(__file__).resolve().parent.parent

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(api_router, prefix="/api")



@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# Route pour l'éditeur .env
@app.get("/env-editor", response_class=HTMLResponse)
async def env_editor(request: Request):
    return templates.TemplateResponse("env_editor.html", {"request": request})
