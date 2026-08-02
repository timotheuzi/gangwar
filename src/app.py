# Gangwar Master Engine - Production Build (Final Stable & Integrated)
import os
import time
import random
import json
import argparse
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

app = Flask(__name__)
app.secret_key = 'pimp_syndicate_secret_777_stable'
socketio = None # Standard SocketIO placeholder for WSGI entries

# ============
# Data Helpers
# ============

# Base directory for model files - ensure it's absolute and correct relative to app.py
MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'model'))

def get_model_path(filename):
    """Returns the absolute path to a model file for server stability."""
    return os.path.join(MODEL_DIR, filename)

def load_json(filename, default=None):
    path = get_model_path(filename)
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                content = f.read()
                if content.strip():
                    return json.loads(content)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
    return default if default is not None else {}

def save_json(filename, data):
    path = get_model_path(filename)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

# Shared Data Files
BOTS_FILE = 'bots.json'
MARKET_FILE = 'global_market.json'
PRICES_FILE = 'current_drug_prices.json'
PLAYER_FILE = 'player_state.json'
NPCS_FILE = 'npcs.json'
ROOMS_FILE = 'rooms_config.json'
HIGH_SCORES_FILE = 'high_scores.json'

# ============
# Dataclasses
# ============

@dataclass
class Drugs:
    weed: int = 0; crack: int = 5; coke: int = 0; ice: int = 0; percs: int = 0; pixie_dust: int = 0; lean: int = 0; shrooms: int = 0; acid: int = 0; opium: int = 0; crystal_blue: int = 0; white_widow: int = 0; purple_haze: int = 0; fentanyl: int = 0; ketamine: int = 0; speed: int = 0; blue_dream: int = 0; red_devil: int = 0; white_china: int = 0; mdma_crystals: int = 0
    def keys(self): 
        config = load_json('drug_config.json', {"drugs": {}})
        return list(config.get('drugs', {}).keys())

@dataclass
class Weapons:
    pistols: int = 0; bullets: int = 10; grenades: int = 0; vampire_bat: int = 0; missile_launcher: int = 0; missiles: int = 0; vest: int = 0; knife: int = 1; ghost_guns: int = 0; ar15: int = 0; exploding_bullets: int = 0; hollow_point_bullets: int = 0; sword: int = 0; axe: int = 0; golden_gun: int = 0; poison_blowgun: int = 0; chain_whip: int = 0; plasma_cutter: int = 0; flamethrower: int = 0; katana: int = 0; brass_knuckles: int = 0; uzi: int = 0; sawed_off_shotgun: int = 0; sniper_rifle: int = 0; molotov: int = 0; micro_smg: int = 0; grenade_launcher: int = 0; combat_knife: int = 0; pistol_automatic: bool = False; ghost_gun_automatic: bool = False

@dataclass
class GameState:
    player_name: str = ""; gang_name: str = ""; money: int = 1000; account: int = 0; loan: int = 0; loan_days: int = 0; members: int = 1; squidies: int = 25; day: int = 1; health: int = 30; steps: int = 0; max_steps: int = 7; current_score: int = 0; current_location: str = "city"; lives: int = 3; damage: int = 0; drugs: Drugs = field(default_factory=Drugs); weapons: Weapons = field(default_factory=Weapons); drug_prices: Dict[str, int] = field(default_factory=dict)
    @property
    def max_health(self) -> int: return 30 + 10 * (self.members - 1)

# ============
# Logic Helpers
# ============

def get_game_state():
    """Reconstructs the GameState from persistent storage."""
    def filter_keys(cls, data):
        if not isinstance(data, dict): return {}
        return {k: v for k, v in data.items() if k in cls.__dataclass_fields__}

    raw_data = load_json(PLAYER_FILE)
    if not raw_data:
        raw_data = asdict(GameState())

    # Nested Object Rebuild
    raw_data['drugs'] = Drugs(**filter_keys(Drugs, raw_data.get('drugs', {})))
    raw_data['weapons'] = Weapons(**filter_keys(Weapons, raw_data.get('weapons', {})))
    raw_data['drug_prices'] = get_current_prices().get('prices', {})
    
    return GameState(**filter_keys(GameState, raw_data))

def save_game_state(gs):
    """Saves the current state to disk."""
    total = gs.money + gs.account
    gs.current_score = (total // 1000) + (gs.day * 100) + (gs.members * 50)
    save_json(PLAYER_FILE, asdict(gs))

def reset_game_state():
    gs = GameState()
    save_game_state(gs)
    return gs

# CRITICAL FIX: Always inject game_state into ALL templates automatically
@app.context_processor
def inject_game_state():
    try:
        return dict(game_state=get_game_state())
    except:
        return dict(game_state=GameState())

# ============
# Market System
# ============

def get_market_supply():
    drug_config_data = load_json('drug_config.json', {"drugs": {}})
    return load_json(MARKET_FILE, {d: 100 for d in drug_config_data.get('drugs', {})})

def modify_market_supply(drug, amount):
    market = get_market_supply()
    market[drug] = max(0, market.get(drug, 100) + amount)
    save_json(MARKET_FILE, market)

def update_daily_market_events():
    drug_config_data = load_json('drug_config.json', {"drugs": {}})
    event_multipliers = {}
    alerts = []
    for drug in drug_config_data.get('drugs', {}):
        roll = random.random()
        if roll < 0.05:
            event_multipliers[drug] = random.uniform(3.0, 6.0)
            alerts.append(f"POLICE RAIDS ON {drug.upper()}!")
        elif roll < 0.10:
            event_multipliers[drug] = random.uniform(0.1, 0.3)
            alerts.append(f"MARKET FLOODED WITH {drug.upper()}!")
        else:
            event_multipliers[drug] = random.uniform(0.8, 1.2)
            
    res = {
        "event_multipliers": event_multipliers,
        "day": time.strftime("%Y-%m-%d"),
        "fluctuation_alert": " | ".join(random.sample(alerts, min(2, len(alerts)))) if alerts else "The streets are calm today."
    }
    save_json(PRICES_FILE, res)
    return res

def get_current_prices():
    drug_config_data = load_json('drug_config.json', {"drugs": {}})
    prices_state = load_json(PRICES_FILE, {})
    if prices_state.get('day') != time.strftime("%Y-%m-%d"):
        prices_state = update_daily_market_events()
        
    market = get_market_supply()
    event_mults = prices_state.get('event_multipliers', {})
    dynamic_prices = {}
    
    for drug in drug_config_data.get('drugs', {}):
        info = drug_config_data['drugs'][drug]
        base = info.get('base_price', 1000)
        supply = market.get(drug, 100)
        supply_mult = min(5.0, max(0.2, 100.0 / max(1, supply)))
        event_mult = event_mults.get(drug, 1.0)
        dynamic_prices[drug] = int(base * event_mult * supply_mult)
        
    return {
        "prices": dynamic_prices,
        "fluctuation_alert": prices_state.get('fluctuation_alert', ""),
        "day": prices_state.get('day')
    }

# For compatibility with main.py
def load_current_drug_prices():
    return get_current_prices()

def update_daily_prices():
    return update_daily_market_events()

# ============
# High Scores
# ============

def get_high_scores():
    scores = load_json(HIGH_SCORES_FILE, [])
    if not isinstance(scores, list):
        return []
    return scores

def add_high_score(gs):
    scores = get_high_scores()
    new_score = {
        "player_name": gs.player_name or "Unknown Pimp",
        "gang_name": gs.gang_name or "No Gang",
        "score": gs.current_score,
        "money_earned": gs.money + gs.account,
        "days_survived": gs.day,
        "gang_wars_won": 0, # Placeholder
        "fights_won": 0,    # Placeholder
        "date_achieved": time.strftime("%Y-%m-%d")
    }
    scores.append(new_score)
    scores.sort(key=lambda x: x.get('score', 0), reverse=True)
    save_json(HIGH_SCORES_FILE, scores[:100])

# ============
# Chat & Bot AI
# ============

CHAT_MESSAGES = []
BOT_CHALLENGE = None

def add_chat_message(player, msg):
    m = {"player": player, "message": msg, "time": time.strftime("%H:%M"), "id": len(CHAT_MESSAGES) + 1}
    CHAT_MESSAGES.append(m)
    if len(CHAT_MESSAGES) > 100: CHAT_MESSAGES.pop(0)
    return m

def simulate_bots(player_loc=None, player_name=None):
    global BOT_CHALLENGE
    bots = load_json(BOTS_FILE, [])
    prices_info = get_current_prices()
    prices = prices_info['prices']
    drug_config_data = load_json('drug_config.json', {"drugs": {}})
    drug_list = list(drug_config_data.get('drugs', {}).keys())
    
    for b in bots:
        roll = random.random()
        if roll < 0.20:
            b['location'] = random.choice(["city", "crackhouse", "bar", "bank", "alleyway", "gunshack", "picknsave"])
        elif roll < 0.60 and drug_list:
            d = random.choice(drug_list)
            p = prices.get(d, 1000)
            if random.random() < 0.4 and b['money'] > p * 10:
                qty = random.randint(2, 10); b['money'] -= qty * p; b['drugs'][d] = b['drugs'].get(d, 0) + qty
                modify_market_supply(d, -qty); add_chat_message(b['name'], f"Secured a batch of {d}.")
            elif b['drugs'].get(d, 0) > 0:
                qty = b['drugs'][d]; b['money'] += qty * p; b['drugs'][d] = 0
                modify_market_supply(d, qty); add_chat_message(b['name'], f"Unloaded some weight of {d.upper()}. Cash only.")
        elif roll < 0.85:
            if b['location'] == player_loc and player_name and not BOT_CHALLENGE:
                BOT_CHALLENGE = b['name']
                add_chat_message(b['name'], f"Yo {player_name}, this is MY turf! Get out or get smoked!")
    save_json(BOTS_FILE, bots)

def get_who_list():
    gs = get_game_state()
    online = [{"name": gs.player_name, "type": "Player", "loc": gs.current_location}]
    bots = load_json(BOTS_FILE, [])
    for b in bots:
        online.append({"name": b['name'], "type": "Bot", "loc": b.get('location', 'city')})
    return online

def get_top_list():
    bots = load_json(BOTS_FILE, [])
    all_p = [{"name": b['name'], "score": (b.get('money', 0) // 1000) + (b.get('members', 1) * 50)} for b in bots]
    gs = get_game_state()
    all_p.append({"name": gs.player_name, "score": gs.current_score})
    all_p.sort(key=lambda x: x['score'], reverse=True)
    return all_p[:10]

# ============
# Combat Engine
# ============

def process_combat_action(gs, action, weapon, enemy_hp, enemy_type, enemy_count, is_boss=False):
    log, defeated, dead = [], False, False
    if action == 'attack':
        dmg = random.randint(10, 20)
        # Weapon scaling
        if weapon == 'pistol' and gs.weapons.bullets > 0:
            gs.weapons.bullets -= 1; dmg = random.randint(35, 60)
        elif weapon == 'ar15' and gs.weapons.bullets >= 3:
            gs.weapons.bullets -= 3; dmg = random.randint(70, 120)
        elif weapon == 'golden_gun':
            dmg = random.randint(300, 750)
        
        if gs.members > 1:
            g_dmg = random.randint(10, 25) * (gs.members - 1)
            dmg += g_dmg
            log.append(f"Gang fire support: +{g_dmg} dmg!")
        
        enemy_hp -= dmg
        log.append(f"You dealt {dmg} damage to {enemy_type}!")
        
        if enemy_hp > 0:
            e_dmg = random.randint(8, 20) * enemy_count
            if is_boss: e_dmg = int(e_dmg * 3.0)
            if gs.weapons.vest > 0:
                block = min(gs.weapons.vest, e_dmg // 2)
                gs.weapons.vest -= block; e_dmg -= block
                log.append(f"Vest absorbed {block} damage.")
            gs.damage += e_dmg
            log.append(f"{enemy_type} retaliates for {e_dmg} damage!")
            
    elif action == 'flee':
        if random.random() < 0.5:
            return True, enemy_hp, ["Escape successful!"], False
        else:
            e_dmg = random.randint(15, 40); gs.damage += e_dmg
            log.append(f"Escape failed! Took {e_dmg} damage.")

    if enemy_hp <= 0:
        defeated = True
        log.append(f"VICTORY! Defeated {enemy_type}. Looted cash!")
    
    if gs.damage >= 30:
        gs.lives -= 1; gs.damage = 0; gs.health = 30
        log.append("YOU WERE KNOCKED OUT! Lost a life.")
        dead = (gs.lives <= 0)
        if dead:
            add_high_score(gs)
        
    save_game_state(gs)
    return defeated, enemy_hp, log, dead

# ============
# Configuration Data
# ============
weapon_prices_config = {
    "weapons": {
        "bullets": {"price": 50},
        "pistol": {"price": 500},
        "ar15": {"price": 5000},
        "vest": {"price": 1000},
        "golden_gun": {"price": 100000},
        "katana": {"price": 2500},
        "uzi": {"price": 3500},
        "sawed_off_shotgun": {"price": 1500}
    }
}

rooms_config = load_json(ROOMS_FILE, {"rooms": {"entrance": {"title": "Street Entrance", "description": "A dark alleyway leading to the city.", "exits": {"north": "city"}}}})
npcs_data = load_json(NPCS_FILE, {})

def generate_random_room(current_rid):
    return "secret_room_" + str(random.randint(1, 100))

# ============
# Flask Routes
# ============

@app.route('/')
def index():
    gs = get_game_state()
    return render_template('index.html', game_state=gs)

@app.route('/new_game', methods=['GET', 'POST'])
def new_game():
    if request.method == 'POST':
        p_name = request.form.get('player_name')
        g_name = request.form.get('gang_name')
        if p_name and g_name:
            gs = GameState(player_name=p_name, gang_name=g_name)
            save_game_state(gs)
            session['game_state'] = True
            return redirect(url_for('city'))
    return render_template('new_game.html')

@app.route('/city')
def city():
    gs = get_game_state()
    gs.current_location = "city"
    save_game_state(gs)
    prices_data = get_current_prices()
    return render_template('city.html', game_state=gs, city_alert=prices_data.get('fluctuation_alert', ""))

@app.route('/crackhouse')
def crackhouse():
    gs = get_game_state(); gs.current_location = "crackhouse"; save_game_state(gs)
    return render_template('crackhouse.html', game_state=gs)

@app.route('/gunshack')
def gunshack():
    gs = get_game_state(); gs.current_location = "gunshack"; save_game_state(gs)
    return render_template('gunshack.html', game_state=gs)

@app.route('/bar')
def bar():
    gs = get_game_state(); gs.current_location = "bar"; save_game_state(gs)
    return render_template('bar.html', game_state=gs)

@app.route('/bank')
def bank():
    gs = get_game_state(); gs.current_location = "bank"; save_game_state(gs)
    return render_template('bank.html', game_state=gs)

@app.route('/picknsave')
def picknsave():
    gs = get_game_state(); gs.current_location = "picknsave"; save_game_state(gs)
    return render_template('picknsave.html', game_state=gs)

@app.route('/credits')
def credits():
    scores = get_high_scores()
    return render_template('credits.html', high_scores=scores)

@app.route('/high_scores')
def high_scores():
    scores = get_high_scores()
    return render_template('high_scores.html', high_scores=scores)

@app.route('/wander')
def wander():
    gs = get_game_state()
    gs.steps += 1
    simulate_bots(gs.current_location, gs.player_name)
    save_game_state(gs)
    return render_template('wander_result.html', game_state=gs)

@app.route('/alleyway')
def alleyway():
    gs = get_game_state(); gs.current_location = "alleyway"; save_game_state(gs)
    return render_template('alleyway.html', game_state=gs)

@app.route('/stats')
def stats():
    gs = get_game_state()
    return render_template('stats.html', game_state=gs)

@app.route('/final_battle')
def final_battle():
    gs = get_game_state()
    return render_template('final_battle.html', game_state=gs)

@app.route('/trade_drugs', methods=['POST'])
def trade_drugs():
    gs = get_game_state(); action = request.form.get('action'); d_type = request.form.get('drug_type'); qty = int(request.form.get('quantity', 1))
    price = gs.drug_prices.get(d_type, 1000)
    if action == 'buy' and gs.money >= price * qty:
        gs.money -= price * qty; setattr(gs.drugs, d_type, getattr(gs.drugs, d_type) + qty); modify_market_supply(d_type, -qty)
        simulate_bots(gs.current_location, gs.player_name)
    elif action == 'sell' and getattr(gs.drugs, d_type) >= qty:
        gs.money += price * qty; setattr(gs.drugs, d_type, getattr(gs.drugs, d_type) - qty); modify_market_supply(d_type, qty)
        simulate_bots(gs.current_location, gs.player_name)
    save_game_state(gs); return redirect(url_for('crackhouse'))

@app.route('/api/chat/messages')
def api_get_chat():
    return jsonify({"messages": CHAT_MESSAGES})

@app.route('/api/chat/send', methods=['POST'])
def api_send_chat():
    data = request.get_json(); player = data.get('player_name', 'Anonymous'); msg = data.get('message', '').strip()
    if not msg: return jsonify({"error": "Empty"}), 400
    if msg.startswith('/'):
        cmd = msg[1:].lower().split()[0]
        if cmd == 'who':
            who = [get_game_state().player_name] + [b['name'] for b in load_json(BOTS_FILE, [])]
            add_chat_message("SYSTEM", f"Online: {', '.join(filter(None, who))}")
        elif cmd == 'top':
            all_p = [{"name": b['name'], "score": (b['money'] // 1000) + (b['members'] * 50)} for b in load_json(BOTS_FILE, [])]
            all_p.append({"name": get_game_state().player_name, "score": get_game_state().current_score})
            all_p.sort(key=lambda x: x['score'], reverse=True)
            add_chat_message("SYSTEM", f"Top: {' | '.join([f'{p['name']} ({p['score']})' for p in all_p[:5]])}")
        return jsonify({"success": True})
    return jsonify({"success": True, "msg": add_chat_message(player, msg)})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--port', type=int, default=6009)
    args = parser.parse_args(); app.run(debug=True, host='0.0.0.0', port=args.port)
