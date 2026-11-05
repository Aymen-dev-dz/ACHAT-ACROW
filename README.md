# ACROW DZ — Procurement Scraper (by Aymen)

Une plateforme professionnelle d'intelligence achats et de sourcing fournisseurs Google Maps dédiée à **ACROW Algérie** :
1. **Une Plateforme & Interface Web moderne (ACROW DZ — Procurement Scraper by Aymen)** avec suivi en temps réel, filtres et exports.
2. **Un Script Python CLI & Playwright** automatisant la navigation Chrome et l'extraction de fiches de fournisseurs et sous-traitants.

---

## 🚀 Lancement Rapide de l'Interface Web (ACROW DZ — Procurement Scraper)

### Méthode 1 : Double-clic (Windows)
Double-cliquez simplement sur le fichier :
```
lancer_plateforme.bat
```
L'interface s'ouvrira automatiquement dans votre navigateur par défaut à l'adresse **http://127.0.0.1:5050**.

### Méthode 2 : Ligne de commande
```bash
pip install -r requirements.txt
python app.py
```
Puis accédez à `http://127.0.0.1:5050`.

---

## ✨ Fonctionnalités de la Plateforme Web

- **🎯 Studio de Scraping Interactif** :
  - Saisie de la requête (ex: *agences immobilières Alger*, *restaurants Paris*).
  - Choix du nombre de fiches cibles avec curseur dynamique (5, 10, 25, 50, 100+).
  - Bascule entre **Mode Visuel** (Chrome visible à l'écran) et **Mode Arrière-plan (Headless)**.
  - Vitesse réglable (Slow-Mo de 0ms à 1000ms pour imiter une navigation humaine).
  - Enregistrement vidéo MP4 et captures d'écran PNG à la demande.
  - Bouton d'arrêt d'urgence sécurisé en un clic.

- **⚡ Moniteur Temps Réel & Console Live** :
  - Streaming Server-Sent Events (SSE) : pourcentage d'avancement et statut en direct.
  - Nom de la dernière entreprise extraite affiché instantanément.
  - Console de logs intégrée avec autoscroll et bouton de copie des logs.

- **📊 Explorateur de Leads & Contacts** :
  - Tableau interactif avec tri par colonne (Nom, Note, Avis, Catégorie).
  - Badges pour téléphones cliquables (`tel:...`) avec copie 1-clic.
  - Liens directs vers les sites web et fiches Google Maps.
  - KPI analytiques : Taux de présence téléphonique, présence web, note moyenne globale.
  - Filtres rapides : *Tous*, *Avec Téléphone*, *Avec Site Web*, *Note ≥ 4.0*.
  - **Bouton Copier Téléphones** : Récupère tous les numéros au format propre pour vos campagnes WhatsApp / SMS / CRM.

- **📥 Exports Multi-Formats** :
  - **Excel (.xlsx)** auto-formaté avec colonnes ajustées.
  - **CSV (UTF-8 avec BOM)** compatible Excel sans problème d'accents.
  - **JSON** pour développeurs et intégrations API.

- **📁 Gestionnaire de Fichiers & Galerie Média** :
  - Historique complet de tous les scrapings passés.
  - Lecteur vidéo intégré pour revoir les démonstrations de scraping (`demonstration_scraper.mp4`).
  - Galerie de captures d'écran PNG.

---

## Table of Contents
- [Lancement Rapide de l'Interface Web](#-lancement-rapide-de-linterface-web-mapsscraper-studio)
- [Fonctionnalités de la Plateforme Web](#-fonctionnalités-de-la-plateforme-web)
- [Prerequisites](#prerequisites)
- [Multiple Branches](#multiple-branches)
- [Key Features](#key-features)
- [Installation](#installation)
- [Usage (CLI)](#usage)
- [Example](#example)
- [Notes](#notes)
- [Video Example](#video-example)

## Prerequisites
- Python 3.8 or 3.9 (Python 3.10+ may not be compatible with some dependencies)
- Google Chrome or Chromium browser installed (for Playwright)

## Multiple Branches
The repo currently has 3 branches
- Main
- Latest Libraries (The one that works with latest libraries, can cause issues. Prefer Main)
- Linux ( Linux Support if main branch does not work correctly)


## Key Features
- Data Scraping: The script scrapes data from Google Maps listings, extracting valuable information about businesses, such as their name, address, website, and contact details.

- Review Analysis: It extracts review counts and average ratings, providing insights into businesses' online reputation.

- Business Type Detection: The script identifies whether a business offers in-store shopping, in-store pickup, or delivery services.

- Operating Hours: It extracts information about the business's operating hours.

- Introduction Extraction: The script also scrapes introductory information about the businesses when available.

- Data Cleansing: It cleanses and organizes the scraped data, removing redundant or unnecessary columns.

- CSV Export: The cleaned data is exported to a CSV file for further analysis or integration with other tools.

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/zohaibbashir/Google-Maps-Scrapper.git
   cd google-maps-scraper
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```bash
   playwright install
   ```

## Usage

Run the script with your desired search term and number of results:

```bash
python main.py -s "Turkish Restaurants in Toronto Canada" -t 20
```

- `-s` or `--search`: Search query for Google Maps (default: "turkish stores in toronto Canada")
- `-t` or `--total`: Number of results to scrape (default: 1)
- `-o` or `--output`: Output CSV file path (default: result.csv)
- `--append`: Append results to the output file instead of overwriting (default: off)

## Example

Append new results to an existing CSV file:
```bash
python main.py -s "Turkish Restaurants in Toronto Canada" -t 20 -o toronto_turkish_restaurants.csv --append
```

The script will launch a browser, perform the search, and start scraping information. Progress will be displayed in the terminal, and results will be saved to the specified CSV file. If `--append` is used, new results will be added to the end of the file without removing previous data.

## Notes
- The script opens a visible browser window (not headless) for scraping.
- Google Maps DOM may change, which can break the script. If you encounter issues, update the XPaths in `main.py`.
- Avoid running too many scrapes in a short period to prevent being blocked by Google.

## Video Example

https://www.linkedin.com/posts/zohaibbashir_python-data-webscraping-activity-7093920891411062784-flEQ

## License
MIT
