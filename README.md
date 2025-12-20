# OSINT Dashboard

Tableau de bord interactif pour l'analyse et la visualisation d'événements issus de sources ouvertes (OSINT), avec extraction automatisée depuis Telegram et enrichissement des données.

---

## Fonctionnalités principales

- **Collecte automatisée** de messages Telegram via API
- **Extraction et normalisation** des pays, types d'événements, labels, etc.
- **Traduction automatique** des messages (OpenAI)
- **Déduplication** et enrichissement des données
- **Visualisation web** : dashboard interactif (FastAPI + Jinja2 + JS)
- **Éditeur .env** intégré pour la configuration

---

## Installation rapide

1. **Cloner le repo**
   ```bash
   git clone <url-du-repo>
   cd map-intel
   ```
2. **Installer les dépendances**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Configurer les variables d'environnement**
   - Copier `.env.example` en `.env` et remplir les clés nécessaires (OpenAI, Telegram...)

4. **Initialiser la base de données** (optionnel, sinon auto à l'exécution)
   ```bash
   python -c 'from app.database import init_db; init_db()'
   ```

---

## Lancer l'application

```bash
uvicorn app.main:app --reload
```

- Accès au dashboard : [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- Accès à l'éditeur .env : [http://localhost:8000/env-editor](http://localhost:8000/env-editor)

---

## Pipeline de collecte

Pour lancer le pipeline d'extraction, traduction et enrichissement :
```bash
python tools/run_pipeline.py
```

---

## Structure du projet

- `app/` : code principal (API, modèles, services, utils)
- `static/` : fichiers statiques (JS, CSS, images)
- `templates/` : templates HTML (Jinja2)
- `data/` : base SQLite et données
- `tools/` : scripts utilitaires (pipeline, export, etc.)

---

## Dépendances principales
- FastAPI, SQLModel, SQLAlchemy, Jinja2
- Telethon (Telegram), OpenAI, python-dotenv
- Uvicorn (serveur dev)

---

## Auteur

- Projet développé par cam

---

## Licence

MIT
