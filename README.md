# 🛰️ OpenAtlas

Un outil complet conçu pour faciliter la veille informationnelle. Il automatise la collecte, la traduction, l'enrichissement et la visualisation cartographique d’événements issus de sources Telegram sélectionnées par l’utilisateur. 
Grâce à sa fonction de recherche avancée, il permet d’explorer rapidement et précisément la base de donnée.

[![Carte principale](static/img/screenA.png)](static/img/screenA.png)
[![Panneau latéral](static/img/screenB.png)](static/img/screenB.png)
[![Formulaire de rélage](static/img/screenC.png)](static/img/screenC.png)

## 🎯 Fonctionnalités principales

- **Collecte automatisée** de messages Telegram via API
- **Déduplication** des données
- **Traduction automatique** des messages (IA)
- **Enrichissement et normalisation** des pays, zones, types d'événements (IA)
- **Visualisation web** : dashboard interactif (fast api + leaflet)
- **Éditeur .env** intégré pour la configuration

---

## 💾 Installation rapide

-  **Cloner le repo**
   ```bash
   git clone https://github.com/Camprch/OpenAtlas
   cd openatlas
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

Projet 100% open source.
