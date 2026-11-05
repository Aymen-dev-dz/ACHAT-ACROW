# Dockerfile pour ACROW DZ — Procurement Scraper (by Aymen)
# Image officielle Playwright Python avec Chromium & dépendances Linux préinstallées
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Répertoire de travail dans le conteneur
WORKDIR /app

# Variables d'environnement de production
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PORT=8080 \
    DEBIAN_FRONTEND=noninteractive

# Copie et installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# S'assurer que le navigateur Chromium Playwright est installé
RUN playwright install chromium

# Copie de tout le code du projet
COPY . .

# Port d'écoute standard pour Render / Railway / Cloud Run
EXPOSE 8080

# Démarrage avec Gunicorn (s'adapte automatiquement à la variable $PORT de Render)
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 300"]
