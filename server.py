"""
Today in Hawaii — Backend Server
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import csv
import os
import json
import hashlib
from datetime import datetime, date
from collections import defaultdict
import threading
import schedule
import time

import sys
sys.path.insert(0, os.path.dirname(__file__))
try:
    from fetch_hawaii_data import main as fetch_data
except ImportError:
    fetch_data = None

app = Flask(__name__, static_folder=".")
CORS(app)

DATA_FILE    = os.path.join(os.path.dirname(__file__), "hawaii_data.csv")
MANUAL_FILE  = os.path.join(os.path.dirname(__file__), "manual_data.json")
ORIGINS_FILE = os.path.join(os.path.dirname(__file__), "origins_data.json")

ADMIN_PASSWORD = "hawaii2026"


def load_csv():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_manual():
    if not os.path.exists(MANUAL_FILE):
        return None
    with open(MANUAL_FILE) as f:
        return json.load(f)

def load_origins():
    if not os.path.exists(ORIGINS_FILE):
        return None
    with open(ORIGINS_FILE) as f:
        return json.load(f)

def to_int(val):
    try:
        return int(val) if val and str(val).strip() else None
    except (ValueError, AttributeError):
        return None

def generate_stable_data(today):
    seed = int(hashlib.md5(today.isoformat().encode()).hexdigest()[:8], 16)
    dow = today.weekday()
    dow_mult = 1.08 if dow in (4, 5) else (1.05 if dow == 6 else (0.94 if dow == 0 else 1.0))
    month = today.month
    month_mult = 1.08 if month in (12, 1, 2, 3) else (1.05 if month in (6, 7, 8) else (0.92 if month in (9, 10) else 1.0))
    bases = {
        'Maui':       {'arr': 4200, 'dep': 3900, 'dom': 3700, 'intl': 500},
        'Oahu':       {'arr': 9400, 'dep': 8800, 'dom': 7200, 'intl': 2200},
        'Kauai':      {'arr': 1350, 'dep': 1280, 'dom': 1200, 'intl': 150},
        'Big Island': {'arr': 2100, 'dep': 1950, 'dom': 1800, 'intl': 300},
    }
    islands = {}
    for island, b in bases.items():
        island_seed = (seed + hash(island)) % 1000
        variation = (island_seed / 1000.0 - 0.5) * 0.16
        arr  = int(b['arr'] * dow_mult * month_mult * (1 + variation))
        dep  = int(b['dep'] * dow_mult * month_mult * (1 + variation * 0.9))
        dom  = int(b['dom'] * dow_mult * month_mult * (1 + variation))
        intl = int(b['intl'] * dow_mult * month_mult * (1 + variation * 0.7))
        islands[island] = {
            'arrivals': arr, 'departures': dep, 'net_flow': arr - dep,
            'domestic': dom, 'international': intl,
            'change_pct': round(variation * 10, 1), 'on_island_est': round(arr * 8.9)
        }
    return islands


@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/oahu")
def oahu():
    return send_from_directory(".", "oahu.html")

@app.route("/maui")
def maui():
    return send_from_directory(".", "maui.html")

@app.route("/kauai")
def kauai():
    return send_from_directory(".", "kauai.html")

@app.route("/bigisland")
def bigisland():
    return send_from_directory(".", "bigisland.html")

@app.route("/privacy")
def privacy():
    return send_from_directory(".", "privacy.html")

@app.route("/about")
def about():
    return send_from_directory(".", "about.html")

@app.route("/admin")
def admin():
    return send_from_directory(".", "admin.html")

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(".", "sitemap.xml")

@app.route("/robots.txt")
def robots():
    return send_from_directory(".", "robots.txt")


@app.route("/api/today")
def api_today():
    today = date.today()
    manual = load_manual()
    if manual and manual.get('date'):
        islands = manual.get('islands', {})
        total_arr = sum(v.get('arrivals', 0) for v in islands.values())
        total_dep = sum(v.get('departures', 0) for v in islands.values())
        return jsonify({
            "date": manual['date'], "source": "manual",
            "updated_at": manual.get('updated_at', ''),
            "statewide": {"arrivals": total_arr, "departures": total_dep,
                          "net_flow": total_arr - total_dep, "on_island_est": round(total_arr * 8.9)},
            "islands": islands,
        })

    records = load_csv()
    if records:
        dates = sorted(set(r["data_date"] for r in records if r["data_date"]), reverse=True)
        if dates:
            latest_date = dates[0]
            latest = [r for r in records if r["data_date"] == latest_date and r["island"] != "Statewide"]
            prev_date = dates[1] if len(dates) > 1 else None
            prev = {r["island"]: r for r in records if r["data_date"] == prev_date} if prev_date else {}
            islands = {}
            for r in latest:
                island = r["island"]
                arr = to_int(r.get("arrivals"))
                dep = to_int(r.get("departures"))
                dom = to_int(r.get("domestic"))
                intl = to_int(r.get("international"))
                net = (arr - dep) if arr and dep else None
                prev_arr = to_int(prev.get(island, {}).get("arrivals"))
                change_pct = round((arr - prev_arr) / prev_arr * 100, 1) if arr and prev_arr else None
                islands[island] = {"arrivals": arr, "departures": dep, "net_flow": net,
                                   "domestic": dom, "international": intl,
                                   "change_pct": change_pct, "on_island_est": round(arr * 8.9) if arr else None}
            total_arr = sum((v["arrivals"] or 0) for v in islands.values())
            total_dep = sum((v["departures"] or 0) for v in islands.values())
            return jsonify({"date": latest_date, "source": "csv", "updated_at": datetime.now().isoformat(),
                            "statewide": {"arrivals": total_arr, "departures": total_dep,
                                          "net_flow": total_arr - total_dep, "on_island_est": round(total_arr * 8.9)},
                            "islands": islands})

    islands = generate_stable_data(today)
    total_arr = sum(v['arrivals'] for v in islands.values())
    total_dep = sum(v['departures'] for v in islands.values())
    return jsonify({"date": today.isoformat(), "source": "estimate", "updated_at": datetime.now().isoformat(),
                    "statewide": {"arrivals": total_arr, "departures": total_dep,
                                  "net_flow": total_arr - total_dep, "on_island_est": round(total_arr * 8.9)},
                    "islands": islands})


@app.route("/api/origins")
def api_origins():
    origins = load_origins()
    if origins:
        return jsonify(origins)
    return jsonify({"error": "No origins data"}), 404


@app.route("/api/status")
def api_status():
    records = load_csv()
    dates = sorted(set(r["data_date"] for r in records if r["data_date"]), reverse=True)
    manual = load_manual()
    return jsonify({"status": "ok", "records": len(records),
                    "latest_date": dates[0] if dates else None,
                    "manual_date": manual.get('date') if manual else None,
                    "server_time": datetime.now().isoformat()})


@app.route("/api/fetch-now")
def fetch_now():
    t = threading.Thread(target=run_daily_fetch, daemon=True)
    t.start()
    return jsonify({"status": "fetch started", "time": datetime.now().isoformat()})


@app.route("/api/admin/save-daily", methods=["POST"])
def admin_save_daily():
    data = request.get_json()
    if not data or data.get('password') != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    manual = {"date": date.today().isoformat(), "updated_at": datetime.now().isoformat(),
              "islands": data.get('islands', {})}
    with open(MANUAL_FILE, 'w') as f:
        json.dump(manual, f, indent=2)
    return jsonify({"status": "saved", "date": manual['date']})


@app.route("/api/admin/save-origins", methods=["POST"])
def admin_save_origins():
    data = request.get_json()
    if not data or data.get('password') != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    origins = data.get('origins', {})
    origins['updated_at'] = datetime.now().isoformat()
    with open(ORIGINS_FILE, 'w') as f:
        json.dump(origins, f, indent=2)
    return jsonify({"status": "saved"})


@app.route("/api/admin/clear-daily", methods=["POST"])
def admin_clear_daily():
    data = request.get_json()
    if not data or data.get('password') != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    if os.path.exists(MANUAL_FILE):
        os.remove(MANUAL_FILE)
    return jsonify({"status": "cleared"})


def run_daily_fetch():
    if fetch_data:
        print(f"[{datetime.now()}] Running fetch...")
        try:
            fetch_data()
            print(f"[{datetime.now()}] Fetch complete.")
        except Exception as e:
            print(f"[{datetime.now()}] Fetch error: {e}")

def schedule_loop():
    schedule.every().day.at("18:30").do(run_daily_fetch)
    if not os.path.exists(DATA_FILE):
        run_daily_fetch()
    while True:
        schedule.run_pending()
        time.sleep(30)

_scheduler_started = False
_scheduler_lock = threading.Lock()

def start_scheduler():
    global _scheduler_started
    with _scheduler_lock:
        if not _scheduler_started:
            _scheduler_started = True
            threading.Thread(target=schedule_loop, daemon=True).start()

start_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
