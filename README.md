# 🛰️ OSINT Dashboard

Tableau de bord ergonomique pour la collecte, la traduction, l'enrichissement et la visualisation d'événements issus de sources Telegram.

[![Carte principale](static/img/screen1.png)](static/img/screen1.png)
[![Panneau latéral](static/img/screen2.png)](static/img/screen2.png)
[![Formulaire de rélage](static/img/screen3.png)](static/img/screen3.png)

## 🎯 Fonctionnalités principales

- **Collecte automatisée** de messages Telegram via API
- **Extraction et normalisation** des pays, types d'événements, labels, etc.
- **Traduction automatique** des messages (OpenAI)
- **Déduplication** et enrichissement des données
- **Visualisation web** : dashboard interactif (fast api + leaflet)
- **Éditeur .env** intégré pour la configuration

---

## 💾 Installation rapide

-  **Cloner le repo**
   ```bash
   git clone https://github.com/Camprch/map-intel
   cd map-intel
   ```
-  **Installer les dépendances**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

---

## 🚀 Lancer l'application

```bash
uvicorn app.main:app --reload
```

- Accès au dashboard : [http://localhost:8000/dashboard](http://localhost:8000/dashboard)

---

## 🏗️ Structure du projet

- `app/` : code principal (API, modèles, services, utils)
- `static/` : fichiers statiques (JS, CSS, images)
- `templates/` : templates HTML
- `data/` : base SQLite et données
- `tools/` : scripts utilitaires (pipeline, export, etc.)

---

## 📄 Licence

100% open source !
