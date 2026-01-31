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

# FastAPI application entrypoint
app = FastAPI(title="OSINT Dashboard (from scratch)")

# Project root used for static and template directories
BASE_DIR = Path(__file__).resolve().parent.parent

# Serve static assets from /static
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Jinja templates for HTML pages
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Mount all API routes under /api
app.include_router(api_router, prefix="/api")



@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Render the main dashboard page
    return templates.TemplateResponse("dashboard.html", {"request": request})

# HTML view for editing .env configuration
@app.get("/env-editor", response_class=HTMLResponse)
async def env_editor(request: Request):
    # Render the environment editor page
    return templates.TemplateResponse("env_editor.html", {"request": request})
