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

# Suppress successful GET request logs (only show errors and warnings)
import logging
from werkzeug.serving import WSGIRequestHandler

class SuppressSuccessfulGETFilter(logging.Filter):
    def filter(self, record):
        # Suppress logs for successful GET requests (200 status)
        if 'GET' in record.getMessage() and ' 200 ' in record.getMessage():
            return False
        return True

# Apply filter to Werkzeug logger
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(SuppressSuccessfulGETFilter())

# ============
# Data Helpers
# ============

# Dynamic project path detection
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
MODEL_DIR = os.path.join(PROJECT_ROOT, "model")

def get_model_path(filename):
    """Returns the absolute path to a model file."""
    return os.path.join(MODEL_DIR, filename)

def load_json(filename, default=None):
    path = get_model_path(filename)
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        return default if default is not None else {}
    except Exception as e:
        print(f"Error loading {filename} from {path}: {e}")
        return default if default is not None else {}

def save_json(filename, data):
    path = get_model_path(filename)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {filename} to {path}: {e}")

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
    weed: int = 0; crack: int = 5; coke: int = 0; ice: int = 0; percs: int = 0; pixie_dust: int = 0; lean: int = 0; shrooms: int = 0; acid: int = 0; opium: int = 0; crystal_blue: int = 0; white_widow: int = 0; purple_haze: int = 0; fentanyl: int = 0; ketamine: int = 0; speed: int = 0; blue_dream: int = 0; red_devil: int = 0; white_china: int = 0; mdma_crystals: int = 0; moon_rocks: int = 0; blue_magic: int = 0; grey_death: int = 0; super_lemon_haze: int = 0
    def keys(self): 
        config = load_json('drug_config.json', {"drugs": {}})
        return list(config.get('drugs', {}).keys())

@dataclass
class Weapons:
    pistols: int = 0; bullets: int = 10; grenades: int = 0; vampire_bat: int = 0; missile_launcher: int = 0; missiles: int = 0; vest: int = 0; knife: int = 1; ghost_guns: int = 0; ar15: int = 0; exploding_bullets: int = 0; hollow_point_bullets: int = 0; sword: int = 0; axe: int = 0; golden_gun: int = 0; poison_blowgun: int = 0; chain_whip: int = 0; plasma_cutter: int = 0; flamethrower: int = 0; katana: int = 0; brass_knuckles: int = 0; uzi: int = 0; sawed_off_shotgun: int = 0; sniper_rifle: int = 0; molotov: int = 0; micro_smg: int = 0; grenade_launcher: int = 0; combat_knife: int = 0; pistol_automatic: bool = False; ghost_gun_automatic: bool = False

@dataclass
class GameState:
    player_name: str = ""; gang_name: str = ""; money: int = 1000; account: int = 0; loan: int = 0; loan_days: int = 0; members: int = 1; squidies: int = 25; day: int = 1; health: int = 30; steps: int = 0; max_steps: int = 7; current_score: int = 0; current_location: str = "city"; lives: int = 3; damage: int = 0; drugs: Drugs = field(default_factory=Drugs); weapons: Weapons = field(default_factory=Weapons); drug_prices: Dict[str, int] = field(default_factory=dict); flags: Dict[str, bool] = field(default_factory=lambda: {"eric_met": False, "steve_met": False, "has_id": False}); squidies_pistols: int = 50; squidies_bullets: int = 500; squidies_grenades: int = 20; squidies_missile_launcher: int = 5; squidies_missiles: int = 50
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

# Context processor for templates
@app.context_processor
def inject_globals():
    try:
        gs = get_game_state()
    except:
        gs = GameState()
    try:
        hs = get_high_scores()
    except:
        hs = []
    try:
        drug_config_data = load_json('drug_config.json', {"drugs": {}})
    except:
        drug_config_data = {"drugs": {}}
    try:
        top_list = get_top_list()
    except:
        top_list = []
    return dict(game_state=gs, high_scores=hs, drug_config=drug_config_data, top_list=top_list)

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
        # Format drug name for display (replace underscores with spaces)
        display_name = drug.replace('_', ' ').title()
        if roll < 0.05:
            event_multipliers[drug] = random.uniform(3.0, 6.0)
            alerts.append(f"POLICE RAIDS ON {display_name.upper()}!")
        elif roll < 0.10:
            event_multipliers[drug] = random.uniform(0.1, 0.3)
            alerts.append(f"MARKET FLOODED WITH {display_name.upper()}!")
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
        info = drug_config_data.get('drugs', {}).get(drug, {})
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

# Compatibility helpers
def load_current_drug_prices(): return get_current_prices()
def update_daily_prices(): return update_daily_market_events()

# ============
# High Scores
# ============

def get_high_scores():
    scores = load_json(HIGH_SCORES_FILE, [])
    if isinstance(scores, list):
        return scores
    return []

def add_high_score(gs):
    """Add high score and ensure player name is saved correctly"""
    if not gs.player_name or gs.player_name.strip() == "":
        return  # Don't save scores without player names
    
    scores = get_high_scores()
    new_score = {
        "player_name": gs.player_name.strip(),
        "gang_name": gs.gang_name.strip() if gs.gang_name else "No Gang",
        "score": gs.current_score,
        "money_earned": gs.money + gs.account,
        "days_survived": gs.day,
        "gang_wars_won": 0,
        "fights_won": 0,
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

def drop_drugs_on_death(bot, player_loc=None):
    """Drop drugs when a bot dies/gets knocked out"""
    drug_config_data = load_json('drug_config.json', {"drugs": {}})
    drug_list = list(drug_config_data.get('drugs', {}).keys())
    
    # Drop all drugs the bot was carrying
    dropped_drugs = []
    for drug in drug_list:
        qty = bot.get('drugs', {}).get(drug, 0)
        if qty > 0:
            dropped_drugs.append(f"{qty} {drug}")
            # Add to market supply (drugs are now available in the area)
            modify_market_supply(drug, qty)
            bot['drugs'][drug] = 0
    
    # Announce the drop if player is in the same room
    if dropped_drugs and bot.get('current_room') == player_loc:
        add_chat_message("SYSTEM", f"💀 {bot['name']} was knocked out! Dropped: {', '.join(dropped_drugs)}")
    
    return dropped_drugs

def simulate_bots(player_loc=None, player_name=None):
    global BOT_CHALLENGE
    bots = load_json(BOTS_FILE, [])
    prices_info = get_current_prices()
    prices = prices_info['prices']
    drug_config_data = load_json('drug_config.json', {"drugs": {}, "drug_effects": {}})
    drug_list = list(drug_config_data.get('drugs', {}).keys())
    drug_effects = drug_config_data.get('drug_effects', {})
    
    # Load all available rooms from rooms_config
    rooms_config_data = load_json(ROOMS_FILE, {"rooms": {}})
    all_rooms = list(rooms_config_data.get('rooms', {}).keys())
    
    # Define allowed rooms for bots (wandering streets and dark alleyway areas)
    allowed_bot_rooms = [
        "entrance", "dead_end", "side_street", "dumpster", "hidden_entrance",
        "underground", "secret_room", "abandoned_lot", "burned_out_car",
        "construction_site", "alley_graffiti_wall", "overgrown_garden",
        "flooded_chamber", "alley_fight_club", "mysterious_door", "ancient_vault",
        "speakeasy", "rooftop_access", "rooftop_garden", "abandoned_roof_deck",
        "rooftop_hideout", "penthouse_ruins", "makeshift_bridge", "rooftop_observatory",
        "neighboring_roof", "emergency_stairwell", "service_elevator", "maintenance_tunnel",
        "basement_storage", "utility_room", "sewer_access", "forgotten_archive",
        "boiler_room", "sewer_main_line", "coal_storage", "sewer_junction",
        "underground_stream", "storm_drain", "maintenance_shaft", "crystal_cave",
        "drainage_basin", "street_level_access", "gang_hideout", "forgotten_laboratory",
        "buried_vault", "sewage_treatment_chamber", "abandoned_warehouse",
        "loading_dock", "warehouse_office", "industrial_yard", "catwalk",
        "junkyard_office", "roof_access", "scale_house", "water_tower",
        "weigh_station", "maintenance_ladder", "ground_level", "perimeter_fence",
        "chain_lair", "tech_sanctum"
    ]
    
    # Bot drug limits to prevent unlimited accumulation
    MAX_DRUGS_PER_TYPE = 15  # Maximum of 15 units of any single drug
    MAX_TOTAL_DRUGS = 30     # Maximum total drugs across all types
    
    for b in bots:
        roll = random.random()
        
        # Bot movement - can explore everywhere but stays in wandering/street areas
        if roll < 0.20:
            # Move to a random allowed room
            if allowed_bot_rooms:
                new_room = random.choice(allowed_bot_rooms)
                b['location'] = new_room
                b['current_room'] = new_room
        
        # Bot drug usage - bots occasionally take drugs
        elif roll < 0.35 and drug_list and drug_effects:
            # Bot takes a drug they have
            available_drugs = [d for d in drug_list if b.get('drugs', {}).get(d, 0) > 0]
            if available_drugs and random.random() < 0.3:  # 30% chance to use if they have drugs
                drug = random.choice(available_drugs)
                b['drugs'][drug] -= 1
                effect = drug_effects.get(drug, {})
                
                # Apply drug effects to bot
                if 'heal_amount' in effect:
                    b['health'] = b.get('health', 100) + effect['heal_amount']
                if 'damage' in effect:
                    b['health'] = b.get('health', 100) - effect['damage']
                
                # Check if bot died from drug damage
                if b.get('health', 100) <= 0:
                    drop_drugs_on_death(b, player_loc)
                    # Respawn bot after a short delay (reset health and move to random room)
                    b['health'] = 100
                    if allowed_bot_rooms:
                        new_room = random.choice(allowed_bot_rooms)
                        b['location'] = new_room
                        b['current_room'] = new_room
                else:
                    # Announce if player is in same room
                    if b.get('current_room') == player_loc:
                        add_chat_message(b['name'], effect.get('message', f"Used {drug}."))
        
        # Bot trading activities
        elif roll < 0.60 and drug_list:
            d = random.choice(drug_list)
            p = prices.get(d, 1000)
            
            # Calculate current drug totals
            bot_drugs = b.get('drugs', {})
            current_qty = bot_drugs.get(d, 0)
            total_drugs = sum(bot_drugs.values())
            
            # Bot buying drugs - with limits
            if random.random() < 0.4 and b.get('money', 0) > p * 10:
                # Check if bot can carry more
                if current_qty < MAX_DRUGS_PER_TYPE and total_drugs < MAX_TOTAL_DRUGS:
                    # Calculate how much they can actually buy
                    max_can_buy = min(
                        int(b.get('money', 0) / p),  # Limited by money
                        MAX_DRUGS_PER_TYPE - current_qty,  # Limited by per-type cap
                        MAX_TOTAL_DRUGS - total_drugs  # Limited by total cap
                    )
                    qty = min(random.randint(2, 10), max_can_buy)
                    
                    if qty > 0:
                        b['money'] -= qty * p
                        b['drugs'][d] = current_qty + qty
                        modify_market_supply(d, -qty)
                        # Global alert for significant drug deals
                        if qty >= 5 and random.random() < 0.3:
                            add_chat_message("SYSTEM", f"📢 {b['name']} secured a batch of {qty} {d} in the streets!")
            
            # Bot selling drugs
            elif current_qty > 0:
                qty = current_qty
                b['money'] += qty * p
                b['drugs'][d] = 0
                modify_market_supply(d, qty)
                # Global alert for significant sales
                if qty >= 5 and random.random() < 0.4:
                    add_chat_message("SYSTEM", f"💰 {b['name']} unloaded {qty} {d.upper()} on the black market!")
        
        # Bot challenges/interactions
        elif roll < 0.85:
            if b.get('current_room') == player_loc and player_name and not BOT_CHALLENGE:
                BOT_CHALLENGE = b['name']
                add_chat_message(b['name'], f"Yo {player_name}, this is MY turf! Get out or get smoked!")
        
        # Bot-initiated trading with player (rare)
        elif roll < 0.90 and drug_list:
            # Bot tries to trade with player if in same room
            if b.get('current_room') == player_loc and player_name:
                # Bot has drugs to sell or wants to buy
                bot_drugs = b.get('drugs', {})
                available_to_sell = {d: qty for d, qty in bot_drugs.items() if qty > 0}
                
                if available_to_sell and random.random() < 0.2:  # 20% chance to offer trade
                    drug_to_sell = random.choice(list(available_to_sell.keys()))
                    qty = min(available_to_sell[drug_to_sell], random.randint(1, 3))
                    price = prices.get(drug_to_sell, 1000)
                    
                    # Store trade offer in bot data
                    b['trade_offer'] = {
                        'drug': drug_to_sell,
                        'quantity': qty,
                        'price': price,
                        'action': 'sell',  # Bot is selling to player
                        'timestamp': time.time()
                    }
                    
                    add_chat_message(b['name'], f"🤝 Hey {player_name}, I got {qty} {drug_to_sell} for ${price * qty}. Type '/trade {b['name']}' to buy!")
    
    save_json(BOTS_FILE, bots)

def load_bots(): return load_json(BOTS_FILE, [])

def get_who_list():
    gs = get_game_state()
    online = [{"name": gs.player_name, "type": "Player", "loc": gs.current_location}]
    bots = load_bots()
    for b in bots:
        online.append({"name": b['name'], "type": "Bot", "loc": b.get('current_room', b.get('location', 'city'))})
    return online

def get_top_list():
    bots = load_bots()
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
        if dead: add_high_score(gs)
        
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
    return render_template('index.html')

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
    return render_template('city.html', city_alert=prices_data.get('fluctuation_alert', ""))

@app.route('/crackhouse')
def crackhouse():
    gs = get_game_state(); gs.current_location = "crackhouse"; save_game_state(gs)
    return render_template('crackhouse.html')

@app.route('/gunshack')
def gunshack():
    gs = get_game_state(); gs.current_location = "gunshack"; save_game_state(gs)
    return render_template('gunshack.html')

@app.route('/bar')
def bar():
    gs = get_game_state(); gs.current_location = "bar"; save_game_state(gs)
    return render_template('bar.html')

@app.route('/bank')
def bank():
    gs = get_game_state(); gs.current_location = "bank"; save_game_state(gs)
    return render_template('bank.html')

@app.route('/picknsave')
def picknsave():
    gs = get_game_state(); gs.current_location = "picknsave"; save_game_state(gs)
    return render_template('picknsave.html')

@app.route('/credits')
def credits():
    hs = get_high_scores()
    return render_template('credits.html', high_scores=hs)

@app.route('/high_scores')
def high_scores():
    hs = get_high_scores()
    return render_template('high_scores.html', high_scores=hs)

@app.route('/wander')
def wander():
    gs = get_game_state()
    gs.steps += 1
    
    # Generate random exploration events
    events = []
    roll = random.random()
    
    if roll < 0.3:
        # Find money
        found_money = random.randint(50, 200)
        gs.money += found_money
        events.append(f"You found ${found_money} on the ground!")
    elif roll < 0.5:
        # Random encounter with bot
        simulate_bots(gs.current_location, gs.player_name)
        bots = load_bots()
        room_bots = [b for b in bots if b.get('current_room') == gs.current_location]
        if room_bots:
            bot = random.choice(room_bots)
            events.append(f"You bump into {bot['name']} on the streets.")
    elif roll < 0.6:
        # Drug deal opportunity
        drug_config_data = load_json('drug_config.json', {"drugs": {}})
        drug_list = list(drug_config_data.get('drugs', {}).keys())
        if drug_list:
            drug = random.choice(drug_list)
            qty = random.randint(1, 3)
            price = get_current_prices().get('prices', {}).get(drug, 1000)
            if gs.money >= price * qty:
                gs.money -= price * qty
                setattr(gs.drugs, drug, getattr(gs.drugs, drug) + qty)
                events.append(f"A street dealer offers you {qty} {drug} for ${price * qty}. You take the deal.")
    
    save_game_state(gs)
    result = " ".join(events) if events else "You wander around the city without incident."
    return render_template('wander_result.html', result=result)

@app.route('/alleyway')
def alleyway():
    gs = get_game_state(); gs.current_location = "alleyway"; save_game_state(gs)
    
    # Initialize session room if not set
    if 'current_room' not in session:
        session['current_room'] = 'entrance'
    
    # Get current room from session
    current_room_id = session.get('current_room', 'entrance')
    current_room = rooms_config['rooms'].get(current_room_id, rooms_config['rooms'].get('entrance'))
    
    # Simulate bots for this room to ensure they appear
    simulate_bots(current_room_id, gs.player_name)
    
    return render_template('alleyway.html', current_room=current_room)

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/final_battle')
def final_battle():
    return render_template('final_battle.html')

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
    gs = get_game_state()
    # Get room from request parameter or fall back to player's current location
    player_room = request.args.get('room', gs.current_location)
    
    # Filter messages to only show those from the same room
    # Messages from bots include their current_room in the message data
    room_messages = []
    for msg in CHAT_MESSAGES:
        # Always include player messages and system messages
        if msg['player'] == gs.player_name or msg['player'] == 'SYSTEM':
            room_messages.append(msg)
        else:
            # For bot messages, check if bot is in the same room
            bots = load_bots()
            bot = next((b for b in bots if b['name'] == msg['player']), None)
            if bot and bot.get('current_room') == player_room:
                room_messages.append(msg)
    
    return jsonify({"messages": room_messages})

@app.route('/api/chat/send', methods=['POST'])
def api_send_chat():
    data = request.get_json(); player = data.get('player_name', 'Anonymous'); msg = data.get('message', '').strip()
    if not msg: return jsonify({"error": "Empty"}), 400
    if msg.startswith('/'):
        cmd_parts = msg[1:].lower().split()
        cmd = cmd_parts[0]
        if cmd == 'who':
            who = [get_game_state().player_name] + [b['name'] for b in load_bots()]
            add_chat_message("SYSTEM", f"Online: {', '.join(filter(None, who))}")
        elif cmd == 'top':
            all_p = get_top_list()
            add_chat_message("SYSTEM", f"Top: {' | '.join([f'{p['name']} ({p['score']})' for p in all_p[:5]])}")
        elif cmd == 'trade' and len(cmd_parts) >= 2:
            # Handle bot trade: /trade <bot_name> [accept/decline]
            bot_name = ' '.join(cmd_parts[1:])
            bots = load_bots()
            bot = next((b for b in bots if b['name'].lower() == bot_name.lower()), None)
            
            if not bot:
                add_chat_message("SYSTEM", f"Bot '{bot_name}' not found.")
            elif bot.get('current_room') != get_game_state().current_location:
                add_chat_message("SYSTEM", f"{bot_name} is not in your room.")
            elif 'trade_offer' not in bot:
                add_chat_message("SYSTEM", f"{bot_name} has no trade offer.")
            else:
                # Execute the trade
                offer = bot['trade_offer']
                gs = get_game_state()
                drug_type = offer['drug']
                qty = offer['quantity']
                price = offer['price']
                
                if gs.money >= price * qty:
                    gs.money -= price * qty
                    setattr(gs.drugs, drug_type, getattr(gs.drugs, drug_type) + qty)
                    bot['money'] = bot.get('money', 0) + price * qty
                    bot['drugs'][drug_type] -= qty
                    save_game_state(gs)
                    add_chat_message("SYSTEM", f"✅ Trade complete! Bought {qty} {drug_type} from {bot_name} for ${price * qty}")
                    del bot['trade_offer']
                else:
                    add_chat_message("SYSTEM", f"❌ Not enough money! Need ${price * qty}")
        return jsonify({"success": True})
    return jsonify({"success": True, "msg": add_chat_message(player, msg)})

@app.route('/api/chat/users')
def api_get_chat_users():
    """Get list of users (bots and player) in the same room"""
    gs = get_game_state()
    player_room = request.args.get('room', gs.current_location)
    
    # Only show users in wandering/street/alleyway rooms
    wandering_rooms = [
        "entrance", "dead_end", "side_street", "dumpster", "hidden_entrance",
        "underground", "secret_room", "abandoned_lot", "burned_out_car",
        "construction_site", "alley_graffiti_wall", "overgrown_garden",
        "flooded_chamber", "alley_fight_club", "mysterious_door", "ancient_vault",
        "speakeasy", "rooftop_access", "rooftop_garden", "abandoned_roof_deck",
        "rooftop_hideout", "penthouse_ruins", "makeshift_bridge", "rooftop_observatory",
        "neighboring_roof", "emergency_stairwell", "service_elevator", "maintenance_tunnel",
        "basement_storage", "utility_room", "sewer_access", "forgotten_archive",
        "boiler_room", "sewer_main_line", "coal_storage", "sewer_junction",
        "underground_stream", "storm_drain", "maintenance_shaft", "crystal_cave",
        "drainage_basin", "street_level_access", "gang_hideout", "forgotten_laboratory",
        "buried_vault", "sewage_treatment_chamber", "abandoned_warehouse",
        "loading_dock", "warehouse_office", "industrial_yard", "catwalk",
        "junkyard_office", "roof_access", "scale_house", "water_tower",
        "weigh_station", "maintenance_ladder", "ground_level", "perimeter_fence",
        "chain_lair", "tech_sanctum", "alleyway"
    ]
    
    # Only return users if we're in a wandering/street room
    if player_room not in wandering_rooms:
        return jsonify({"users": []})
    
    users = []
    
    # Add player
    users.append({
        "name": gs.player_name,
        "type": "Player",
        "room": player_room
    })
    
    # Add bots in the same room
    bots = load_bots()
    for b in bots:
        if b.get('current_room') == player_room:
            users.append({
                "name": b['name'],
                "type": "Bot",
                "room": b.get('current_room', '')
            })
    
    return jsonify({"users": users})

@app.route('/bot_trade', methods=['POST'])
def bot_trade():
    """Allow bots to rarely trade drugs with the player"""
    gs = get_game_state()
    bot_name = request.form.get('bot_name')
    action = request.form.get('action')  # 'buy' or 'sell'
    drug_type = request.form.get('drug_type')
    quantity = int(request.form.get('quantity', 1))
    
    bots = load_bots()
    bot = next((b for b in bots if b['name'] == bot_name), None)
    
    if not bot:
        return jsonify({"error": "Bot not found"}), 404
    
    # Check if bot and player are in the same room
    if bot.get('current_room') != gs.current_location:
        return jsonify({"error": "Bot is not in your room"}), 400
    
    prices = get_current_prices().get('prices', {})
    price = prices.get(drug_type, 1000)
    
    if action == 'buy':
        # Player buys from bot
        total_cost = price * quantity
        if gs.money >= total_cost and bot.get('drugs', {}).get(drug_type, 0) >= quantity:
            gs.money -= total_cost
            setattr(gs.drugs, drug_type, getattr(gs.drugs, drug_type) + quantity)
            bot['money'] = bot.get('money', 0) + total_cost
            bot['drugs'][drug_type] -= quantity
            save_game_state(gs)
            save_json(BOTS_FILE, bots)
            return jsonify({"success": True, "message": f"Bought {quantity} {drug_type} from {bot_name}"})
        else:
            return jsonify({"error": "Insufficient funds or bot doesn't have enough"}), 400
    
    elif action == 'sell':
        # Player sells to bot
        if getattr(gs.drugs, drug_type, 0) >= quantity and bot.get('money', 0) >= price * quantity:
            gs.money += price * quantity
            setattr(gs.drugs, drug_type, getattr(gs.drugs, drug_type) - quantity)
            bot['money'] -= price * quantity
            bot['drugs'][drug_type] = bot.get('drugs', {}).get(drug_type, 0) + quantity
            save_game_state(gs)
            save_json(BOTS_FILE, bots)
            return jsonify({"success": True, "message": f"Sold {quantity} {drug_type} to {bot_name}"})
        else:
            return jsonify({"error": "Insufficient drugs or bot doesn't have enough money"}), 400
    
    return jsonify({"error": "Invalid action"}), 400

# ============
# Missing Routes
# ============

@app.route('/prostitutes')
def visit_prostitutes():
    gs = get_game_state(); gs.current_location = "prostitutes"; save_game_state(gs)
    return render_template('prostitutes.html')

@app.route('/prostitute_action', methods=['POST'])
def prostitute_action():
    gs = get_game_state()
    action = request.form.get('action')
    if action == 'quick_service':
        if gs.money >= 200:
            gs.money -= 200; gs.damage = max(0, gs.damage - 5); save_game_state(gs)
    elif action == 'vip_experience':
        if gs.money >= 500:
            gs.money -= 500; gs.damage = max(0, gs.damage - 10); save_game_state(gs)
    elif action == 'recruit_hooker':
        if gs.money >= 1000:
            gs.money -= 1000; gs.members += 1; save_game_state(gs)
    return redirect(url_for('prostitutes'))

@app.route('/buy_weapon', methods=['POST'])
def buy_weapon():
    gs = get_game_state()
    weapon_type = request.form.get('weapon_type')
    quantity = int(request.form.get('quantity', 1))
    weapon_prices = {
        'pistol': 1200, 'ghost_gun': 600, 'bullets': 100, 'exploding_bullets': 2000,
        'hollow_point_bullets': 500, 'grenade': 1000, 'vampire_bat': 2500,
        'missile_launcher': 1000000, 'missile': 100000, 'ar15': 50000,
        'vest_light': 5000, 'vest_medium': 25000, 'vest_heavy': 35000
    }
    price = weapon_prices.get(weapon_type, 1000) * quantity
    if gs.money >= price:
        gs.money -= price
        if weapon_type == 'pistol': gs.weapons.pistols += quantity
        elif weapon_type == 'ghost_gun': gs.weapons.ghost_guns += quantity
        elif weapon_type == 'bullets': gs.weapons.bullets += quantity
        elif weapon_type == 'exploding_bullets': gs.weapons.exploding_bullets += quantity
        elif weapon_type == 'hollow_point_bullets': gs.weapons.hollow_point_bullets += quantity
        elif weapon_type == 'grenade': gs.weapons.grenades += quantity
        elif weapon_type == 'vampire_bat': gs.weapons.vampire_bat += quantity
        elif weapon_type == 'missile_launcher': gs.weapons.missile_launcher += quantity
        elif weapon_type == 'missile': gs.weapons.missiles += quantity
        elif weapon_type == 'ar15': gs.weapons.ar15 += quantity
        elif weapon_type == 'vest_light': gs.weapons.vest += 5
        elif weapon_type == 'vest_medium': gs.weapons.vest += 10
        elif weapon_type == 'vest_heavy': gs.weapons.vest += 15
        save_game_state(gs)
    return redirect(url_for('gunshack'))

@app.route('/upgrade_weapon', methods=['POST'])
def upgrade_weapon():
    gs = get_game_state()
    weapon_type = request.form.get('weapon_type')
    if weapon_type == 'pistol' and gs.money >= 2000 and gs.weapons.pistols > 0:
        gs.money -= 2000; gs.weapons.pistol_automatic = True; save_game_state(gs)
    elif weapon_type == 'ghost_gun' and gs.money >= 2000 and gs.weapons.ghost_guns > 0:
        gs.money -= 2000; gs.weapons.ghost_gun_automatic = True; save_game_state(gs)
    return redirect(url_for('gunshack'))

@app.route('/bank_transaction', methods=['POST'])
def bank_transaction():
    gs = get_game_state()
    action = request.form.get('action')
    amount = int(request.form.get('amount', 0))
    if action == 'deposit' and gs.money >= amount:
        gs.money -= amount; gs.account += amount; save_game_state(gs)
    elif action == 'withdraw' and gs.account >= amount:
        gs.account -= amount; gs.money += amount; save_game_state(gs)
    elif action == 'loan':
        gs.loan += amount; gs.money += amount; gs.loan_days = 0; save_game_state(gs)
    elif action == 'pay_loan' and gs.money >= amount and gs.loan > 0:
        gs.loan -= amount; gs.money -= amount; save_game_state(gs)
    return redirect(url_for('bank'))

@app.route('/fight_cops', methods=['POST'])
def fight_cops():
    gs = get_game_state()
    action = request.form.get('action')
    weapon = request.form.get('weapon')
    num_cops = int(request.form.get('num_cops', 1))
    
    if action == 'shoot':
        if weapon == 'pistol' and gs.weapons.bullets > 0:
            gs.weapons.bullets -= 1
            dmg = random.randint(35, 60)
            num_cops -= random.randint(1, 2)
        elif weapon == 'grenade' and gs.weapons.grenades > 0:
            gs.weapons.grenades -= 1
            dmg = 100; num_cops -= random.randint(2, 4)
        elif weapon == 'knife' and gs.weapons.knife > 0:
            dmg = random.randint(10, 20)
            num_cops -= 1
        else:
            dmg = 0
        
        if num_cops > 0:
            cop_dmg = random.randint(8, 15) * num_cops
            gs.damage += cop_dmg
        else:
            gs.money += random.randint(100, 500)
    
    elif action == 'run':
        if random.random() < 0.5:
            num_cops = 0
        else:
            gs.damage += random.randint(15, 30)
    
    if gs.damage >= 30:
        gs.lives -= 1; gs.damage = 0; gs.health = 30
    
    save_game_state(gs)
    return redirect(url_for('city'))

@app.route('/start_war', methods=['POST'])
def start_war():
    return render_template('gang_war.html')

@app.route('/start_final_battle', methods=['POST'])
def start_final_battle():
    return render_template('final_battle.html')

@app.route('/handle_encounter', methods=['POST'])
def handle_encounter():
    gs = get_game_state()
    encounter_type = request.form.get('encounter_type')
    # Simplified encounter handling
    save_game_state(gs)
    return redirect(url_for('city'))

@app.route('/move_room', methods=['POST'])
def move_room():
    direction = request.form.get('direction')
    gs = get_game_state()
    
    # Get current room from session or default to entrance
    current_room_id = session.get('current_room', 'entrance')
    current_room = rooms_config['rooms'].get(current_room_id, rooms_config['rooms'].get('entrance'))
    
    # Check if the direction is valid
    if direction in current_room.get('exits', {}):
        new_room_id = current_room['exits'][direction]
        new_room = rooms_config['rooms'].get(new_room_id)
        if new_room:
            session['current_room'] = new_room_id
            gs.steps += 1
            save_game_state(gs)
            return render_template('alleyway.html', current_room=new_room)
    
    # Invalid move, go back to current room
    save_game_state(gs)
    return redirect(url_for('alleyway'))

@app.route('/search_room')
def search_room():
    gs = get_game_state()
    session['secret_found'] = True
    save_game_state(gs)
    return redirect(url_for('alleyway'))

@app.route('/search_deeper')
def search_deeper():
    gs = get_game_state()
    gs.money += random.randint(50, 200)
    save_game_state(gs)
    return redirect(url_for('alleyway'))

@app.route('/bulk_purchase', methods=['POST'])
def bulk_purchase():
    gs = get_game_state()
    drug_type = request.form.get('drug_type')
    # Simplified bulk purchase
    save_game_state(gs)
    return redirect(url_for('closet'))

@app.route('/picknsave_action', methods=['POST'])
def picknsave_action():
    gs = get_game_state()
    action = request.form.get('action')
    if action == 'buy_food' and gs.money >= 500:
        gs.money -= 500; save_game_state(gs)
    elif action == 'buy_medical' and gs.money >= 1000:
        gs.money -= 1000; gs.damage = max(0, gs.damage - 10); save_game_state(gs)
    elif action == 'buy_id' and gs.money >= 5000:
        gs.money -= 5000; gs.flags.has_id = True; save_game_state(gs)
    elif action == 'buy_info' and gs.money >= 2000:
        gs.money -= 2000; save_game_state(gs)
    elif action == 'recruit' and gs.money >= 10000:
        gs.money -= 10000; gs.members += 1; save_game_state(gs)
    return redirect(url_for('picknsave'))

@app.route('/search_picknsave')
def search_picknsave():
    return render_template('search_picknsave.html')

@app.route('/fight_npc', methods=['POST'])
def fight_npc():
    npc_id = request.form.get('npc_id')
    return redirect(url_for('npc_interaction', npc_id=npc_id))

@app.route('/trade_with_npc', methods=['GET', 'POST'])
def trade_with_npc():
    npc_id = request.form.get('npc_id', request.args.get('npc_id', 'nox'))
    return render_template('npc_trade.html', npc_id=npc_id)

@app.route('/npc_interaction')
def npc_interaction():
    npc_id = request.args.get('npc_id', 'nox')
    return render_template('npc_interaction.html', npc_id=npc_id)

@app.route('/talk_to_npc')
def talk_to_npc():
    npc_id = request.args.get('npc_id', 'nox')
    return render_template('npc_dialogue.html', npc_id=npc_id)

@app.route('/look_at_npc')
def look_at_npc():
    npc_id = request.args.get('npc_id', 'nox')
    return render_template('npc_interaction.html', npc_id=npc_id)

@app.route('/npc_dialogue')
def npc_dialogue():
    npc_id = request.args.get('npc_id', 'nox')
    return render_template('npc_dialogue.html', npc_id=npc_id)

@app.route('/npc_dialogue_topic')
def npc_dialogue_topic():
    npc_id = request.args.get('npc_id', 'nox')
    topic = request.args.get('topic', 'general')
    return render_template('npc_dialogue_topic.html', npc_id=npc_id, topic=topic)

@app.route('/npc_dialogue_respond', methods=['POST'])
def npc_dialogue_respond():
    npc_id = request.form.get('npc_id', 'nox')
    topic = request.form.get('topic', 'general')
    return redirect(url_for('npc_dialogue_topic', npc_id=npc_id, topic=topic))

@app.route('/npc_trade_action', methods=['POST'])
def npc_trade_action():
    npc_id = request.form.get('npc_id', 'nox')
    return redirect(url_for('npc_trade', npc_id=npc_id))

@app.route('/continue_activity')
def continue_activity():
    return redirect(url_for('wander'))

@app.route('/closet')
def closet():
    return render_template('closet.html')

@app.route('/search_closet')
def search_closet():
    gs = get_game_state()
    gs.money += random.randint(10, 100)
    save_game_state(gs)
    return redirect(url_for('closet'))

@app.route('/npcs')
def npcs():
    return render_template('npcs.html')

@app.route('/recruit_hooker', methods=['POST'])
def recruit_hooker():
    hooker_name = request.form.get('hooker_name', 'Unknown')
    gs = get_game_state()
    if gs.money >= 1000:
        gs.money -= 1000
        gs.members += 1
        save_game_state(gs)
    return redirect(url_for('alleyway'))

@app.route('/pickup_loot')
def pickup_loot():
    npc_id = request.args.get('npc_id', 'nox')
    gs = get_game_state()
    gs.money += random.randint(50, 200)
    save_game_state(gs)
    return redirect(url_for('npc_interaction', npc_id=npc_id))

@app.route('/attempt_flee_npc')
def attempt_flee_npc():
    npc_id = request.args.get('npc_id', 'nox')
    if random.random() < 0.5:
        return redirect(url_for('city'))
    else:
        gs = get_game_state()
        gs.damage += random.randint(10, 20)
        save_game_state(gs)
        return redirect(url_for('npc_interaction', npc_id=npc_id))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--port', type=int, default=6009)
    args = parser.parse_args(); app.run(debug=True, host='0.0.0.0', port=args.port)
