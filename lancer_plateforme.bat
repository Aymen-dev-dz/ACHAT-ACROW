@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"

echo ======================================================================
echo   ACROW DZ - PROCUREMENT SCRAPER (BY AYMEN) - SOURCING ACHATS
echo ======================================================================
echo.
echo   Demarrage du serveur local sur http://127.0.0.1:5050 ...
echo   Votre navigateur Google Chrome va s'ouvrir automatiquement !
echo.
echo   MODE VISUEL :
echo   Lorsque vous cliquerez sur "Lancer le Sourcing Fournisseurs",
echo   une deuxieme fenetre Google Chrome s'ouvrira en grand sur votre
echo   ecran pour vous montrer le scraping Google Maps en direct !
echo.
echo   Pour arreter le serveur : fermez cette fenetre noire ou Ctrl+C
echo ======================================================================
echo.

python app.py

if errorlevel 1 (
    echo.
    echo Une erreur s'est produite lors de l'execution.
    echo Appuyez sur une touche pour quitter.
    pause > nul
)
