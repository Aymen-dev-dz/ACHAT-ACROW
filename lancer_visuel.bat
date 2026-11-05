@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ========================================================
echo   Lancement du Scraper Google Maps en mode VISUEL
echo   Vous allez voir la fenetre Chrome s'ouvrir a l'ecran !
echo ========================================================
echo.
python main.py -s "agences immobilieres Alger" -t 5 --slow-mo 300 -o "resultats_alger.csv"
echo.
echo ========================================================
echo   Extraction terminee ! Resultats dans resultats_alger.csv
echo ========================================================
pause
