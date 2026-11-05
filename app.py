import os
import sys

# Ensure UTF-8 stream output on Windows to prevent UnicodeEncodeError with cp1252
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import time
import signal
import queue
import logging
import threading
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional

import psutil
import pandas as pd
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    Response,
    send_file,
    send_from_directory,
    abort,
)

# Base directories
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = "google-maps-scraper-platform-secret-2026"
app.config["TEMPLATES_AUTO_RELOAD"] = True


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = Response()
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return res


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

# Global scraper manager state
def kill_process_tree(pid: int):
    """Forcefully and cleanly kills a process and all its child processes (including Chrome and Playwright)."""
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        parent.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            subprocess.call(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


class ScraperManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.process: Optional[subprocess.Popen] = None
        self.status: str = "idle"  # idle, running, completed, stopped, error
        self.search_query: str = ""
        self.total_target: int = 0
        self.current_count: int = 0
        self.current_name: str = ""
        self.current_step: str = "En attente d'une mission..."
        self.output_file: str = "result.csv"
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.logs_history: List[Dict[str, Any]] = []
        self.subscribers: List[queue.Queue] = []
        self.monitor_thread: Optional[threading.Thread] = None

    def broadcast(self, event_type: str, data: Dict[str, Any]):
        message = {
            "type": event_type,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "data": data,
        }
        with self.lock:
            # Keep last 1000 logs
            if event_type == "log":
                self.logs_history.append(message)
                if len(self.logs_history) > 1000:
                    self.logs_history.pop(0)

            # Broadcast to active SSE queues
            dead_subs = []
            for q in self.subscribers:
                try:
                    q.put_nowait(message)
                except Exception:
                    dead_subs.append(q)
            for dead in dead_subs:
                if dead in self.subscribers:
                    self.subscribers.remove(dead)

    def subscribe(self) -> queue.Queue:
        q = queue.Queue(maxsize=200)
        with self.lock:
            self.subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self.lock:
            if q in self.subscribers:
                self.subscribers.remove(q)

    def get_state(self) -> Dict[str, Any]:
        with self.lock:
            elapsed = 0
            if self.started_at:
                end_time = self.finished_at or time.time()
                elapsed = round(end_time - self.started_at, 1)

            percentage = 0
            if self.total_target > 0:
                percentage = min(100, int((self.current_count / self.total_target) * 100))

            return {
                "status": self.status,
                "search_query": self.search_query,
                "total_target": self.total_target,
                "current_count": self.current_count,
                "current_name": self.current_name,
                "current_step": self.current_step,
                "output_file": self.output_file,
                "percentage": percentage,
                "elapsed_seconds": elapsed,
                "is_running": self.status == "running",
            }

    def start_scrape(
        self,
        search_query: str,
        total: int,
        headless: bool,
        slow_mo: int,
        output_file: str,
        append: bool,
        screenshots: bool,
        record_video: bool,
    ) -> bool:
        with self.lock:
            if self.status == "running":
                return False

            self.status = "running"
            self.search_query = search_query.strip()
            self.total_target = max(1, int(total))
            self.current_count = 0
            self.current_name = ""
            self.current_step = "Initialisation du navigateur..."
            self.output_file = output_file.strip() or "result.csv"
            if not self.output_file.endswith(".csv"):
                self.output_file += ".csv"
            self.started_at = time.time()
            self.finished_at = None
            self.logs_history.clear()

        # Build command
        cmd = [
            sys.executable,
            os.path.join(BASE_DIR, "main.py"),
            "-s", self.search_query,
            "-t", str(self.total_target),
            "-o", self.output_file,
            "--slow-mo", str(slow_mo),
        ]
        if headless or (sys.platform != "win32" and not os.environ.get("DISPLAY")):
            cmd.append("--headless")
        if append:
            cmd.append("--append")
        if screenshots:
            cmd.append("--screenshots")
        if record_video:
            cmd.extend(["--record-video", "videos"])

        self.broadcast("status", self.get_state())
        self.broadcast("log", {"level": "info", "message": f"🚀 Démarrage du scraping: '{self.search_query}' (Cible: {self.total_target} fiches)"})
        self.broadcast("log", {"level": "info", "message": f"⚙️ Options: Mode={'Arrière-plan (Headless)' if headless else 'Visuel'}, Ralentissement={slow_mo}ms, Sortie='{self.output_file}'"})

        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

            proc = subprocess.Popen(
                cmd,
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
            with self.lock:
                self.process = proc
        except Exception as e:
            with self.lock:
                self.status = "error"
                self.finished_at = time.time()
                self.current_step = f"Erreur de démarrage: {str(e)}"
            self.broadcast("log", {"level": "error", "message": f"❌ Impossible de démarrer le processus: {str(e)}"})
            self.broadcast("status", self.get_state())
            return False

        def run_worker(p: subprocess.Popen):
            try:
                while True:
                    try:
                        line = p.stdout.readline()
                    except (ValueError, OSError, Exception):
                        break
                    if not line:
                        break
                    line = line.rstrip()
                    if not line:
                        continue
                    self._parse_log_line(line)
                    self.broadcast("log", {"level": "raw", "message": line})

                try:
                    p.stdout.close()
                except Exception:
                    pass
                return_code = p.wait()

                with self.lock:
                    self.finished_at = time.time()
                    if self.status == "stopped":
                        self.current_step = "Scraping interrompu par l'utilisateur."
                        self.broadcast("log", {"level": "warn", "message": "⏹️ Scraping arrêté avec succès."})
                    elif return_code == 0:
                        self.status = "completed"
                        self.current_step = f"Scraping terminé avec succès ({self.current_count} fiches extraites) !"
                        self.broadcast("log", {"level": "success", "message": f"✅ Scraping terminé avec succès ! Fichier sauvegardé: {self.output_file}"})
                    else:
                        self.status = "error"
                        self.current_step = f"Erreur d'exécution (code {return_code})"
                        self.broadcast("log", {"level": "error", "message": f"❌ Le processus s'est arrêté avec le code {return_code}"})

                self.broadcast("status", self.get_state())

            except Exception as e:
                with self.lock:
                    if self.status != "stopped":
                        self.status = "error"
                        self.finished_at = time.time()
                        self.current_step = f"Exception: {str(e)}"
                        self.broadcast("log", {"level": "error", "message": f"💥 Erreur critique: {str(e)}"})
                        self.broadcast("status", self.get_state())
            finally:
                with self.lock:
                    if self.process == p:
                        self.process = None

        self.monitor_thread = threading.Thread(target=run_worker, args=(proc,), daemon=True)
        self.monitor_thread.start()
        return True

    def _parse_log_line(self, line: str):
        should_broadcast = False
        with self.lock:
            # Check for listings scrolling count
            if "Currently Found:" in line:
                try:
                    count = int(line.split("Currently Found:")[-1].strip())
                    self.current_step = f"Recherche Google Maps en cours... ({count} résultats repérés)"
                    should_broadcast = True
                except Exception:
                    pass

            elif "Total Found:" in line:
                try:
                    total_found = int(line.split("Total Found:")[-1].strip())
                    self.current_step = f"{total_found} résultats sélectionnés, extraction des détails..."
                    should_broadcast = True
                except Exception:
                    pass

            elif "EXTRACTED [" in line:
                # Example: EXTRACTED [3/10]: Agence Immobilière El Bahdja
                try:
                    parts = line.split("EXTRACTED [")[-1].split("]:")
                    fraction = parts[0].strip()
                    place_name = parts[1].strip() if len(parts) > 1 else ""
                    current_idx = int(fraction.split("/")[0])
                    self.current_count = current_idx
                    self.current_name = place_name
                    self.current_step = f"Extraction fiche {fraction} : {place_name}"
                    should_broadcast = True
                except Exception:
                    pass

            elif "Saved" in line and "places to" in line:
                self.current_step = line
                should_broadcast = True

        if should_broadcast:
            self.broadcast("status", self.get_state())

    def stop_scrape(self) -> bool:
        proc_to_kill = None
        with self.lock:
            self.status = "stopped"
            self.finished_at = time.time()
            self.current_step = "Scraping interrompu par l'utilisateur."
            if self.process:
                proc_to_kill = self.process
                self.process = None

        self.broadcast("log", {"level": "warn", "message": "🛑 Arrêt immédiat demandé par l'utilisateur..."})
        self.broadcast("status", self.get_state())

        if proc_to_kill:
            try:
                # Kill process and all children FIRST so the pipe write-end closes and readline() exits naturally
                kill_process_tree(proc_to_kill.pid)
                try:
                    proc_to_kill.kill()
                except Exception:
                    pass
            except Exception as e:
                self.broadcast("log", {"level": "error", "message": f"Erreur lors de l'arrêt du processus: {e}"})

        return True


manager = ScraperManager()


# -------------------------------------------------------------
# HELPER FUNCTIONS FOR CSV/FILES
# -------------------------------------------------------------
def get_csv_files_info() -> List[Dict[str, Any]]:
    files_info = []
    for item in os.listdir(BASE_DIR):
        if item.lower().endswith(".csv") and os.path.isfile(os.path.join(BASE_DIR, item)):
            filepath = os.path.join(BASE_DIR, item)
            stat = os.stat(filepath)
            size_kb = round(stat.st_size / 1024, 1)
            size_str = f"{size_kb} KB" if size_kb < 1024 else f"{round(size_kb / 1024, 2)} MB"
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            # Quick row count
            row_count = 0
            try:
                with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
                    row_count = max(0, sum(1 for line in f if line.strip()) - 1)
            except Exception:
                pass

            files_info.append({
                "filename": item,
                "size_str": size_str,
                "size_bytes": stat.st_size,
                "modified": mtime,
                "mtime_raw": stat.st_mtime,
                "row_count": row_count,
            })

    # Sort most recent first
    files_info.sort(key=lambda x: x["mtime_raw"], reverse=True)
    return files_info


def read_csv_safe(filename: str) -> pd.DataFrame:
    filepath = os.path.join(BASE_DIR, os.path.basename(filename))
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Fichier non trouvé: {filename}")

    # Try encodings: utf-8-sig, utf-8, latin-1
    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
        try:
            df = pd.read_csv(filepath, encoding=enc)
            return df
        except UnicodeDecodeError:
            continue
    return pd.read_csv(filepath, encoding="utf-8-sig", errors="replace")


# -------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/scrape/start", methods=["POST"])
def api_start_scrape():
    data = request.get_json() or {}
    search_query = data.get("search", "").strip()
    total = int(data.get("total", 10))
    headless = bool(data.get("headless", False))
    slow_mo = int(data.get("slow_mo", 200))
    output_file = data.get("output_file", "").strip() or "result.csv"
    append = bool(data.get("append", False))
    screenshots = bool(data.get("screenshots", False))
    record_video = bool(data.get("record_video", False))

    if not search_query:
        return jsonify({"success": False, "error": "Veuillez saisir un terme de recherche (ex: 'Agences Alger')"}), 400

    started = manager.start_scrape(
        search_query=search_query,
        total=total,
        headless=headless,
        slow_mo=slow_mo,
        output_file=output_file,
        append=append,
        screenshots=screenshots,
        record_video=record_video,
    )
    if not started:
        return jsonify({"success": False, "error": "Un scraping est déjà en cours d'exécution."}), 409

    return jsonify({"success": True, "message": "Scraping lancé avec succès !", "state": manager.get_state()})


@app.route("/api/scrape/stop", methods=["POST"])
def api_stop_scrape():
    stopped = manager.stop_scrape()
    if not stopped:
        return jsonify({"success": False, "error": "Aucun scraping n'est actuellement en cours."}), 400
    return jsonify({"success": True, "message": "Arrêt du scraping demandé."})


@app.route("/api/scrape/status", methods=["GET"])
def api_get_status():
    return jsonify(manager.get_state())


@app.route("/api/scrape/stream")
def api_stream_logs():
    q = manager.subscribe()

    def event_stream():
        # First send current state and recent logs
        current_state = manager.get_state()
        yield f"data: {json.dumps({'type': 'init', 'state': current_state, 'logs': manager.logs_history[-50:]})}\n\n"

        while True:
            try:
                # Block for up to 15 seconds waiting for message
                msg = q.get(timeout=15.0)
                yield f"data: {json.dumps(msg)}\n\n"
            except queue.Empty:
                # Send ping comment to keep connection alive
                yield ": keepalive\n\n"
            except GeneratorExit:
                manager.unsubscribe(q)
                break
            except Exception:
                manager.unsubscribe(q)
                break

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/api/files", methods=["GET"])
def api_list_files():
    files = get_csv_files_info()
    return jsonify({"success": True, "files": files})


@app.route("/api/files/<filename>", methods=["GET"])
def api_get_file_data(filename: str):
    filename = os.path.basename(filename)
    try:
        df = read_csv_safe(filename)
        # Clean nulls
        df = df.fillna("")

        # Calculate rich stats
        total_rows = len(df)
        with_phone = 0
        with_website = 0
        avg_rating = 0.0

        if "phone_number" in df.columns:
            with_phone = int((df["phone_number"].astype(str).str.strip() != "").sum())
        if "website" in df.columns:
            with_website = int((df["website"].astype(str).str.strip() != "").sum())
        if "reviews_average" in df.columns:
            ratings = pd.to_numeric(df["reviews_average"], errors="coerce").dropna()
            if not ratings.empty:
                avg_rating = round(float(ratings.mean()), 2)

        records = df.to_dict(orient="records")
        columns = list(df.columns)

        return jsonify({
            "success": True,
            "filename": filename,
            "columns": columns,
            "rows": records,
            "stats": {
                "total": total_rows,
                "with_phone": with_phone,
                "with_website": with_website,
                "phone_percentage": round((with_phone / total_rows * 100), 1) if total_rows > 0 else 0,
                "website_percentage": round((with_website / total_rows * 100), 1) if total_rows > 0 else 0,
                "avg_rating": avg_rating,
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Erreur lors de la lecture du fichier: {str(e)}"}), 500


@app.route("/api/files/<filename>", methods=["DELETE"])
def api_delete_file(filename: str):
    filename = os.path.basename(filename)
    filepath = os.path.join(BASE_DIR, filename)
    if not os.path.isfile(filepath):
        return jsonify({"success": False, "error": "Fichier introuvable."}), 404
    try:
        os.remove(filepath)
        return jsonify({"success": True, "message": f"Fichier {filename} supprimé avec succès."})
    except Exception as e:
        return jsonify({"success": False, "error": f"Impossible de supprimer le fichier: {str(e)}"}), 500


@app.route("/api/export/<filename>/<fmt>", methods=["GET"])
def api_export_file(filename: str, fmt: str):
    filename = os.path.basename(filename)
    filepath = os.path.join(BASE_DIR, filename)
    if not os.path.isfile(filepath):
        abort(404)

    df = read_csv_safe(filename)

    if fmt == "csv":
        return send_file(
            filepath,
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )

    elif fmt == "xlsx":
        excel_path = os.path.join(BASE_DIR, f"{os.path.splitext(filename)[0]}.xlsx")
        try:
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Leads Google Maps")
                # Auto-adjust column width
                worksheet = writer.sheets["Leads Google Maps"]
                for col in worksheet.columns:
                    max_len = max(len(str(cell.value or "")) for cell in col)
                    col_letter = col[0].column_letter
                    worksheet.column_dimensions[col_letter].width = min(50, max(max_len + 3, 12))

            return send_file(
                excel_path,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=os.path.basename(excel_path),
            )
        except Exception as e:
            return jsonify({"success": False, "error": f"Erreur export Excel: {str(e)}"}), 500

    elif fmt == "json":
        json_data = df.to_json(orient="records", indent=2, force_ascii=False)
        return Response(
            json_data,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename={os.path.splitext(filename)[0]}.json"},
        )

    return jsonify({"success": False, "error": "Format non supporté."}), 400


@app.route("/api/media", methods=["GET"])
def api_list_media():
    screenshots = []
    if os.path.isdir(SCREENSHOTS_DIR):
        for f in os.listdir(SCREENSHOTS_DIR):
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                stat = os.stat(os.path.join(SCREENSHOTS_DIR, f))
                screenshots.append({
                    "name": f,
                    "url": f"/media/screenshots/{f}",
                    "size_kb": round(stat.st_size / 1024, 1),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })

    videos = []
    # Check videos folder and root for demo mp4
    search_dirs = [("videos", VIDEOS_DIR), ("", BASE_DIR)]
    seen_videos = set()
    for sub, vdir in search_dirs:
        if os.path.isdir(vdir):
            for f in os.listdir(vdir):
                if f.lower().endswith((".mp4", ".webm", ".mkv")):
                    if f in seen_videos:
                        continue
                    seen_videos.add(f)
                    stat = os.stat(os.path.join(vdir, f))
                    url_path = f"/media/videos/{f}" if sub == "videos" else f"/media/root/{f}"
                    videos.append({
                        "name": f,
                        "url": url_path,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    })

    return jsonify({
        "screenshots": screenshots,
        "videos": videos,
    })


@app.route("/media/<category>/<filename>")
def serve_media(category: str, filename: str):
    filename = os.path.basename(filename)
    if category == "screenshots":
        return send_from_directory(SCREENSHOTS_DIR, filename)
    elif category == "videos":
        return send_from_directory(VIDEOS_DIR, filename)
    elif category == "root":
        return send_from_directory(BASE_DIR, filename)
    abort(404)


def find_available_port(preferred_ports=(5050, 8080, 8000, 5500, 7860)) -> int:
    import socket
    for p in preferred_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    for p in range(5051, 5100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return 5050


def open_browser_delayed(url: str):
    import webbrowser
    time.sleep(1.2)
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    env_port = os.environ.get("PORT")
    port = int(env_port) if env_port else find_available_port()
    url = f"http://127.0.0.1:{port}"
    print("=" * 70)
    print(" [ACROW DZ — PROCUREMENT SCRAPER (BY AYMEN)] Plateforme Achats active !")
    print(f" -> Ouvrez votre navigateur sur : {url}")
    print("=" * 70)

    # Automatically open default browser once started
    threading.Thread(target=open_browser_delayed, args=(url,), daemon=True).start()

    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
