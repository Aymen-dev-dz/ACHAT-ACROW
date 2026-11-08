@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"

echo ======================================================================
echo   ACROW DZ - PROCUREMENT SCRAPER (BY AYMEN) - SOURCING ACHATS
echo ======================================================================
echo.
echo   Demarrage de la plateforme sur http://127.0.0.1:5050 ...
echo   Ouverture automatique de Google Chrome dans quelques secondes...
echo.
echo   Pour arreter le serveur : fermez cette fenetre ou appuyez sur Ctrl+C
echo ======================================================================
echo.

python app.py

if errorlevel 1 (
    echo.
    echo Une erreur s'est produite lors de l'execution.
    echo Appuyez sur une touche pour quitter.
    pause > nul
)
