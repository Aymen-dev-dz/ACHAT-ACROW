"""
Script de préparation des fichiers statiques pour le déploiement Netlify.
Copie templates/index.html et static/ dans public/
"""
import os
import shutil

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(PUBLIC_DIR, exist_ok=True)

# Copier index.html
src_index = os.path.join(TEMPLATES_DIR, "index.html")
dst_index = os.path.join(PUBLIC_DIR, "index.html")
if os.path.isfile(src_index):
    shutil.copy2(src_index, dst_index)
    print(f"OK: Copie {src_index} -> {dst_index}")

# Copier le dossier static
dst_static = os.path.join(PUBLIC_DIR, "static")
if os.path.isdir(STATIC_DIR):
    if os.path.exists(dst_static):
        shutil.rmtree(dst_static)
    shutil.copytree(STATIC_DIR, dst_static)
    print(f"OK: Copie {STATIC_DIR} -> {dst_static}")

print("Pret pour Netlify: dossier public/ genere avec succes.")
