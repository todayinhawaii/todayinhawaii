"""
VisitorPulse Hawaii — Backend Server
=====================================
A tiny Flask web server that:
1. Serves the website (index.html)
2. Exposes /api/today and /api/history endpoints
   so the frontend can fetch real data from hawaii_data.csv
3. Runs the daily fetch automatically at 8am

Deploy this to Railway — it handles everything.
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import csv
import os
from datetime import datetime, date, timedelta
from collections import defaultdict
import threading
import schedule
import time

# Import our data fetcher
import sys
sys.path.insert(0, os.path.dirname(__file__))
try:
    from fetch_hawaii_data import main as fetch_data
except ImportError:
    fetch_data = None

app = Flask(__name__, static_folder=".")
CORS(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), "hawaii_data.csv")


# ── DATA LOADING ──────────────────────────────────────────────

def load_csv() -> list[dict]:
    """Load all records from hawaii_data.csv."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_int(val):
    """Safe integer conversion."""
    try:
        return int(val) if val and val.strip() else None
    except (ValueError, AttributeError):
        return None


# ── API ROUTES ────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main website."""
    return send_from_directory(".", "index.html")


@app.route("/api/today")
def api_today():
    """
    Returns today's data for all islands.
    Falls back to most recent available day if today isn't in yet.
    """
    records = load_csv()
    if not records:
        return jsonify({"error": "No data yet. Run fetch_hawaii_data.py first."}), 404

    # Find the most recent date in the data
    dates = sorted(set(r["data_date"] for r in records if r["data_date"]), reverse=True)
    latest_date = dates[0] if dates else None

    if not latest_date:
        return jsonify({"error": "No valid dates in data"}), 404

    # Get records for the latest date (excluding statewide summary)
    latest = [r for r in records
              if r["data_date"] == latest_date and r["island"] != "Statewide"]

    # Also get previous day for % change
    prev_date = dates[1] if len(dates) > 1 else None
    prev = {r["island"]: r for r in records
            if r["data_date"] == prev_date} if prev_date else {}

    islands = {}
    for r in latest:
        island = r["island"]
        arr  = to_int(r.get("arrivals"))
        dep  = to_int(r.get("departures"))
        dom  = to_int(r.get("domestic"))
        intl = to_int(r.get("international"))
        net  = to_int(r.get("net_flow")) or ((arr - dep) if arr and dep else None)

        prev_arr = to_int(prev.get(island, {}).get("arrivals"))
        change_pct = None
        if arr and prev_arr and prev_arr > 0:
            change_pct = round((arr - prev_arr) / prev_arr * 100, 1)

        islands[island] = {
            "arrivals":      arr,
            "departures":    dep,
            "net_flow":      net,
            "domestic":      dom,
            "international": intl,
            "change_pct":    change_pct,
            "on_island_est": round(arr * 8.9) if arr else None,
        }

    # Statewide totals
    total_arr = sum(v["arrivals"] or 0 for v in islands.values())
    total_dep = sum(v["departures"] or 0 for v in islands.values())

    return jsonify({
        "date":       latest_date,
        "updated_at": datetime.now().isoformat(),
        "statewide": {
            "arrivals":      total_arr,
            "departures":    total_dep,
            "net_flow":      total_arr - total_dep,
            "on_island_est": round(total_arr * 8.9),
        },
        "islands": islands,
    })


@app.route("/api/history")
@app.route("/api/history/<int:days>")
def api_history(days=30):
    """
    Returns daily arrival history for the last N days, per island.
    Used by the trend chart.
    """
    days = min(days, 365)   # Cap at 1 year
    records = load_csv()
    if not records:
        return jsonify({"error": "No data yet"}), 404

    # Collect all dates, sorted
    all_dates = sorted(set(
        r["data_date"] for r in records
        if r["data_date"] and r["island"] != "Statewide"
    ))
    recent_dates = all_dates[-days:] if len(all_dates) >= days else all_dates

    # Build per-island history
    by_island_date = defaultdict(dict)
    for r in records:
        if r["island"] != "Statewide":
            by_island_date[r["island"]][r["data_date"]] = to_int(r.get("arrivals"))

    history = {}
    for island in by_island_date:
        history[island] = [
            {
                "date": d,
                "arrivals": by_island_date[island].get(d),
            }
            for d in recent_dates
        ]

    return jsonify({
        "days": days,
        "dates": recent_dates,
        "islands": history,
    })


@app.route("/api/status")
def api_status():
    """Health check — useful for Railway to verify the server is running."""
    records = load_csv()
    dates   = sorted(set(r["data_date"] for r in records if r["data_date"]), reverse=True)
    return jsonify({
        "status":       "ok",
        "records":      len(records),
        "latest_date":  dates[0] if dates else None,
        "server_time":  datetime.now().isoformat(),
    })


# ── SCHEDULED DAILY FETCH ─────────────────────────────────────

def run_daily_fetch():
    """Runs the data fetch in a background thread."""
    if fetch_data:
        print(f"[{datetime.now()}] Running scheduled data fetch...")
        try:
            fetch_data()
            print(f"[{datetime.now()}] Fetch complete.")
        except Exception as e:
            print(f"[{datetime.now()}] Fetch error: {e}")
    else:
        print("Warning: fetch_hawaii_data.py not found — skipping scheduled fetch")


def schedule_loop():
    """Runs in a background thread to trigger daily fetch."""
    # Fetch at 8:30am Hawaii time (UTC-10 = 18:30 UTC)
    schedule.every().day.at("18:30").do(run_daily_fetch)
    # Also fetch on startup if no data yet
    if not os.path.exists(DATA_FILE):
        print("No data file found — running initial fetch...")
        run_daily_fetch()
    while True:
        schedule.run_pending()
        time.sleep(60)


# ── START SERVER ──────────────────────────────────────────────

if __name__ == "__main__":
    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=schedule_loop, daemon=True)
    scheduler_thread.start()

    # Start the web server
    port = int(os.environ.get("PORT", 5000))
    print(f"VisitorPulse Hawaii server starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
