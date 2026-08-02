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

def get_model_path(filename):
    """Returns the absolute path to a model file for server stability."""
    # Try multiple common locations for model files
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'model', filename)),
        os.path.abspath(os.path.join(os.getcwd(), 'model', filename)),
        os.path.abspath(os.path.join('/home/gangwars/gangwar/model', filename))
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return possible_paths[0] # Default

def load_json(filename, default=None):
    path = get_model_path(filename)
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                content = f.read()
                return json.loads(content) if content else (default or {})
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
class Flags:
    has_id: bool = False
    has_info: bool = False

@dataclass
class GameState:
    player_name: str = ""; gang_name: str = ""; money: int = 1000; account: int = 0; loan: int = 0; loan_days: int = 0; members: int = 1; squidies: int = 25; squidies_pistols: int = 10; squidies_ar15s: int = 5; squidies_bullets: int = 100; squidies_grenades: int = 20; squidies_missile_launcher: int = 2; squidies_missiles: int = 10; day: int = 1; health: int = 30; steps: int = 0; max_steps: int = 7; current_score: int = 0; current_location: str = "city"; lives: int = 3; damage: int = 0; drugs: Drugs = field(default_factory=Drugs); weapons: Weapons = field(default_factory=Weapons); drug_prices: Dict[str, int] = field(default_factory=dict); flags: Flags = field(default_factory=Flags)
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
    raw_data['flags'] = Flags(**filter_keys(Flags, raw_data.get('flags', {})))
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
        
    save_game_state(gs)
    return defeated, enemy_hp, log, dead

# ============
# Configuration Data
# ============
weapon_prices_config = load_json('weapon_prices.json', {"weapons": {}})
rooms_config = load_json(ROOMS_FILE, {"rooms": {"entrance": {"title": "Street Entrance", "description": "A dark alleyway leading to the city.", "exits": {"north": "city"}}}})
npcs_data = load_json(NPCS_FILE, {})
npcs_dialogues = load_json('npc_dialogues.json', {})

def generate_random_room(current_rid):
    return "secret_room_" + str(random.randint(1, 100))

def get_npcs_in_room(room_id):
    """Get all NPCs and bots currently in a specific room."""
    npcs_in_room = []
    
    # Check NPCs from npcs.json
    for npc_id, npc in npcs_data.items():
        if npc.get('location') == room_id and npc.get('is_alive', True):
            npc_copy = npc.copy()
            npc_copy['id'] = npc_id
            npcs_in_room.append(npc_copy)
    
    # Check bots from bots.json
    bots = load_json(BOTS_FILE, [])
    for bot in bots:
        if bot.get('location') == room_id:
            bot_copy = bot.copy()
            bot_copy['id'] = bot['name'].lower().replace(' ', '_')
            bot_copy['name'] = bot['name']
            bot_copy['personality'] = bot.get('chat_personality', 'neutral')
            bot_copy['is_alive'] = True
            bot_copy['type'] = 'bot'
            npcs_in_room.append(bot_copy)
    
    return npcs_in_room

def get_room_npcs(room_id):
    """Alias for get_npcs_in_room for backwards compatibility."""
    return get_npcs_in_room(room_id)

# ============
# NPC Dialogue System
# ============

def get_npc_dialogue_topics(npc_id):
    """Get available dialogue topics for an NPC."""
    if npc_id in npcs_dialogues:
        return list(npcs_dialogues[npc_id].get('topics', {}).keys())
    return []

def get_npc_greeting(npc_id):
    """Get a greeting from an NPC."""
    if npc_id in npcs_dialogues:
        greetings = npcs_dialogues[npc_id].get('greetings', ["Hello."])
        return random.choice(greetings)
    return "Hello."

def get_npc_dialogue_response(npc_id, topic, player_data):
    """Get a dialogue response from an NPC."""
    if npc_id not in npcs_dialogues:
        return {"text": "I don't know who you're talking to.", "cost": 0, "effect": None}
    
    npc_data = npcs_dialogues[npc_id]
    if topic not in npc_data.get('topics', {}):
        return {"text": "I don't have anything to say about that.", "cost": 0, "effect": None}
    
    topic_data = npc_data['topics'][topic]
    responses = topic_data.get('responses', [])
    if not responses:
        return {"text": "I have nothing to say.", "cost": 0, "effect": None}
    
    # Simple response selection - could be enhanced with evolution system
    response = random.choice(responses)
    return response

# ============
# War System
# ============

def check_npc_war_declaration(gs):
    """Check if any NPCs want to declare war on the player."""
    wars = []
    npcs = load_json(NPCS_FILE, {})
    
    for npc_id, npc in npcs.items():
        if not npc.get('is_alive', True):
            continue
        
        # Check if NPC is in same location as player
        if npc.get('location') != gs.current_location:
            continue
        
        # Check relationship - hostile NPCs may declare war
        evolution = npc.get('evolution', {})
        relationships = evolution.get('relationships', {})
        player_rel = relationships.get('player', 0)
        
        # Hostile or enemy NPCs have a chance to declare war
        if player_rel <= -30:  # hostile or worse
            if random.random() < 0.15:  # 15% chance when in same room
                wars.append({
                    'npc_id': npc_id,
                    'npc_name': npc['name'],
                    'reason': 'They want you out of their territory!',
                    'power': evolution.get('power_level', 100)
                })
    
    return wars

def process_war_declaration(attacker_name, defender_gs):
    """Process a war declaration - instant combat."""
    # Load attacker stats
    npcs = load_json(NPCS_FILE, {})
    attacker = None
    for npc_id, npc in npcs.items():
        if npc['name'] == attacker_name:
            attacker = npc
            break
    
    if not attacker:
        return {"success": False, "message": "Attacker not found!"}
    
    # Calculate combat
    attacker_hp = attacker.get('hp', 100)
    attacker_dmg = attacker.get('damage', 10)
    
    # Player combat
    player_dmg = random.randint(20, 40)
    if defender_gs.weapons.pistols > 0 and defender_gs.weapons.bullets > 0:
        defender_gs.weapons.bullets -= 1
        player_dmg = random.randint(50, 80)
    
    if defender_gs.members > 1:
        gang_dmg = random.randint(10, 20) * (defender_gs.members - 1)
        player_dmg += gang_dmg
    
    # Attacker takes damage
    attacker_hp -= player_dmg
    
    result = {
        "success": True,
        "attacker": attacker_name,
        "player_damage_dealt": player_dmg,
        "attacker_hp_remaining": max(0, attacker_hp),
        "log": [f"⚔️ WAR DECLARED! {attacker_name} attacks you!", f"You dealt {player_damage} damage!"]
    }
    
    if attacker_hp <= 0:
        # Player wins the war
        result["victory"] = True
        result["log"].append(f"🎉 VICTORY! You defeated {attacker_name}!")
        result["loot"] = random.randint(500, 2000)
        defender_gs.money += result["loot"]
        result["log"].append(f"Looted ${result['loot']} from the battlefield!")
        
        # Mark NPC as dead
        attacker['is_alive'] = False
        save_json(NPCS_FILE, npcs)
    else:
        # Attacker retaliates
        e_dmg = attacker_dmg
        if defender_gs.weapons.vest > 0:
            block = min(defender_gs.weapons.vest, e_dmg // 2)
            defender_gs.weapons.vest -= block
            e_dmg -= block
            result["log"].append(f"Vest absorbed {block} damage.")
        
        defender_gs.damage += e_dmg
        result["log"].append(f"{attacker_name} deals {e_dmg} damage!")
        result["victory"] = False
    
    save_game_state(defender_gs)
    return result

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
    return render_template('credits.html')

@app.route('/wander')
def wander():
    gs = get_game_state()
    gs.steps += 1
    simulate_bots(gs.current_location, gs.player_name)
    save_game_state(gs)
    
    # Check for NPC war declarations
    wars = check_npc_war_declaration(gs)
    if wars:
        war = wars[0]
        result = process_war_declaration(war['npc_name'], gs)
        if result.get('victory'):
            flash(f"⚔️ WAR DECLARED! {war['npc_name']} attacked you! You won! Looted ${result['loot']}!", "success")
        else:
            flash(f"⚔️ WAR DECLARED! {war['npc_name']} attacked you! You took damage!", "danger")
        return redirect(url_for('city'))
    
    # Random wander result
    events = load_json('wander_events.json', {"wander_messages": ["You wander the streets..."]})
    result = random.choice(events.get('wander_messages', ["Nothing happens."]))
    
    return render_template('wander_result.html', game_state=gs, result=result)

@app.route('/alleyway')
def alleyway():
    gs = get_game_state()
    gs.current_location = "alleyway"
    save_game_state(gs)
    
    # Get current room from session or default to entrance
    current_room_id = session.get('alleyway_room', 'entrance')
    current_room = rooms_config.get('rooms', {}).get(current_room_id, rooms_config.get('rooms', {}).get('entrance', {'title': 'Unknown', 'description': '', 'exits': {}}))
    
    # Get NPCs in this room
    room_npcs = get_npcs_in_room(current_room_id)
    
    # Check for NPC war declarations when entering a room
    wars = check_npc_war_declaration(gs)
    if wars:
        war = wars[0]
        result = process_war_declaration(war['npc_name'], gs)
        if result.get('victory'):
            flash(f"⚔️ WAR! {war['npc_name']} declared war! You defeated them! Looted ${result['loot']}!", "success")
        else:
            flash(f"⚔️ WAR! {war['npc_name']} declared war! You took {sum([int(e.split()[-2]) for e in result['log'] if 'damage' in e])} damage!", "danger")
        return redirect(url_for('alleyway'))
    
    return render_template('alleyway.html', game_state=gs, current_room=current_room, room_npcs=room_npcs)

@app.route('/move_room', methods=['POST'])
def move_room():
    direction = request.form.get('direction')
    gs = get_game_state()
    current_room_id = session.get('alleyway_room', 'entrance')
    current_room = rooms_config.get('rooms', {}).get(current_room_id, {})
    
    if direction and direction in current_room.get('exits', {}):
        new_room_id = current_room['exits'][direction]
        session['alleyway_room'] = new_room_id
        gs.steps += 1
        simulate_bots(gs.current_location, gs.player_name)
        if gs.steps >= gs.max_steps:
            gs.day += 1
            gs.steps = 0
            update_daily_prices()
        save_game_state(gs)
    
    return redirect(url_for('alleyway'))

@app.route('/search_room', methods=['POST'])
def search_room():
    gs = get_game_state()
    current_room_id = session.get('alleyway_room', 'entrance')
    
    # Search for NPCs/bosses in room
    npcs_in_room = get_npcs_in_room(current_room_id)
    boss = next((n for n in npcs_in_room if n.get('is_alive')), None)
    
    if boss:
        # Fight the boss
        session['fighting_boss'] = boss['id']
        return redirect(url_for('npc_interaction', npc_id=boss['id']))
    
    # Random search results
    roll = random.random()
    if roll < 0.15:
        new_rid = generate_random_room(current_room_id)
        session['alleyway_room'] = new_rid
        flash("You found a hidden passage to a new sector!", "success")
    elif roll < 0.3:
        amt = random.randint(500, 2000)
        gs.money += amt
        flash(f"Found a briefcase with ${amt:,}!", "success")
    elif roll < 0.45:
        drug = random.choice(gs.drugs.keys())
        setattr(gs.drugs, drug, getattr(gs.drugs, drug) + 5)
        flash(f"Found 5kg of {drug}!", "success")
    else:
        flash("Nothing but rats and rust.", "info")
    
    gs.steps += 1
    simulate_bots(gs.current_location, gs.player_name)
    if gs.steps >= gs.max_steps:
        gs.day += 1
        gs.steps = 0
        update_daily_prices()
    save_game_state(gs)
    return redirect(url_for('alleyway'))

@app.route('/search_deeper', methods=['POST'])
def search_deeper():
    gs = get_game_state()
    gs.steps += 1
    simulate_bots(gs.current_location, gs.player_name)
    
    # Higher risk, higher reward
    roll = random.random()
    if roll < 0.3:
        amt = random.randint(2000, 5000)
        gs.money += amt
        flash(f"You found a major stash! ${amt:,}!", "success")
    elif roll < 0.5:
        drug = random.choice(gs.drugs.keys())
        setattr(gs.drugs, drug, getattr(gs.drugs, drug) + 15)
        flash(f"Jackpot! Found 15kg of {drug}!", "success")
    else:
        # Take damage from trap/guard
        dmg = random.randint(5, 15)
        gs.damage += dmg
        flash(f"Triggered a trap! Took {dmg} damage.", "danger")
    
    if gs.steps >= gs.max_steps:
        gs.day += 1
        gs.steps = 0
        update_daily_prices()
    save_game_state(gs)
    return redirect(url_for('alleyway'))

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

# ============
# NPC Routes
# ============

@app.route('/npcs')
def npcs():
    gs = get_game_state()
    room_npcs = get_npcs_in_room(gs.current_location)
    return render_template('npcs.html', game_state=gs, npcs=room_npcs)

@app.route('/talk_to_npc/<npc_id>')
def talk_to_npc(npc_id):
    gs = get_game_state()
    npc = npcs_data.get(npc_id, {})
    greeting = get_npc_greeting(npc_id)
    topics = get_npc_dialogue_topics(npc_id)
    return render_template('npc_dialogue.html', game_state=gs, npc=npc, greeting=greeting, topics=topics)

@app.route('/look_at_npc/<npc_id>')
def look_at_npc(npc_id):
    gs = get_game_state()
    npc = npcs_data.get(npc_id, {})
    return render_template('npc_interaction.html', game_state=gs, npc=npc, action='look', message=f"You look at {npc.get('name', 'the NPC')}.")

@app.route('/trade_with_npc/<npc_id>')
def trade_with_npc(npc_id):
    gs = get_game_state()
    npc = npcs_data.get(npc_id, {})
    return render_template('npc_trade.html', game_state=gs, npc=npc, error=None)

@app.route('/npc_interaction/<npc_id>')
def npc_interaction(npc_id):
    gs = get_game_state()
    npc = npcs_data.get(npc_id, {})
    return render_template('npc_interaction.html', game_state=gs, npc=npc, action='talk', message=f"You encounter {npc.get('name', 'someone')}...")

@app.route('/npc_dialogue/<npc_id>')
def npc_dialogue(npc_id):
    gs = get_game_state()
    npc = npcs_data.get(npc_id, {})
    greeting = get_npc_greeting(npc_id)
    topics = get_npc_dialogue_topics(npc_id)
    return render_template('npc_dialogue.html', game_state=gs, npc=npc, greeting=greeting, topics=topics)

@app.route('/npc_dialogue_topic/<npc_id>/<topic>')
def npc_dialogue_topic(npc_id, topic):
    gs = get_game_state()
    npc = npcs_data.get(npc_id, {})
    return render_template('npc_dialogue_topic.html', game_state=gs, npc=npc, topic=topic, question=topic.replace('_', ' ').title())

@app.route('/npc_dialogue_respond', methods=['POST'])
def npc_dialogue_respond():
    npc_id = request.form.get('npc_id')
    topic = request.form.get('topic')
    gs = get_game_state()
    npc = npcs_data.get(npc_id, {})
    
    player_data = {
        "money": gs.money,
        "day": gs.day,
        "health": gs.health - gs.damage,
        "gang_members": [f"member{i}" for i in range(gs.members)],
        "name": gs.player_name
    }
    
    response = get_npc_dialogue_response(npc_id, topic, player_data)
    return render_template('npc_dialogue_response.html', game_state=gs, npc=npc, response=response.get('text', '...'))

@app.route('/npc_trade_action/<npc_id>', methods=['POST'])
def npc_trade_action(npc_id):
    gs = get_game_state()
    action = request.form.get('action')
    item_type = request.form.get('item_type')
    quantity = int(request.form.get('quantity', 1))
    npc = npcs_data.get(npc_id, {})
    
    price = gs.drug_prices.get(item_type, 1000)
    error = None
    
    if action == 'buy':
        total_cost = price * quantity * 1.5  # NPC markup
        if gs.money >= total_cost:
            gs.money -= total_cost
            setattr(gs.drugs, item_type, getattr(gs.drugs, item_type) + quantity)
        else:
            error = "Not enough money!"
    elif action == 'sell':
        if getattr(gs.drugs, item_type, 0) >= quantity:
            total_value = price * quantity * 0.5  # NPC underpays
            gs.money += total_value
            setattr(gs.drugs, item_type, getattr(gs.drugs, item_type) - quantity)
        else:
            error = "You don't have enough!"
    
    save_game_state(gs)
    return render_template('npc_trade.html', game_state=gs, npc=npc, error=error)

@app.route('/fight_npc/<npc_id>', methods=['POST'])
def fight_npc(npc_id):
    gs = get_game_state()
    weapon = request.form.get('weapon', 'fists')
    npc = npcs_data.get(npc_id, {})
    
    if not npc.get('is_alive', True):
        return redirect(url_for('npc_interaction', npc_id=npc_id))
    
    # Combat
    npc_hp = npc.get('hp', 100)
    npc_dmg = npc.get('damage', 10)
    
    # Player attacks
    if weapon == 'pistol' and gs.weapons.bullets > 0:
        gs.weapons.bullets -= 1
        player_dmg = random.randint(40, 70)
    elif weapon == 'ar15' and gs.weapons.bullets >= 3:
        gs.weapons.bullets -= 3
        player_dmg = random.randint(80, 130)
    elif weapon == 'knife':
        player_dmg = random.randint(25, 45)
    else:
        player_dmg = random.randint(10, 25)
    
    if gs.members > 1:
        gang_dmg = random.randint(10, 20) * (gs.members - 1)
        player_dmg += gang_dmg
    
    npc_hp -= player_dmg
    
    result = {"log": [f"You attack {npc['name']} with {weapon} for {player_dmg} damage!"]}
    
    if npc_hp <= 0:
        # Victory
        npc['is_alive'] = False
        save_json(NPCS_FILE, npcs_data)
        loot = random.randint(100, 500)
        gs.money += loot
        result["victory"] = True
        result["log"].append(f"🎉 VICTORY! {npc['name']} defeated!")
        result["log"].append(f"Looted ${loot}!")
        save_game_state(gs)
        return render_template('npc_interaction.html', game_state=gs, npc=npc, action='fight', 
                           message=" | ".join(result["log"]))
    else:
        # NPC retaliates
        e_dmg = npc_dmg
        if gs.weapons.vest > 0:
            block = min(gs.weapons.vest, e_dmg // 2)
            gs.weapons.vest -= block
            e_dmg -= block
            result["log"].append(f"Vest absorbed {block} damage.")
        
        gs.damage += e_dmg
        result["log"].append(f"{npc['name']} retaliates for {e_dmg} damage!")
        result["victory"] = False
        
        if gs.damage >= 30:
            gs.lives -= 1
            gs.damage = 0
            gs.health = 30
            result["log"].append("YOU WERE KNOCKED OUT! Lost a life.")
        
        save_game_state(gs)
        return render_template('npc_interaction.html', game_state=gs, npc=npc, action='fight',
                           message=" | ".join(result["log"]))

@app.route('/attempt_flee_npc/<npc_id>')
def attempt_flee_npc(npc_id):
    gs = get_game_state()
    npc = npcs_data.get(npc_id, {})
    
    if random.random() < 0.5:
        message = "You successfully fled!"
        success = True
    else:
        e_dmg = random.randint(15, 30)
        gs.damage += e_dmg
        message = f"Flee failed! {npc['name']} attacks for {e_dmg} damage!"
        success = False
        
        if gs.damage >= 30:
            gs.lives -= 1
            gs.damage = 0
            gs.health = 30
            message += " YOU WERE KNOCKED OUT!"
        
        save_game_state(gs)
    
    return render_template('npc_interaction.html', game_state=gs, npc=npc, action='flee', message=message)

@app.route('/pickup_loot/<npc_id>')
def pickup_loot(npc_id):
    gs = get_game_state()
    npc = npcs_data.get(npc_id, {})
    
    if npc.get('is_alive', True):
        return redirect(url_for('npc_interaction', npc_id=npc_id))
    
    # Loot the body
    loot = random.randint(50, 200)
    gs.money += loot
    save_game_state(gs)
    
    return render_template('npc_interaction.html', game_state=gs, npc=npc, action='loot',
                       message=f"You searched the body and found ${loot}!")

# ============
# Shop Routes
# ============

@app.route('/buy_weapon', methods=['POST'])
def buy_weapon():
    gs = get_game_state()
    weapon_type = request.form.get('weapon_type')
    quantity = int(request.form.get('quantity', 1))
    
    prices = load_json('weapon_prices.json', {"weapons": {}}).get('weapons', {})
    weapon_info = prices.get(weapon_type, {})
    price = weapon_info.get('price', 1000)
    
    total_cost = price * quantity
    if gs.money >= total_cost:
        gs.money -= total_cost
        if hasattr(gs.weapons, weapon_type):
            setattr(gs.weapons, weapon_type, getattr(gs.weapons, weapon_type) + quantity)
        save_game_state(gs)
        flash(f"Purchased {quantity}x {weapon_type}!", "success")
    else:
        flash("Not enough money!", "danger")
    
    return redirect(url_for('gunshack'))

@app.route('/upgrade_weapon', methods=['POST'])
def upgrade_weapon():
    gs = get_game_state()
    weapon_type = request.form.get('weapon_type')
    
    if weapon_type == 'pistol' and gs.weapons.pistols > 0 and not gs.weapons.pistol_automatic:
        if gs.money >= 2000:
            gs.money -= 2000
            gs.weapons.pistol_automatic = True
            save_game_state(gs)
            flash("Pistol upgraded to automatic!", "success")
        else:
            flash("Need $2,000!", "danger")
    elif weapon_type == 'ghost_gun' and gs.weapons.ghost_guns > 0 and not gs.weapons.ghost_gun_automatic:
        if gs.money >= 2000:
            gs.money -= 2000
            gs.weapons.ghost_gun_automatic = True
            save_game_state(gs)
            flash("Ghost Gun upgraded to automatic!", "success")
        else:
            flash("Need $2,000!", "danger")
    
    return redirect(url_for('gunshack'))

@app.route('/bank_transaction', methods=['POST'])
def bank_transaction():
    gs = get_game_state()
    action = request.form.get('action')
    amount = int(request.form.get('amount', 0))
    
    if action == 'deposit':
        if gs.money >= amount:
            gs.money -= amount
            gs.account += amount
            flash(f"Deposited ${amount:,}!", "success")
    elif action == 'withdraw':
        if gs.account >= amount:
            gs.account -= amount
            gs.money += amount
            flash(f"Withdrew ${amount:,}!", "success")
    elif action == 'loan':
        gs.loan += amount
        gs.money += amount
        flash(f"Took out ${amount:,} loan!", "warning")
    elif action == 'pay_loan':
        if gs.money >= amount:
            gs.money -= amount
            gs.loan = max(0, gs.loan - amount)
            flash(f"Paid ${amount:,} toward loan!", "success")
    
    save_game_state(gs)
    return redirect(url_for('bank'))

@app.route('/picknsave_action', methods=['POST'])
def picknsave_action():
    gs = get_game_state()
    action = request.form.get('action')
    
    if action == 'buy_food':
        if gs.money >= 500:
            gs.money -= 500
            flash("Bought food supplies!", "success")
    elif action == 'buy_medical':
        if gs.money >= 1000:
            gs.money -= 1000
            gs.damage = max(0, gs.damage - 10)
            flash("Bought medical supplies! Healed 10 damage.", "success")
    elif action == 'buy_id':
        if gs.money >= 5000 and not gs.flags.has_id:
            gs.money -= 5000
            gs.flags.has_id = True
            flash("Bought fake ID! You're protected from ID checks.", "success")
    elif action == 'buy_info':
        if gs.money >= 2000:
            gs.money -= 2000
            gs.flags.has_info = True
            flash("Bought police intel!", "success")
    elif action == 'recruit':
        if gs.money >= 10000:
            gs.money -= 10000
            gs.members += 1
            flash("Recruited a new member!", "success")
    
    save_game_state(gs)
    return redirect(url_for('picknsave'))

@app.route('/search_picknsave', methods=['POST'])
def search_picknsave():
    gs = get_game_state()
    secrets = []
    benefits = []
    
    roll = random.random()
    if roll < 0.3:
        secrets.append("You found a ledger showing the store's illegal side business.")
        benefits.append("You can now access bulk pricing")
    elif roll < 0.6:
        secrets.append("You overheard the owner talking about a shipment coming in.")
        benefits.append("Market prices will be revealed")
    else:
        secrets.append("Nothing suspicious found... this time.")
    
    return render_template('search_picknsave.html', game_state=gs, secrets=secrets, benefits=benefits)

@app.route('/bulk_purchase', methods=['POST'])
def bulk_purchase():
    gs = get_game_state()
    drug_type = request.form.get('drug_type')
    quantity = int(request.form.get('quantity', 10))
    
    price = gs.drug_prices.get(drug_type, 1000)
    total = price * quantity * 0.8  # 20% bulk discount
    
    if gs.money >= total:
        gs.money -= int(total)
        setattr(gs.drugs, drug_type, getattr(gs.drugs, drug_type) + quantity)
        save_game_state(gs)
        flash(f"Bought {quantity}kg of {drug_type} for ${int(total):,}!", "success")
    else:
        flash("Not enough money!", "danger")
    
    return redirect(url_for('closet'))

@app.route('/closet')
def closet():
    gs = get_game_state()
    return render_template('closet.html', game_state=gs, message=None)

@app.route('/search_closet', methods=['POST'])
def search_closet():
    gs = get_game_state()
    gs.steps += 1
    
    roll = random.random()
    if roll < 0.4:
        amt = random.randint(1000, 3000)
        gs.money += amt
        message = f"Found ${amt:,} hidden in the closet!"
    elif roll < 0.7:
        drug = random.choice(gs.drugs.keys())
        qty = random.randint(5, 15)
        setattr(gs.drugs, drug, getattr(gs.drugs, drug) + qty)
        message = f"Found {qty}kg of {drug}!"
    else:
        message = "Nothing interesting in here."
    
    save_game_state(gs)
    return render_template('closet.html', game_state=gs, message=message)

# ============
# Encounter Routes
# ============

@app.route('/encounter')
def encounter():
    gs = get_game_state()
    encounter_type = random.choice(['squidies', 'baby_momma', 'discovery', 'drug_deal'])
    
    descriptions = {
        'squidies': 'You bump into some Squidies gang members! They look hostile.',
        'baby_momma': 'Your ex has spotted you and is demanding child support!',
        'discovery': 'You found something interesting!',
        'drug_deal': 'A shady dealer offers you a deal...'
    }
    
    return render_template('encounter.html', game_state=gs, 
                         encounter_type=encounter_type,
                         encounter_description=descriptions.get(encounter_type, 'Something happens...'),
                         encounter_context={'type': 'wander'})

@app.route('/handle_encounter', methods=['POST'])
def handle_encounter():
    gs = get_game_state()
    action = request.form.get('action')
    encounter_type = request.form.get('encounter_type')
    
    if action == 'fight':
        # Simple combat
        dmg = random.randint(20, 50)
        gs.damage += dmg
        if gs.damage >= 30:
            gs.lives -= 1
            gs.damage = 0
            gs.health = 30
            message = f"Fought and took {dmg} damage! Knocked out! Lost a life."
        else:
            message = f"Fought and took {dmg} damage!"
        loot = random.randint(100, 500)
        gs.money += loot
        message += f" Looted ${loot}!"
    elif action == 'run':
        if random.random() < 0.5:
            message = "Escaped successfully!"
        else:
            dmg = random.randint(20, 40)
            gs.damage += dmg
            message = f"Failed to escape! Took {dmg} damage!"
    elif action == 'sneak':
        if random.random() < 0.6:
            message = "Sneaked past successfully!"
        else:
            dmg = random.randint(10, 25)
            gs.damage += dmg
            message = f"Sneak failed! Took {dmg} damage!"
    elif action == 'trade':
        message = "Traded successfully!"
        gs.money += random.randint(200, 800)
    else:
        message = "You handled the situation."
    
    save_game_state(gs)
    return render_template('exploration_result.html', game_state=gs, result=message)

@app.route('/continue_activity')
def continue_activity():
    return redirect(url_for('wander'))

# ============
# War Routes
# ============

@app.route('/start_war', methods=['POST'])
def start_war():
    gs = get_game_state()
    # Final battle logic
    return render_template('gang_war.html', game_state=gs)

@app.route('/start_final_battle', methods=['POST'])
def start_final_battle():
    gs = get_game_state()
    # Simple final battle
    player_power = gs.members + gs.weapons.pistols + (gs.weapons.bullets // 10)
    enemy_power = gs.squidies
    
    if player_power > enemy_power:
        gs.money += 100000
        flash("🎉 VICTORY! You destroyed the Squidies and became king of the streets!", "success")
        return render_template('game_win.html', game_state=gs)
    else:
        gs.lives = 0
        save_game_state(gs)
        return render_template('game_loss.html', game_state=gs)

# ============
# Chat Routes
# ============

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

@app.route('/api/player/info')
def api_player_info():
    gs = get_game_state()
    return jsonify({"player_name": gs.player_name})

# ============
# High Scores
# ============

@app.route('/high_scores')
def high_scores():
    scores = load_json(HIGH_SCORES_FILE, [])
    return render_template('high_scores.html', game_state=get_game_state(), scores=scores)

# ============
# Game Over Routes
# ============

@app.route('/game_over')
def game_over():
    return render_template('game_over.html', game_state=get_game_state())

@app.route('/game_win')
def game_win():
    return render_template('game_win.html', game_state=get_game_state())

@app.route('/game_loss')
def game_loss():
    return render_template('game_loss.html', game_state=get_game_state())

# ============
# Misc Routes
# ============

@app.route('/prostitute_action', methods=['POST'])
def prostitute_action():
    gs = get_game_state()
    action = request.form.get('action')
    
    if action == 'quick_service' and gs.money >= 500:
        gs.money -= 500
        gs.damage = max(0, gs.damage - 5)
        flash("...", "info")
    elif action == 'vip_experience' and gs.money >= 2000:
        gs.money -= 2000
        gs.damage = 0
        flash("...", "info")
    elif action == 'recruit_hooker' and gs.money >= 5000:
        gs.money -= 5000
        gs.members += 1
        flash("Recruited!", "success")
    
    save_game_state(gs)
    return redirect(url_for('prostitutes'))

@app.route('/recruit_hooker/<hooker_name>', methods=['POST'])
def recruit_hooker(hooker_name):
    gs = get_game_state()
    if gs.money >= 5000:
        gs.money -= 5000
        gs.members += 1
        save_game_state(gs)
        flash(f"Recruited {hooker_name}!", "success")
    else:
        flash("Need $5,000!", "danger")
    return redirect(url_for('alleyway'))

@app.route('/visit_prostitutes')
def visit_prostitutes():
    gs = get_game_state()
    gs.current_location = "crackhouse"
    save_game_state(gs)
    return render_template('prostitutes.html', game_state=gs)

@app.route('/prostitutes')
def prostitutes():
    gs = get_game_state()
    return render_template('prostitutes.html', game_state=gs)

@app.route('/infobooth')
def infobooth():
    gs = get_game_state()
    return render_template('infobooth.html', game_state=gs)

@app.route('/fight_cops', methods=['POST'])
def fight_cops():
    gs = get_game_state()
    action = request.form.get('action')
    
    if action == 'shoot':
        if gs.weapons.bullets > 0:
            gs.weapons.bullets -= 1
            dmg = random.randint(30, 60)
            gs.damage += dmg
            flash(f"Shot at cops! Took {dmg} damage!", "warning")
    elif action == 'run':
        if random.random() < 0.4:
            flash("Escaped the cops!", "success")
        else:
            dmg = random.randint(20, 40)
            gs.damage += dmg
            flash(f"Can't escape! Took {dmg} damage!", "danger")
    
    if gs.damage >= 30:
        gs.lives -= 1
        gs.damage = 0
        gs.health = 30
        flash("Knocked out by cops! Lost a life.", "danger")
    
    save_game_state(gs)
    return redirect(url_for('city'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--port', type=int, default=6009)
    args = parser.parse_args(); app.run(debug=True, host='0.0.0.0', port=args.port)