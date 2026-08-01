# Gangwar Master Engine - Integrated Production Build
import os
import time
import random
import json
import argparse
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

app = Flask(__name__)
app.secret_key = 'pimp_secret_key_12345'
socketio = None # Standard SocketIO placeholder for entry points

# ============
# Data Helpers
# ============

def load_json(filename, default=None):
    try:
        path = os.path.join(os.path.dirname(__file__), '..', 'model', filename)
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
    return default if default is not None else {}

def save_json(filename, data):
    try:
        path = os.path.join(os.path.dirname(__file__), '..', 'model', filename)
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

# Static Configs
drug_config = load_json('drug_config.json', {"drugs": {}})
weapon_prices_config = load_json('weapon_prices.json', {"weapons": {}})
npcs_data = load_json('npcs.json', {})
rooms_config = load_json('rooms_config.json', {"rooms": {}})

# ============
# Market System
# ============

def get_market_supply():
    return load_json(MARKET_FILE, {d: 100 for d in drug_config.get('drugs', {})})

def modify_market_supply(drug, amount):
    """Adjust global supply. Positive increases supply (selling), Negative decreases (buying)."""
    market = get_market_supply()
    market[drug] = max(0, market.get(drug, 100) + amount)
    save_json(MARKET_FILE, market)

def update_daily_market_events():
    """Generates daily volatility multipliers that last for the whole game day."""
    event_multipliers = {}
    alerts = []
    
    for drug in drug_config.get('drugs', {}):
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
    """Calculates prices dynamically: Base * EventMult * (1 / SupplyFactor)"""
    market = get_market_supply()
    prices_state = load_json(PRICES_FILE, {})
    
    if prices_state.get('day') != time.strftime("%Y-%m-%d"):
        prices_state = update_daily_market_events()
        
    event_mults = prices_state.get('event_multipliers', {})
    dynamic_prices = {}
    
    for drug, info in drug_config.get('drugs', {}).items():
        base = info.get('base_price', 1000)
        supply = market.get(drug, 100)
        
        # Supply-Demand Multiplier: Lower supply = Higher price
        supply_mult = 100.0 / max(1, supply)
        supply_mult = min(5.0, max(0.2, supply_mult)) # Clamp
        
        event_mult = event_mults.get(drug, 1.0)
        dynamic_prices[drug] = int(base * event_mult * supply_mult)
        
    return {
        "prices": dynamic_prices,
        "fluctuation_alert": prices_state.get('fluctuation_alert', ""),
        "day": prices_state.get('day')
    }

# ============
# Chat & Bot AI
# ============

CHAT_MESSAGES = []
BOT_CHALLENGE = None

def add_chat_message(player, msg):
    m = {"player": player, "message": msg, "time": time.strftime("%H:%M"), "id": len(CHAT_MESSAGES) + 1}
    CHAT_MESSAGES.append(m)
    if len(CHAT_MESSAGES) > 100:
        CHAT_MESSAGES.pop(0)
    return m

def load_bots():
    return load_json(BOTS_FILE, [])

def save_bots(bots):
    save_json(BOTS_FILE, bots)

def simulate_bots(player_loc=None, player_name=None):
    """Bots roam, trade, build gangs, and start beef."""
    global BOT_CHALLENGE
    bots = load_bots()
    prices_info = get_current_prices()
    prices = prices_info['prices']
    
    for b in bots:
        roll = random.random()
        # 1. Wander (20% chance)
        if roll < 0.20:
            b['location'] = random.choice(["city", "crackhouse", "bar", "bank", "alleyway", "gunshack", "picknsave"])
        
        # 2. Trade (40% chance)
        elif roll < 0.60:
            if b['location'] in ["crackhouse", "alleyway", "city"]:
                drug_list = list(drug_config.get('drugs', {}).keys())
                if drug_list:
                    drug = random.choice(drug_list)
                    p = prices.get(drug, 1000)
                    
                    if random.random() < 0.4 and b['money'] > p * 10:
                        qty = random.randint(2, 10)
                        b['money'] -= qty * p
                        b['drugs'][drug] = b['drugs'].get(drug, 0) + qty
                        modify_market_supply(drug, -qty)
                        add_chat_message(b['name'], f"Copped a batch of {drug}. Watch the prices.")
                    elif b['drugs'].get(drug, 0) > 0:
                        qty = b['drugs'][drug]
                        b['money'] += qty * p
                        b['drugs'][drug] = 0
                        modify_market_supply(drug, qty)
                        add_chat_message(b['name'], f"Just unloaded my {drug} stash. Cash only.")
        
        # 3. Gang Building (15% chance)
        elif roll < 0.75:
            if b['money'] > 15000:
                b['money'] -= 10000
                b['members'] += 1
                add_chat_message(b['name'], "Expanding the circle. New enforcers on the block.")
            elif b['money'] > 5000:
                b['money'] -= 3000
                if 'weapons' not in b:
                    b['weapons'] = {}
                b['weapons']['bullets'] = b['weapons'].get('bullets', 0) + 200
        
        # 4. Beef (10% chance)
        elif roll < 0.85:
            if b['location'] == player_loc and player_name and not BOT_CHALLENGE:
                BOT_CHALLENGE = b['name']
                add_chat_message(b['name'], f"Yo {player_name}, this is MY turf! Get ready to bleed!")
            else:
                others = [ob for ob in bots if ob['name'] != b['name']]
                if others:
                    other = random.choice(others)
                    if b['members'] > other['members']:
                        b['money'] += 1500
                        other['members'] = max(1, other['members'] - 1)
                        add_chat_message(b['name'], f"Just handled {other['name']}'s crew. This is my city.")

    save_bots(bots)

# ============
# Dataclasses
# ============

@dataclass
class Drugs:
    weed: int = 0
    crack: int = 5
    coke: int = 0
    ice: int = 0
    percs: int = 0
    pixie_dust: int = 0
    lean: int = 0
    shrooms: int = 0
    acid: int = 0
    opium: int = 0
    crystal_blue: int = 0
    white_widow: int = 0
    purple_haze: int = 0
    fentanyl: int = 0
    ketamine: int = 0
    speed: int = 0
    blue_dream: int = 0
    red_devil: int = 0
    white_china: int = 0
    mdma_crystals: int = 0
    moon_rocks: int = 0
    blue_magic: int = 0
    grey_death: int = 0
    super_lemon_haze: int = 0
    def keys(self):
        return list(drug_config.get('drugs', {}).keys())

@dataclass
class Weapons:
    pistols: int = 0
    bullets: int = 10
    grenades: int = 0
    vampire_bat: int = 0
    missile_launcher: int = 0
    missiles: int = 0
    vest: int = 0
    knife: int = 1
    ghost_guns: int = 0
    ar15: int = 0
    exploding_bullets: int = 0
    hollow_point_bullets: int = 0
    sword: int = 0
    axe: int = 0
    golden_gun: int = 0
    poison_blowgun: int = 0
    chain_whip: int = 0
    plasma_cutter: int = 0
    flamethrower: int = 0
    katana: int = 0
    brass_knuckles: int = 0
    uzi: int = 0
    sawed_off_shotgun: int = 0
    sniper_rifle: int = 0
    molotov: int = 0
    micro_smg: int = 0
    grenade_launcher: int = 0
    combat_knife: int = 0
    pistol_automatic: bool = False
    ghost_gun_automatic: bool = False

@dataclass
class GameState:
    player_name: str = ""
    gang_name: str = ""
    money: int = 1000
    account: int = 0
    loan: int = 0
    loan_days: int = 0
    members: int = 1
    day: int = 1
    health: int = 30
    steps: int = 0
    max_steps: int = 7
    current_score: int = 0
    current_location: str = "city"
    lives: int = 3
    damage: int = 0
    drugs: Drugs = field(default_factory=Drugs)
    weapons: Weapons = field(default_factory=Weapons)
    drug_prices: Dict[str, int] = field(default_factory=dict)
    @property
    def max_health(self) -> int:
        return 30 + 10 * (self.members - 1)

# ============
# Logic Helpers
# ============

def get_game_state():
    data = load_json(PLAYER_FILE, asdict(GameState()))
    data['drugs'] = Drugs(**data.get('drugs', {}))
    w_data = data.get('weapons', {})
    data['weapons'] = Weapons(**w_data) if isinstance(w_data, dict) else Weapons()
    data['drug_prices'] = get_current_prices()['prices']
    return GameState(**data)

def save_game_state(gs):
    total = gs.money + gs.account
    gs.current_score = (total // 1000) + (gs.day * 100) + (gs.members * 50)
    save_json(PLAYER_FILE, asdict(gs))

def reset_game_state():
    path = os.path.join(os.path.dirname(__file__), '..', 'model', PLAYER_FILE)
    if os.path.exists(path):
        os.remove(path)
    return get_game_state()

def get_who_list():
    res = []
    gs = get_game_state()
    if gs.player_name:
        res.append({"name": gs.player_name, "loc": gs.current_location, "type": "Player"})
    for b in load_bots():
        res.append({"name": b['name'], "loc": b['location'], "type": "Bot"})
    return res

def get_top_list():
    res = []
    high_scores = load_json(HIGH_SCORES_FILE, [])
    for hs in high_scores:
        res.append({"name": hs.get('player_name', 'Unknown'), "score": hs.get('score', 0), "status": "Legend"})
    for b in load_bots():
        res.append({"name": b['name'], "score": (b['money'] // 1000) + (b['members'] * 50), "status": "Bot"})
    gs = get_game_state()
    if gs.player_name:
        res.append({"name": gs.player_name, "score": gs.current_score, "status": "You"})
    res.sort(key=lambda x: x['score'], reverse=True)
    return res[:10]

# ============
# Combat Engine
# ============

def process_combat_action(gs, action, weapon, enemy_hp, enemy_type, enemy_count, is_boss=False):
    log = []
    if action == 'attack':
        # Player damage
        dmg = random.randint(10, 20)
        # Weapon check and ammo deduction
        if weapon == 'pistol' and gs.weapons.pistols > 0 and gs.weapons.bullets > 0:
            gs.weapons.bullets -= 1
            dmg = random.randint(35, 60)
        elif weapon == 'ar15' and gs.weapons.ar15 > 0 and gs.weapons.bullets >= 3:
            gs.weapons.bullets -= 3
            dmg = random.randint(70, 120)
        elif weapon == 'golden_gun' and gs.weapons.golden_gun > 0:
            dmg = random.randint(300, 750)
        elif weapon == 'katana' and gs.weapons.katana > 0:
            dmg = random.randint(60, 130)
        elif weapon == 'brass_knuckles' and gs.weapons.brass_knuckles > 0:
            dmg = random.randint(30, 65)
        elif weapon == 'uzi' and gs.weapons.uzi > 0 and gs.weapons.bullets >= 5:
            gs.weapons.bullets -= 5
            dmg = random.randint(60, 110)
        elif weapon == 'sawed_off_shotgun' and gs.weapons.sawed_off_shotgun > 0 and gs.weapons.bullets >= 2:
            gs.weapons.bullets -= 2
            dmg = random.randint(100, 190)
        
        # Crew support
        if gs.members > 1:
            g_dmg = random.randint(10, 25) * (gs.members - 1)
            dmg += g_dmg
            log.append(f"Gang fire support: +{g_dmg} damage!")
        
        enemy_hp -= dmg
        log.append(f"You dealt {dmg} damage to {enemy_type}!")
        
        if enemy_hp > 0:
            # Enemy Counter-Attack
            e_dmg = random.randint(8, 20) * enemy_count
            if is_boss:
                e_dmg = int(e_dmg * 3.0)
            
            # Vest Protection
            if gs.weapons.vest > 0:
                block = min(gs.weapons.vest, e_dmg // 2)
                gs.weapons.vest -= block
                e_dmg -= block
                log.append(f"Vest absorbed {block} damage.")
            
            gs.damage += e_dmg
            log.append(f"{enemy_type} retaliates for {e_dmg} damage!")
            
    elif action == 'flee':
        if random.random() < 0.5:
            return True, enemy_hp, ["Escape successful!"], False
        else:
            e_dmg = random.randint(15, 40)
            gs.damage += e_dmg
            log.append(f"Escape failed! {enemy_type} hits you for {e_dmg} damage!")

    defeated = enemy_hp <= 0
    dead = False
    if defeated:
        log.append(f"VICTORY! Defeated {enemy_type}.")
        loot = random.randint(1000, 10000)
        gs.money += loot
        log.append(f"Looted ${loot:,} from the scene.")
        if is_boss:
            npc_id = next((k for k, v in npcs_data.items() if v['name'] == enemy_type), None)
            if npc_id:
                npcs_data[npc_id]['is_alive'] = False
                for d in npcs_data[npc_id].get('unique_drops', []):
                    if hasattr(gs.weapons, d):
                        setattr(gs.weapons, d, getattr(gs.weapons, d) + 1)
                        log.append(f"ACQUIRED UNIQUE WEAPON: {d.upper()}!")
                    elif hasattr(gs.drugs, d):
                        setattr(gs.drugs, d, getattr(gs.drugs, d) + 10)
                        log.append(f"SEIZED CACHE: 10kg {d.upper()}!")
                save_json(NPCS_FILE, npcs_data)
    
    if gs.damage >= 30:
        gs.lives -= 1
        gs.damage = 0
        gs.health = 30
        log.append("YOU WERE LEFT FOR DEAD! Lost a life.")
        if gs.lives <= 0:
            dead = True
        
    save_game_state(gs)
    return defeated, enemy_hp, log, dead

# ============
# Procedural Content Generation
# ============

def generate_random_room(prev_room_id):
    """Adds a new procedurally generated room to the config."""
    global rooms_config
    room_id = f"proc_{int(time.time())}_{random.randint(100, 999)}"
    titles = ["Hidden Trap House", "Abandoned Chem Lab", "Cartel Safehouse", "Dilapidated Loft", "Secret Armory", "Shadowy Basement", "Smuggler's Cove", "Neon Den", "Underground Casino", "Hacker's Sanctum"]
    descs = ["A heavily fortified space smelling of chemical fumes.", "Vials line the tables in this dimly lit room.", "Stacks of empty crates suggest a recent shipment.", "Neon lights flicker through broken windows.", "Weapon racks line the concrete walls.", "Dusty relics of a forgotten empire litter the floor.", "The air is thick with high-grade product.", "Hidden monitors show street feeds from above."]
    
    new_room = {
        "title": random.choice(titles),
        "description": random.choice(descs),
        "exits": {"south": prev_room_id}
    }
    
    if prev_room_id in rooms_config['rooms']:
        rooms_config['rooms'][prev_room_id]['exits']['north'] = room_id
        
    rooms_config['rooms'][room_id] = new_room
    save_json(ROOMS_FILE, rooms_config)
    return room_id

# ============
# Flask Routes
# ============

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/city')
def city():
    gs = get_game_state()
    gs.current_location = "city"
    save_game_state(gs)
    prices_data = get_current_prices()
    return render_template('city.html', game_state=gs, city_alert=prices_data.get('fluctuation_alert', ''))

@app.route('/crackhouse')
def crackhouse():
    gs = get_game_state()
    gs.current_location = "crackhouse"
    save_game_state(gs)
    return render_template('crackhouse.html', game_state=gs)

@app.route('/trade_drugs', methods=['POST'])
def trade_drugs():
    gs = get_game_state()
    action = request.form.get('action')
    d_type = request.form.get('drug_type')
    qty = int(request.form.get('quantity', 1))
    price = gs.drug_prices.get(d_type, 1000)
    
    if action == 'buy' and gs.money >= price * qty:
        gs.money -= price * qty
        setattr(gs.drugs, d_type, getattr(gs.drugs, d_type) + qty)
        modify_market_supply(d_type, -qty)
        simulate_bots(gs.current_location, gs.player_name)
    elif action == 'sell' and getattr(gs.drugs, d_type) >= qty:
        gs.money += price * qty
        setattr(gs.drugs, d_type, getattr(gs.drugs, d_type) - qty)
        modify_market_supply(d_type, qty)
        simulate_bots(gs.current_location, gs.player_name)
    
    save_game_state(gs)
    return redirect(url_for('crackhouse'))

@app.route('/gunshack')
def gunshack():
    gs = get_game_state()
    gs.current_location = "gunshack"
    save_game_state(gs)
    return render_template('gunshack.html', game_state=gs)

@app.route('/buy_weapon', methods=['POST'])
def buy_weapon():
    gs = get_game_state()
    w_type = request.form.get('weapon_type')
    qty = int(request.form.get('quantity', 1))
    
    price_info = weapon_prices_config['weapons'].get(w_type)
    if not price_info:
        return redirect(url_for('gunshack'))
    
    total_cost = price_info['price'] * qty
    if gs.money < total_cost:
        flash(f"Need ${total_cost:,}!", "danger")
        return redirect(url_for('gunshack'))
        
    gs.money -= total_cost
    if w_type.endswith('bullets'):
        setattr(gs.weapons, w_type, getattr(gs.weapons, w_type) + qty * 50)
    elif hasattr(gs.weapons, f"{w_type}s"):
        setattr(gs.weapons, f"{w_type}s", getattr(gs.weapons, f"{w_type}s") + qty)
    else:
        setattr(gs.weapons, w_type, getattr(gs.weapons, w_type) + qty)
        
    save_game_state(gs)
    flash(f"Bought {qty} {w_type}!", "success")
    return redirect(url_for('gunshack'))

@app.route('/bank')
def bank():
    gs = get_game_state()
    gs.current_location = "bank"
    save_game_state(gs)
    return render_template('bank.html', game_state=gs)

@app.route('/bank_transaction', methods=['POST'])
def bank_transaction():
    gs = get_game_state()
    action = request.form.get('action')
    amount = int(request.form.get('amount', 0))
    if action == 'deposit' and gs.money >= amount:
        gs.money -= amount
        gs.account += amount
    elif action == 'withdraw' and gs.account >= amount:
        gs.account -= amount
        gs.money += amount
    elif action == 'loan' and gs.loan == 0:
        gs.loan = amount
        gs.money += amount
    elif action == 'pay_loan' and gs.money >= amount:
        gs.money -= amount
        gs.loan = max(0, gs.loan - amount)
    save_game_state(gs)
    return redirect(url_for('bank'))

@app.route('/alleyway')
def alleyway():
    gs = get_game_state()
    gs.current_location = "alleyway"
    save_game_state(gs)
    curr = session.get('current_alleyway_room', 'entrance')
    room = rooms_config['rooms'].get(curr, rooms_config['rooms']['entrance'])
    return render_template('alleyway.html', game_state=gs, current_room=room)

@app.route('/move_room/<direction>')
def move_room(direction):
    gs = get_game_state()
    curr = session.get('current_alleyway_room', 'entrance')
    exits = rooms_config['rooms'].get(curr, {}).get('exits', {})
    if direction in exits:
        next_r = exits[direction]
        if next_r == 'city':
            session['current_alleyway_room'] = 'entrance'
            return redirect(url_for('city'))
        session['current_alleyway_room'] = next_r
        gs.steps += 1
        simulate_bots(gs.current_location, gs.player_name)
        if gs.steps >= gs.max_steps:
            gs.day += 1
            gs.steps = 0
            update_daily_market_events()
        save_game_state(gs)
    return redirect(url_for('alleyway'))

@app.route('/wander')
def wander():
    gs = get_game_state()
    gs.steps += 1
    simulate_bots(gs.current_location, gs.player_name)
    if gs.steps >= gs.max_steps:
        gs.day += 1
        gs.steps = 0
        update_daily_market_events()
    save_game_state(gs)
    return render_template('wander_result.html', game_state=gs, result="You wander the streets.")

@app.route('/api/chat/messages')
def api_get_chat():
    return jsonify({"messages": CHAT_MESSAGES})

@app.route('/api/chat/send', methods=['POST'])
def api_send_chat():
    data = request.get_json()
    player = data.get('player_name', 'Anonymous')
    msg = data.get('message', '').strip()
    if not msg:
        return jsonify({"error": "Empty"}), 400
    if msg.startswith('/'):
        cmd = msg[1:].lower().split()[0]
        if cmd == 'who':
            add_chat_message("SYSTEM", f"Online: {', '.join([e['name'] for e in get_who_list()])}")
        elif cmd == 'top':
            add_chat_message("SYSTEM", f"Leaderboard: {' | '.join([f'{p['name']} ({p['score']})' for p in get_top_list()[:5]])}")
        return jsonify({"success": True})
    return jsonify({"success": True, "msg": add_chat_message(player, msg)})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=6009)
    args = parser.parse_args()
    app.run(debug=True, host='0.0.0.0', port=args.port)
