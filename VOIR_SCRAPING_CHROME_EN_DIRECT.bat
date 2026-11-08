@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"

cls
echo ======================================================================
echo    ACROW DZ - DEMONSTRATION SCRAPING VISUEL GOOGLE CHROME (5 ETOILES)
echo ======================================================================
echo.
echo   Ce script ouvre Google Chrome EN GRAND sur votre ecran pour que vous
echo   puissiez voir le scraping Google Maps travailler en direct !
echo.
echo ======================================================================
echo.

set /p SEARCH="Entrez votre recherche [Defaut: quincaillerie algerie]: "
if "%SEARCH%"=="" set SEARCH=quincaillerie algerie

set /p TOTAL="Nombre de fournisseurs 5 ETOILES a trouver [Defaut: 5]: "
if "%TOTAL%"=="" set TOTAL=5

echo.
echo ----------------------------------------------------------------------
echo  Lancement de Google Chrome en mode VISUEL...
echo  Recherche    : "%SEARCH%"
echo  Cible        : %TOTAL% fournisseurs
echo  Filtre       : 5.0 ETOILES UNIQUEMENT
echo  Vitesse      : Ralenti (Slow-Mo) pour bien voir chaque action
echo ----------------------------------------------------------------------
echo.

python main.py -s "%SEARCH%" -t %TOTAL% --min-rating 5.0 --slow-mo 600 -o resultats_visuel_5etoiles.csv

echo.
echo ======================================================================
echo   SCRAPING TERMINE AVEC SUCCES !
echo   Les resultats 5 etoiles sont enregistres dans :
echo   resultats_visuel_5etoiles.csv
echo ======================================================================
echo.
echo   Ouverture automatique du fichier CSV des resultats...
start "" "resultats_visuel_5etoiles.csv"
echo.
pause
