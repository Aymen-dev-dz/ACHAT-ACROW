# Guide de Déploiement — ACROW DZ : Procurement Scraper (by Aymen)

Ce guide explique comment mettre en ligne votre plateforme pour votre équipe achats.

---

## ⚠️ Important : Comprendre l'Architecture (Netlify vs Serveur Python)

L'application est composée de deux parties :
1. **L'Interface Web Utilisateur (Frontend HTML/Tailwind/JS)** : Peut être hébergée partout, y compris sur **Netlify**.
2. **Le Moteur d'Extraction Google Maps (Playwright + Chrome + Python)** :
   - Netlify est une plateforme d'hébergement statique et de fonctions serverless (AWS Lambda). Les fonctions Netlify ont une limite de 10 à 26 secondes et ne peuvent pas exécuter un vrai navigateur Chrome complet.
   - Le scraping de Google Maps (navigation, défilement, extraction de 50 à 100 fiches) prend généralement de 30 secondes à 3 minutes.
   - **Pour que le scraping fonctionne en ligne**, le backend doit tourner sur un service qui supporte Python, Docker et Playwright (comme **Render.com**, **Railway.app** ou un **VPS**).

---

## Option 1 : Déploiement Complet Clé en Main (Gratuit sur Render.com) — *Recommandé*

Render permet d'héberger le **Frontend + le Backend + Chrome/Playwright** ensemble sur une URL publique gratuite (ex: `https://acrow-procurement-scraper.onrender.com`).

### Étapes :
1. Créez un compte gratuit sur [Render.com](https://render.com).
2. Poussez votre projet sur votre compte **GitHub** (dépôt public ou privé).
3. Sur Render, cliquez sur **New +** > **Web Service**.
4. Connectez votre dépôt GitHub.
5. Render détectera automatiquement le fichier `Dockerfile` déjà configuré dans le projet.
6. Cliquez sur **Deploy Web Service** !
   - Render va construire le conteneur avec Chromium, Gunicorn et Flask.
   - Votre plateforme sera immédiatement accessible en ligne 24/7.

---

## Option 2 : Déploiement sur Netlify (Interface Frontend)

Si vous souhaitez héberger l'interface sur Netlify :

### Méthode A : Drag & Drop Direct (Sans Git)
1. Exécutez une fois en local :
   ```bash
   python build_static.py
   ```
   Cela génère le dossier `public/` contenant `index.html` et le logo ACROW.
2. Allez sur [Netlify.com](https://app.netlify.com/drop).
3. Glissez-déposez simplement le dossier **`public`** sur la page Netlify Drop.
4. Votre site est instantanément en ligne !

### Méthode B : Via GitHub & netlify.toml
1. Poussez le projet sur GitHub.
2. Sur Netlify, cliquez sur **Add new site** > **Import an existing project** > **GitHub**.
3. Netlify lira automatiquement le fichier `netlify.toml` :
   - **Publish directory** : `public`
   - **Build command** : `python build_static.py`
4. Cliquez sur **Deploy**.

> 💡 **Astuce Connexion API** :
> Une fois votre backend déployé sur Render (Option 1), décommentez la règle de redirection dans `netlify.toml` pour relier automatiquement votre frontend Netlify à votre serveur de scraping !

---

## Option 3 : Déploiement avec Docker (Sur votre propre VPS ou Serveur ACROW)

Si ACROW dispose d'un serveur Linux (Ubuntu, Debian, etc.) :
```bash
# 1. Cloner le projet
git clone <votre-repo-url>
cd Google-Maps-Scrapper-main

# 2. Lancer avec Docker Compose
docker-compose up -d --build
```
L'application sera accessible sur `http://IP_DE_VOTRE_SERVEUR:8080`.
