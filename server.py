"""
Today in Hawaii — Backend Server
"""

from flask import Flask, redirect, jsonify, send_from_directory, request, Response
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
        'Maui':       {'arr': 7000,  'dep': 6500,  'dom': 6100, 'intl': 900},
        'Oahu':       {'arr': 15800, 'dep': 14800, 'dom': 12000, 'intl': 3800},
        'Kauai':      {'arr': 2200,  'dep': 2050,  'dom': 1950, 'intl': 250},
        'Big Island': {'arr': 3500,  'dep': 3250,  'dom': 2950, 'intl': 550},
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
            'change_pct': round(variation * 10, 1), 'on_island_est': round(arr * 9.2)
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

@app.route("/hiking")
def hiking():
    return send_from_directory(".", "hiking.html")

@app.route("/beaches")
def beaches():
    return send_from_directory(".", "beaches.html")

@app.route("/food")
def food():
    return send_from_directory(".", "food.html")

@app.route("/admin")
def admin():
    return send_from_directory(".", "admin.html")

@app.route("/banner.jpg")
def banner():
    return send_from_directory(".", "banner.jpg")

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory('.', 'sitemap.xml', mimetype='application/xml')

@app.route("/robots.txt")
def robots():
    return send_from_directory(".", "robots.txt")

# ── STATIC IMAGE ROUTES ──
@app.route('/fruit-<int:num>.jpg')
def fruit_image(num):
    return send_from_directory('.', 'fruit-' + str(num) + '.jpg')

@app.route('/<int:num>.jpg')
def photo_image(num):
    return send_from_directory('.', str(num) + '.jpg')

@app.route('/808-<int:num>.jpg')
def photo_808(num):
    return send_from_directory('.', '808-' + str(num) + '.jpg')

@app.route('/icon-<int:num>.png')
def icon_image(num):
    return send_from_directory('.', 'icon-' + str(num) + '.png')

# ── HULA CRUSH / ALOHA MEMORY GAME ──
@app.route('/hulacrush')
def hula_crush():
    return send_from_directory('.', 'hulaCrush.html')

@app.route('/games')
def games_hub():
    return send_from_directory('.', 'games.html')

@app.route('/trivia')
def trivia_game():
    return send_from_directory('.', 'trivia.html')

@app.route('/wordsearch')
def wordsearch_game():
    return send_from_directory('.', 'wordsearch.html')

@app.route('/scrabble')
def scrabble_game():
    return send_from_directory('.', 'scrabble.html')

@app.route('/balloons')
def balloons_game():
    return send_from_directory('.', 'balloons.html')

@app.route('/dolphins')
def dolphins_game():
    return send_from_directory('.', 'dolphin.html')

@app.route('/fortune')
def fortune_game():
    return send_from_directory('.', 'fortune.html')

@app.route('/humor')
def humor_game():
    return send_from_directory('.', 'humor.html')

@app.route('/slime')
def slime_game():
    return send_from_directory('.', 'slime.html')

@app.route('/lava')
def lava_game():
    return send_from_directory('.', 'lava.html')

@app.route('/lava_score', methods=['POST'])
def save_lava_score():
    import json, os
    data = request.get_json()
    f = 'lava_scores.json'
    scores = json.load(open(f)) if os.path.exists(f) else []
    scores.append({'name':data.get('name','?'),'location':data.get('location','Hawaii'),
                   'score':int(data.get('score',0))})
    scores.sort(key=lambda x:x['score'],reverse=True)
    json.dump(scores[:100],open(f,'w'))
    return jsonify({'ok':True})

@app.route('/lava_scores')
def get_lava_scores():
    import json, os
    f = 'lava_scores.json'
    scores = json.load(open(f)) if os.path.exists(f) else []
    return jsonify(scores[:10])

@app.route('/turtles')
def turtles_game():
    return send_from_directory('.', 'turtles.html')

@app.route('/turtle_score', methods=['POST'])
def save_turtle_score():
    import json, os
    data = request.get_json()
    f = 'turtle_scores.json'
    scores = json.load(open(f)) if os.path.exists(f) else []
    scores.append({'name':data.get('name','?'),'location':data.get('location','Hawaii'),
                   'score':int(data.get('score',0)),'difficulty':int(data.get('difficulty',1))})
    scores.sort(key=lambda x:x['score'],reverse=True)
    json.dump(scores[:100],open(f,'w'))
    return jsonify({'ok':True})

@app.route('/turtle_scores')
def get_turtle_scores():
    import json, os
    f = 'turtle_scores.json'
    scores = json.load(open(f)) if os.path.exists(f) else []
    return jsonify(scores[:10])

@app.route('/chess')
def chess_game():
    return send_from_directory('.', 'chess.html')

@app.route('/chess_<piece>.png')
def chess_piece_img(piece):
    import os
    if os.path.exists(f'chess_{piece}.png'):
        return send_from_directory('.', f'chess_{piece}.png')
    return '', 404

@app.route('/dolphin_back.jpg')
def dolphin_back():
    import os
    if os.path.exists('dolphin_back.jpg'):
        return send_from_directory('.', 'dolphin_back.jpg')
    return '', 404

@app.route('/card_<card>.jpg')
def dolphin_card(card):
    import os
    f = f'card_{card}.jpg'
    if os.path.exists(f):
        return send_from_directory('.', f)
    return '', 404

@app.route('/chess_bg.mp4')
def chess_bg1(): 
    return send_from_directory('.','chess_bg.mp4') if __import__('os').path.exists('chess_bg.mp4') else ('',404)

@app.route('/chess_bg2.mp4')
def chess_bg2():
    return send_from_directory('.','chess_bg2.mp4') if __import__('os').path.exists('chess_bg2.mp4') else ('',404)

@app.route('/chess_bg3.mp4')
def chess_bg3():
    return send_from_directory('.','chess_bg3.mp4') if __import__('os').path.exists('chess_bg3.mp4') else ('',404)

@app.route('/chess_bg4.mp4')
def chess_bg4():
    return send_from_directory('.','chess_bg4.mp4') if __import__('os').path.exists('chess_bg4.mp4') else ('',404)

@app.route('/chess_bg5.mp4')
def chess_bg5():
    return send_from_directory('.','chess_bg5.mp4') if __import__('os').path.exists('chess_bg5.mp4') else ('',404)

@app.route('/chess_score', methods=['POST'])
def save_chess_score():
    import json, os
    data = request.get_json()
    f = 'chess_scores.json'
    scores = json.load(open(f)) if os.path.exists(f) else []
    scores.append({'name':data.get('name','?'),'location':data.get('location','Hawaii'),
                   'score':int(data.get('score',0)),'difficulty':int(data.get('difficulty',1))})
    scores.sort(key=lambda x:x['score'],reverse=True)
    json.dump(scores[:100],open(f,'w'))
    return jsonify({'ok':True})

@app.route('/chess_scores')
def get_chess_scores():
    import json, os
    f = 'chess_scores.json'
    scores = json.load(open(f)) if os.path.exists(f) else []
    return jsonify(scores[:10])

@app.route('/card_<name>.jpg')
def card_image(name):
    return send_from_directory('.', 'card_'+name+'.jpg')

@app.route('/api/dolphin-scores', methods=['GET'])
def get_dolphin_scores():
    import json as _j
    try:
        scores=_j.load(open('dolphin_scores.json')) if os.path.exists('dolphin_scores.json') else []
        scores.sort(key=lambda x:x.get('timeSecs',99999))
        return app.response_class(_j.dumps(scores[:20]),mimetype='application/json')
    except:
        return app.response_class('[]',mimetype='application/json')

@app.route('/api/dolphin-scores', methods=['POST'])
def post_dolphin_score():
    import json as _j
    try:
        data=request.get_json()
        name=str(data.get('name',''))[:20].strip()
        score=int(data.get('score',0))
        island=str(data.get('island',''))[:30]
        level=int(data.get('level',0))
        timeSecs=int(data.get('timeSecs',99999))
        timeStr=str(data.get('timeStr','?'))[:10]
        if score<=0: return app.response_class(_j.dumps({'ok':False}),mimetype='application/json')
        scores=[]
        if os.path.exists('dolphin_scores.json'):
            with open('dolphin_scores.json') as f: scores=_j.load(f)
        existing=next((s for s in scores if s.get('name','').lower()==name.lower()),None)
        if existing:
            if timeSecs < existing.get('timeSecs',99999):
                existing.update({'score':score,'island':island,'level':level,'timeSecs':timeSecs,'timeStr':timeStr,'date':datetime.now().strftime('%b %d, %Y')})
        else:
            scores.append({'name':name,'score':score,'island':island,'level':level,'timeSecs':timeSecs,'timeStr':timeStr,'date':datetime.now().strftime('%b %d, %Y')})
        scores.sort(key=lambda x:x.get('timeSecs',99999))
        scores=scores[:100]
        with open('dolphin_scores.json','w') as f: _j.dump(scores,f)
        rank=next((i+1 for i,s in enumerate(scores) if s.get('name','').lower()==name.lower()),0)
        return app.response_class(_j.dumps({'ok':True,'rank':rank}),mimetype='application/json')
    except:
        return app.response_class(_j.dumps({'ok':False}),status=500,mimetype='application/json')

@app.route('/api/balloon-scores', methods=['GET'])
def get_balloon_scores():
    import json as _j
    try:
        scores=_j.load(open('balloon_scores.json')) if os.path.exists('balloon_scores.json') else []
        scores.sort(key=lambda x:x.get('score',0),reverse=True)
        return app.response_class(_j.dumps(scores[:20]),mimetype='application/json')
    except:
        return app.response_class('[]',mimetype='application/json')

@app.route('/api/balloon-scores', methods=['POST'])
def post_balloon_score():
    import json as _j
    try:
        data=request.get_json()
        name=str(data.get('name',''))[:20].strip()
        score=int(data.get('score',0))
        island=str(data.get('island',''))[:30]
        level=int(data.get('level',0))
        if score<=0:
            return app.response_class(_j.dumps({'ok':False}),mimetype='application/json')
        scores=[]
        if os.path.exists('balloon_scores.json'):
            with open('balloon_scores.json') as f: scores=_j.load(f)
        existing=next((s for s in scores if s.get('name','').lower()==name.lower()),None)
        if existing:
            if score>existing.get('score',0):
                existing.update({'score':score,'island':island,'level':level,'date':datetime.now().strftime('%b %d, %Y')})
        else:
            scores.append({'name':name,'score':score,'island':island,'level':level,'date':datetime.now().strftime('%b %d, %Y')})
        scores.sort(key=lambda x:x.get('score',0),reverse=True)
        scores=scores[:100]
        with open('balloon_scores.json','w') as f: _j.dump(scores,f)
        rank=next((i+1 for i,s in enumerate(scores) if s.get('name','').lower()==name.lower()),0)
        return app.response_class(_j.dumps({'ok':True,'rank':rank}),mimetype='application/json')
    except:
        return app.response_class(_j.dumps({'ok':False}),status=500,mimetype='application/json')

@app.route('/words.js')
def words_js():
    from flask import Response
    try:
        with open('words.js', 'r') as f:
            content = f.read()
        return Response(content, mimetype='application/javascript')
    except:
        return Response('window.DICTIONARY=new Set(["NET","GEM","CAT","DOG"]);', mimetype='application/javascript')

@app.route('/api/scrabble-scores', methods=['GET'])
def get_scrabble_scores():
    import json as _j
    try:
        scores=_j.load(open('scrabble_scores.json')) if os.path.exists('scrabble_scores.json') else []
        scores.sort(key=lambda x:x.get('score',0),reverse=True)
        return app.response_class(_j.dumps(scores[:20]),mimetype='application/json')
    except:
        return app.response_class('[]',mimetype='application/json')

@app.route('/api/scrabble-scores', methods=['POST'])
def post_scrabble_score():
    import json as _j
    try:
        data=request.get_json()
        name=str(data.get('name',''))[:20].strip()
        score=int(data.get('score',0))
        island=str(data.get('island',''))[:30]
        level=int(data.get('level',0))
        if score<=0:
            return app.response_class(_j.dumps({'ok':False}),mimetype='application/json')
        scores=[]
        if os.path.exists('scrabble_scores.json'):
            with open('scrabble_scores.json') as f: scores=_j.load(f)
        existing=next((s for s in scores if s.get('name','').lower()==name.lower()),None)
        if existing:
            if score>existing.get('score',0):
                existing.update({'score':score,'island':island,'level':level,'date':datetime.now().strftime('%b %d, %Y')})
        else:
            scores.append({'name':name,'score':score,'island':island,'level':level,'date':datetime.now().strftime('%b %d, %Y')})
        scores.sort(key=lambda x:x.get('score',0),reverse=True)
        scores=scores[:100]
        with open('scrabble_scores.json','w') as f: _j.dump(scores,f)
        rank=next((i+1 for i,s in enumerate(scores) if s.get('name','').lower()==name.lower()),0)
        return app.response_class(_j.dumps({'ok':True,'rank':rank}),mimetype='application/json')
    except:
        return app.response_class(_j.dumps({'ok':False}),status=500,mimetype='application/json')

@app.route('/api/wordsearch-scores', methods=['GET'])
def get_ws_scores():
    import json as _j
    try:
        scores = _j.load(open('wordsearch_scores.json')) if os.path.exists('wordsearch_scores.json') else []
        scores.sort(key=lambda x: x.get('score',0), reverse=True)
        return app.response_class(_j.dumps(scores[:20]), mimetype='application/json')
    except:
        return app.response_class('[]', mimetype='application/json')

@app.route('/api/wordsearch-scores', methods=['POST'])
def post_ws_score():
    import json as _j
    try:
        data = request.get_json()
        name = str(data.get('name',''))[:20].strip()
        score = int(data.get('score',0))
        island = str(data.get('island',''))[:30]
        level = int(data.get('level',0))
        if score <= 0:
            return app.response_class(_j.dumps({'ok':False}), mimetype='application/json')
        scores = []
        if os.path.exists('wordsearch_scores.json'):
            with open('wordsearch_scores.json') as f:
                scores = _j.load(f)
        existing = next((s for s in scores if s.get('name','').lower()==name.lower()), None)
        if existing:
            if score > existing.get('score',0):
                existing.update({'score':score,'island':island,'level':level,'date':datetime.now().strftime('%b %d, %Y')})
        else:
            scores.append({'name':name,'score':score,'island':island,'level':level,'date':datetime.now().strftime('%b %d, %Y')})
        scores.sort(key=lambda x: x.get('score',0), reverse=True)
        scores = scores[:100]
        with open('wordsearch_scores.json','w') as f:
            _j.dump(scores, f)
        rank = next((i+1 for i,s in enumerate(scores) if s.get('name','').lower()==name.lower()), 0)
        return app.response_class(_j.dumps({'ok':True,'rank':rank}), mimetype='application/json')
    except Exception as e:
        return app.response_class(_j.dumps({'ok':False}), status=500, mimetype='application/json')

@app.route('/api/trivia-scores', methods=['GET'])
def get_trivia_scores():
    import json as _j
    try:
        if os.path.exists('trivia_scores.json'):
            with open('trivia_scores.json') as f:
                scores = _j.load(f)
        else:
            scores = []
        scores.sort(key=lambda x: x.get('score',0), reverse=True)
        return app.response_class(_j.dumps(scores[:20]), mimetype='application/json')
    except:
        return app.response_class('[]', mimetype='application/json')

@app.route('/api/trivia-scores', methods=['POST'])
def post_trivia_score():
    import json as _j
    try:
        data = request.get_json()
        name = str(data.get('name',''))[:20].strip()
        score = int(data.get('score',0))
        island = str(data.get('island',''))[:30]
        correct = int(data.get('correct',0))
        if score <= 0:
            return app.response_class(_j.dumps({'ok':False}), mimetype='application/json')
        scores = []
        if os.path.exists('trivia_scores.json'):
            with open('trivia_scores.json') as f:
                scores = _j.load(f)
        existing = next((s for s in scores if s.get('name','').lower()==name.lower()), None)
        if existing:
            if score > existing.get('score',0):
                existing['score'] = score
                existing['island'] = island
                existing['correct'] = correct
                existing['date'] = datetime.now().strftime('%b %d, %Y')
        else:
            scores.append({'name':name,'score':score,'island':island,'correct':correct,'date':datetime.now().strftime('%b %d, %Y')})
        scores.sort(key=lambda x: x.get('score',0), reverse=True)
        scores = scores[:100]
        with open('trivia_scores.json','w') as f:
            _j.dump(scores, f)
        rank = next((i+1 for i,s in enumerate(scores) if s.get('name','').lower()==name.lower()), 0)
        return app.response_class(_j.dumps({'ok':True,'rank':rank}), mimetype='application/json')
    except Exception as e:
        return app.response_class(_j.dumps({'ok':False}), status=500, mimetype='application/json')

@app.route('/memorygame')
def memory_game():
    return send_from_directory('.', 'hulaCrush.html')

# ── HAWAII CHARITIES ──
@app.route('/hawaiicharities')
def hawaii_charities():
    return redirect('/#hawaii-charities')

@app.route('/charities')
def charities_short():
    return redirect('/#hawaii-charities')

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
                          "net_flow": total_arr - total_dep, "on_island_est": round(total_arr * 9.2)},
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
                                   "change_pct": change_pct, "on_island_est": round(arr * 9.2) if arr else None}
            total_arr = sum((v["arrivals"] or 0) for v in islands.values())
            total_dep = sum((v["departures"] or 0) for v in islands.values())
            return jsonify({"date": latest_date, "source": "csv", "updated_at": datetime.now().isoformat(),
                            "statewide": {"arrivals": total_arr, "departures": total_dep,
                                          "net_flow": total_arr - total_dep, "on_island_est": round(total_arr * 9.2)},
                            "islands": islands})

    islands = generate_stable_data(today)
    total_arr = sum(v['arrivals'] for v in islands.values())
    total_dep = sum(v['departures'] for v in islands.values())
    return jsonify({"date": today.isoformat(), "source": "estimate", "updated_at": datetime.now().isoformat(),
                    "statewide": {"arrivals": total_arr, "departures": total_dep,
                                  "net_flow": total_arr - total_dep, "on_island_est": round(total_arr * 9.2)},
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


# ── BLOG ROUTES ──
import json as _json
import urllib.request as _urllib

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
ADMIN_KEY = 'aloha2026'

def sb_headers():
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + SUPABASE_KEY,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }

def load_posts():
    try:
        req = _urllib.Request(
            SUPABASE_URL + '/rest/v1/posts?select=*&status=eq.published&order=date.desc',
            headers=sb_headers()
        )
        r = _urllib.urlopen(req, timeout=5)
        return _json.loads(r.read().decode())
    except Exception as e:
        print('Supabase load error:', e)
        return []

def load_all_posts():
    try:
        req = _urllib.Request(
            SUPABASE_URL + '/rest/v1/posts?select=*&order=date.desc',
            headers=sb_headers()
        )
        r = _urllib.urlopen(req, timeout=5)
        return _json.loads(r.read().decode())
    except Exception as e:
        print('Supabase load error:', e)
        return []

def save_post(post):
    try:
        data = _json.dumps(post).encode()
        req = _urllib.Request(
            SUPABASE_URL + '/rest/v1/posts',
            data=data,
            headers={**sb_headers(), 'Prefer': 'resolution=merge-duplicates,return=representation'},
            method='POST'
        )
        r = _urllib.urlopen(req, timeout=5)
        return _json.loads(r.read().decode())
    except Exception as e:
        print('Supabase save error:', e)
        return None

def delete_post_db(post_id):
    try:
        req = _urllib.Request(
            SUPABASE_URL + '/rest/v1/posts?id=eq.' + post_id,
            headers=sb_headers(),
            method='DELETE'
        )
        _urllib.urlopen(req, timeout=5)
        return True
    except Exception as e:
        print('Supabase delete error:', e)
        return False

def check_admin(req):
    return req.headers.get('X-Admin-Key') == ADMIN_KEY

@app.route('/blog')
def blog_index():
    return send_from_directory('.', 'blog.html')

@app.route('/blog/admin')
def blog_admin():
    return send_from_directory('.', 'blog_admin.html')

@app.route('/blog/posts', methods=['GET'])
def get_posts():
    posts = load_posts()
    return app.response_class(_json.dumps(posts), mimetype='application/json')

@app.route('/blog/all-posts', methods=['GET'])
def get_all_posts():
    if not check_admin(request):
        return app.response_class('{"error":"Unauthorized"}', status=401, mimetype='application/json')
    posts = load_all_posts()
    return app.response_class(_json.dumps(posts), mimetype='application/json')

@app.route('/blog/post/<slug>', methods=['GET'])
def get_post(slug):
    try:
        req = _urllib.Request(
            SUPABASE_URL + '/rest/v1/posts?slug=eq.' + slug + '&status=eq.published&select=*',
            headers=sb_headers()
        )
        r = _urllib.urlopen(req, timeout=5)
        posts = _json.loads(r.read().decode())
        if not posts:
            return app.response_class('{"error":"Not found"}', status=404, mimetype='application/json')
        return app.response_class(_json.dumps(posts[0]), mimetype='application/json')
    except Exception as e:
        return app.response_class('{"error":"Server error"}', status=500, mimetype='application/json')

@app.route('/blog/posts', methods=['POST'])
def create_post():
    if not check_admin(request):
        return app.response_class('{"error":"Unauthorized"}', status=401, mimetype='application/json')
    result = save_post(request.get_json())
    return app.response_class('{"ok":true}', mimetype='application/json')

@app.route('/blog/posts', methods=['PUT'])
def update_post():
    if not check_admin(request):
        return app.response_class('{"error":"Unauthorized"}', status=401, mimetype='application/json')
    result = save_post(request.get_json())
    return app.response_class('{"ok":true}', mimetype='application/json')

@app.route('/blog/posts/<post_id>', methods=['DELETE'])
def delete_post(post_id):
    if not check_admin(request):
        return app.response_class('{"error":"Unauthorized"}', status=401, mimetype='application/json')
    delete_post_db(post_id)
    return app.response_class('{"ok":true}', mimetype='application/json')

@app.route('/blog/<path:slug>')
def blog_post_view(slug):
    return send_from_directory('.', 'blog_post.html')


# ── EMAIL SIGNUP ──
MAILERLITE_KEY = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI0IiwianRpIjoiZWU4NzYwOWE5MTViZTMyZTE0NThiOWM5MDA3NTIxMzc2Zjk1OTFhZDdjY2ZjZTI0YjM5ZjA4OWJlZTQ4OGM2M2Q5MGI4YWU3MTAwN2Y2MDUiLCJpYXQiOjE3NzkxMjE2NzcuNjY5NjM2LCJuYmYiOjE3NzkxMjE2NzcuNjY5NjM5LCJleHAiOjQ5MzQ3OTUyNzcuNjYzMjU1LCJzdWIiOiIyMzc3NDc0Iiwic2NvcGVzIjpbXX0.PfkFmcHyhw9ERRgjh3r1UQA7nsBUI2Z2_qJvGehr15ioVFoOvfrdiGhcvbUPe5v-Lp1aooEa_aCeUzBzrFi3Nl3Iz6b-R9k7ULZuSX3boIAOwWGsHO4jrZkrW9tlZUL8zf5rtOBRdMfjfOaI5XGo0hew5QTqoyCzq-Jp-iVAOkzeHa2xAtxZos0psmgRnrz8EUmRm9WvAGMjGpJHUjb1zn3Do73QCI_2z81CMcouFJ7GREJTPC0PnSYvWjl5Z2xtCGfihGGsKG_rUbrpTKB4DsIp-MLErXS9KAeuggJVvLerrf5GLT3IzD0s-3Nh1WGEGGW2qFCZYWIZ43cMYwkghfx0RKC3yRMvdXVBs7YfyLcUzDMk3UNzMNgA_LIKIvuN3QRDIDLQrH7YdJti3CK1PG9JikMuRORpHpRIsKjeu55oUapVLCCUOy_M7Q1SWRBNwADep1QGYFDWMzhoyvMOpLcO6YT_NtDe4C4pnTCZnBv4iVGOaExSEPlFhcMjfqxvdJUhzA8ukvbQT9co47l_IXDqp1OwoBsv_7ynTa43N4sTz8N2BxS-lI4hcE80h-aSXWrB10tOcje3eGINlrGlIPWb0lPJ2FdA0S7Vi9vT5bmvIPgbwTuTrxLosk-GN-ZJiFHf95ru2EBHRsMNPxsdBYY00NK5otkHiAgzSbp-Uss'
MAILERLITE_GROUP = '187822269207151744'

@app.route('/subscribe', methods=['POST'])
def subscribe():
    import json as _j
    import urllib.request as _u
    try:
        data = request.get_json()
        email = data.get('email','').strip()
        name = data.get('name','').strip()
        if not email:
            return app.response_class(_j.dumps({'error':'Email required'}), status=400, mimetype='application/json')
        payload = _j.dumps({'email':email,'fields':{'name':name},'groups':[MAILERLITE_GROUP],'status':'active'}).encode()
        req = _u.Request('https://connect.mailerlite.com/api/subscribers',
            data=payload,
            headers={'Authorization':'Bearer '+MAILERLITE_KEY,'Content-Type':'application/json','Accept':'application/json'},
            method='POST')
        r = _u.urlopen(req, timeout=5)
        return app.response_class(_j.dumps({'ok':True}), mimetype='application/json')
    except Exception as e:
        err = str(e)
        if '422' in err or 'already' in err.lower():
            return app.response_class(_j.dumps({'ok':True,'existing':True}), mimetype='application/json')
        print('Signup error:', e)
        return app.response_class(_j.dumps({'error':str(e)}), status=500, mimetype='application/json')

# ── HULA SCORES LEADERBOARD ──
import json
SCORES_FILE = 'hula_scores.json'

def load_scores():
    try:
        if os.path.exists(SCORES_FILE):
            with open(SCORES_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_scores(scores):
    try:
        with open(SCORES_FILE, 'w') as f:
            json.dump(scores, f)
    except Exception as e:
        print('Score save error:', e)

@app.route('/api/hula-scores', methods=['GET'])
def get_hula_scores():
    scores = load_scores()
    scores.sort(key=lambda x: x.get('score', 0), reverse=True)
    return app.response_class(
        json.dumps(scores[:20]),
        mimetype='application/json'
    )

@app.route('/api/hula-scores', methods=['POST'])
def post_hula_score():
    try:
        data = request.get_json()
        name = str(data.get('name', 'Hawaii Player'))[:20].strip()
        score = int(data.get('score', 0))
        island = str(data.get('island', 'Hawaii'))[:30]
        level = int(data.get('level', 1))
        if score <= 0:
            return app.response_class(json.dumps({'ok': False}), mimetype='application/json')
        scores = load_scores()
        existing = next((s for s in scores if s.get('name','').lower() == name.lower()), None)
        if existing:
            if score > existing.get('score', 0):
                existing['score'] = score
                existing['island'] = island
                existing['level'] = level
                existing['date'] = datetime.now().strftime('%b %d, %Y')
        else:
            scores.append({
                'name': name, 'score': score, 'island': island,
                'level': level, 'date': datetime.now().strftime('%b %d, %Y')
            })
        scores.sort(key=lambda x: x.get('score', 0), reverse=True)
        scores = scores[:100]
        save_scores(scores)
        rank = next((i+1 for i, s in enumerate(scores) if s.get('name','').lower() == name.lower()), 0)
        return app.response_class(json.dumps({'ok': True, 'rank': rank}), mimetype='application/json')
    except Exception as e:
        print('Score post error:', e)
        return app.response_class(json.dumps({'ok': False}), status=500, mimetype='application/json')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
