"""
Hawaii Tourist Tracker — Daily Data Fetcher
============================================
Pulls daily passenger count data from Hawaii's DBEDT Tableau Public dashboard
and saves it to a local CSV (hawaii_data.csv).

Run once a day via cron or Task Scheduler. Appends new data so you build
a growing historical record over time.

Data source: https://dbedt.hawaii.gov/economic/daily-passenger-counts/
Tableau workbook: Dashboard_DailyPax (public.tableau.com)
"""

import requests
import csv
import os
import re
import json
import time
from datetime import datetime, date

# ---------------------------------------------------------------------------
# CONFIGURATION — edit these if needed
# ---------------------------------------------------------------------------
OUTPUT_CSV = "hawaii_data.csv"
LOG_FILE   = "fetch_log.txt"

TABLEAU_BASE = "https://public.tableau.com"
WORKBOOK     = "Dashboard_DailyPax"

# Sheet names inside the DBEDT workbook → friendly island label
SHEETS = {
    "Total Pax":     "Statewide",
    "Oahu":          "Oahu",
    "Maui":          "Maui",
    "HawaiiIsland":  "Big Island",
    "Kauai":         "Kauai",
}

# ---------------------------------------------------------------------------
# TABLEAU DATA PULL
# ---------------------------------------------------------------------------
# Tableau Public exposes CSV downloads via a simple URL trick:
#   https://public.tableau.com/views/{Workbook}/{SheetName}.csv
# This returns the summary (aggregated) data for that sheet as a CSV file.
# No API key or login needed — it's a public dashboard.
# ---------------------------------------------------------------------------

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (HawaiiTouristTracker/1.0)",
    "Accept": "text/html,application/xhtml+xml,*/*",
})

def fetch_sheet(sheet_name: str, island_label: str) -> list[dict]:
    """Download one sheet from Tableau Public as CSV rows."""
    url = f"{TABLEAU_BASE}/views/{WORKBOOK}/{sheet_name}.csv"

    try:
        resp = SESSION.get(url, timeout=30)
        resp.raise_for_status()
        lines = resp.text.splitlines()
        if not lines:
            return []
        reader = csv.DictReader(lines)
        rows = list(reader)
        print(f"  ✓ {island_label}: {len(rows)} rows")
        return rows
    except requests.HTTPError as e:
        print(f"  ✗ {island_label}: HTTP {e.response.status_code}")
        return []
    except requests.RequestException as e:
        print(f"  ✗ {island_label}: {e}")
        return []


# ---------------------------------------------------------------------------
# DATA NORMALIZATION
# ---------------------------------------------------------------------------

def clean_int(val: str) -> int | None:
    """Parse a number string — handles commas, blanks, floats."""
    if not val or val.strip() in ("", "null", "NULL"):
        return None
    try:
        return int(val.replace(",", "").strip())
    except ValueError:
        try:
            return int(float(val.replace(",", "").strip()))
        except ValueError:
            return None


def find_col(row: dict, *candidates: str) -> str:
    """Case-insensitive column lookup with fallback candidates."""
    for name in candidates:
        for k, v in row.items():
            if k.strip().lower() == name.lower():
                return v
    return ""


def normalize(raw: dict, island: str, fetch_date: date) -> dict:
    """Map a raw Tableau row to our standard schema."""
    data_date  = find_col(raw, "Date", "date", "Day", "Report Date", "DAY(Date)")
    arrivals   = find_col(raw, "Arrivals", "In", "Inbound", "SUM(Arrivals)", "Passengers In", "Total Arrivals")
    departures = find_col(raw, "Departures", "Out", "Outbound", "SUM(Departures)", "Passengers Out", "Total Departures")
    domestic   = find_col(raw, "Domestic", "Dom", "SUM(Domestic)")
    intl       = find_col(raw, "International", "Intl", "Intl.", "SUM(International)")

    arr = clean_int(arrivals)
    dep = clean_int(departures)

    return {
        "fetch_date":    fetch_date.isoformat(),
        "data_date":     data_date.strip() if data_date else fetch_date.isoformat(),
        "island":        island,
        "arrivals":      arr,
        "departures":    dep,
        "net_flow":      (arr - dep) if (arr is not None and dep is not None) else None,
        "domestic":      clean_int(domestic),
        "international": clean_int(intl),
    }


# ---------------------------------------------------------------------------
# CSV STORAGE
# ---------------------------------------------------------------------------

FIELDS = ["fetch_date", "data_date", "island",
          "arrivals", "departures", "net_flow",
          "domestic", "international"]


def already_saved() -> set[tuple]:
    """Return (data_date, island) pairs already in the CSV."""
    if not os.path.exists(OUTPUT_CSV):
        return set()
    with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
        return {(r["data_date"], r["island"]) for r in csv.DictReader(f)}


def save(records: list[dict]) -> int:
    """Append new records, skip duplicates. Returns number saved."""
    existing = already_saved()
    new = [r for r in records
           if (r["data_date"], r["island"]) not in existing]
    if not new:
        return 0
    write_header = not os.path.exists(OUTPUT_CSV)
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        w.writerows(new)
    return len(new)


# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

def log(msg: str):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    log("Hawaii Tourist Tracker — fetch starting")
    today   = date.today()
    records = []

    for sheet, island in SHEETS.items():
        rows = fetch_sheet(sheet, island)
        for raw in rows:
            records.append(normalize(raw, island, today))
        time.sleep(1.5)     # Polite delay between requests

    if not records:
        log("ERROR: No data fetched. Check internet connection or Tableau URL.")
        return

    added = save(records)
    log(f"Fetched {len(records)} rows → {added} new records saved to {OUTPUT_CSV}")
    if added == 0:
        log("(All were duplicates — data may not have updated yet today)")
    log("Done.")


if __name__ == "__main__":
    main()
