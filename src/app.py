# Gangwar Master Engine - Integrated Production Build
import os
import time
import random
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

# ============
# Data Helpers
# ============
def load_json(filename, default=None):
    try:
        path = os.path.join(os.path.dirname(__file__), '..', 'model', filename)
        if os.path.exists(path):
            with open(path, 'r') as f: return json.load(f)
    except: pass
    return default if default is not None else {}

def save_json(filename, data):
    try:
        path = os.path.join(os.path.dirname(__file__), '..', 'model', filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f: json.dump(data, f, indent=2)
    except: pass

# File Paths
BOTS_FILE = 'bots.json'
MARKET_FILE = 'global_market.json'
PRICES_FILE = 'current_drug_prices.json'
PLAYER_FILE = 'player_state.json'
NPCS_FILE = 'npcs.json'
ROOMS_FILE = 'rooms_config.json'
HIGH_SCORES_FILE = 'high_scores.json'

# Global Configs
drug_config = load_json('drug_config.json', {"drugs": {}})
weapon_prices_config = load_json('weapon_prices.json', {"weapons": {}})
npcs_data = load_json('npcs.json', {})
rooms_config = load_json('rooms_config.json', {"rooms": {}})

# ============
# Market System
# ============
def modify_market_supply(drug, amount):
    market = load_json(MARKET_FILE, {d: 100 for d in drug_config.get('drugs', {})})
    market[drug] = max(0, market.get(drug, 100) + amount)
    save_json(MARKET_FILE, market)

def update_daily_market_events():
    event_multipliers = {}
    alerts = []
    for drug in drug_config.get('drugs', {}):
        roll = random.random()
        if roll < 0.05:
            event_multipliers[drug] = random.uniform(3.5, 7.0)
            alerts.append(f"POLICE RAID: {drug.upper()} SEIZED!")
        elif roll < 0.10:
            event_multipliers[drug] = random.uniform(0.1, 0.3)
            alerts.append(f"MARKET FLOODED: {drug.upper()} CHEAP!")
        else:
            event_multipliers[drug] = random.uniform(0.8, 1.2)
    res = {"event_multipliers": event_multipliers, "day": time.strftime("%Y-%m-%d"), "alert": " | ".join(alerts) if alerts else "Stable market."}
    save_json(PRICES_FILE, res)
    return res

def get_current_prices():
    prices_state = load_json(PRICES_FILE, {})
    if prices_state.get('day') != time.strftime("%Y-%m-%d"): prices_state = update_daily_market_events()
    market = load_json(MARKET_FILE, {d: 100 for d in drug_config.get('drugs', {})})
    
    dynamic_prices = {}
    for drug, info in drug_config['drugs'].items():
        supply_mult = min(5.0, max(0.2, 100.0 / max(1, market.get(drug, 100))))
        event_mult = prices_state.get('event_multipliers', {}).get(drug, 1.0)
        dynamic_prices[drug] = int(info['base_price'] * event_mult * supply_mult)
    
    return {"prices": dynamic_prices, "fluctuation_alert": prices_state.get('alert', "")}

def load_current_drug_prices(): return get_current_prices()

# ============
# Bot AI Syndicate
# ============
CHAT_MESSAGES = []
BOT_CHALLENGE = None

def add_chat_message(player, msg):
    m = {"player": player, "message": msg, "time": time.strftime("%H:%M")}
    CHAT_MESSAGES.append(m)
    if len(CHAT_MESSAGES) > 50: CHAT_MESSAGES.pop(0)
    return m

def simulate_bots(player_loc=None, player_name=None):
    global BOT_CHALLENGE
    bots = load_json(BOTS_FILE, [])
    prices = get_current_prices()['prices']
    for b in bots:
        roll = random.random()
        if roll < 0.25: b['location'] = random.choice(["city", "crackhouse", "bar", "bank", "alleyway", "gunshack", "picknsave"])
        elif roll < 0.6:
            drug = random.choice(list(drug_config['drugs'].keys()))
            p = prices.get(drug, 1000)
            if random.random() < 0.4 and b['money'] > p * 10:
                qty = random.randint(2, 12); b['money'] -= qty * p; b['drugs'][drug] = b['drugs'].get(drug, 0) + qty
                modify_market_supply(drug, -qty); add_chat_message(b['name'], f"Secured {qty}kg of {drug}.")
            elif b['drugs'].get(drug, 0) > 0:
                qty = b['drugs'][drug]; b['money'] += qty * p; b['drugs'][drug] = 0
                modify_market_supply(drug, qty); add_chat_message(b['name'], f"Unloaded {drug}. Stacking paper.")
        elif roll < 0.75:
            if b['money'] > 15000: b['money'] -= 10000; b['members'] += 1; add_chat_message(b['name'], "Expanded the syndicate.")
        elif roll < 0.85 and b['location'] == player_loc and player_name and not BOT_CHALLENGE:
            BOT_CHALLENGE = b['name']; add_chat_message(b['name'], f"Yo {player_name}, this is MY block! Step off!")
    save_json(BOTS_FILE, bots)

# ============
# Dataclasses & Persistence
# ============
@dataclass
class Drugs:
    weed: int=0; crack: int=0; coke: int=0; ice: int=0; percs: int=0; pixie_dust: int=0; lean: int=0; shrooms: int=0; acid: int=0; opium: int=0; crystal_blue: int=0; white_widow: int=0; purple_haze: int=0; fentanyl: int=0; ketamine: int=0; speed: int=0; blue_dream: int=0; red_devil: int=0; white_china: int=0; mdma_crystals: int=0; moon_rocks: int=0; blue_magic: int = 0; grey_death: int = 0; super_lemon_haze: int = 0
    def keys(self): return list(drug_config.get('drugs', {}).keys())

@dataclass
class Weapons:
    pistols: int=0; bullets: int=10; grenades: int=0; vampire_bat: int=0; missile_launcher: int=0; missiles: int=0; vest: int=0; knife: int=1; ghost_guns: int=0; ar15: int=0; sword: int=0; axe: int=0; golden_gun: int=0; poison_blowgun: int=0; chain_whip: int=0; plasma_cutter: int=0; flamethrower: int=0; katana: int=0; brass_knuckles: int=0; uzi: int=0; sawed_off_shotgun: int=0; sniper_rifle: int=0; molotov: int=0; micro_smg: int=0; grenade_launcher: int=0; combat_knife: int=0; pistol_automatic: bool=False; ghost_gun_automatic: bool=False

@dataclass
class GameState:
    player_name: str=""; gang_name: str=""; money: int=1000; account: int=0; loan: int=0; loan_days: int=0; members: int=1; day: int=1; health: int=30; steps: int=0; max_steps: int=7; current_score: int=0; current_location: str="city"; lives: int=3; damage: int=0; drugs: Drugs=field(default_factory=Drugs); weapons: Weapons=field(default_factory=Weapons); drug_prices: Dict[str, int]=field(default_factory=dict)
    @property
    def max_health(self) -> int: return 30 + 10 * (self.members - 1)

def get_game_state():
    d = load_json(PLAYER_FILE, asdict(GameState()))
    d['drugs'] = Drugs(**d.get('drugs', {}))
    w_data = d.get('weapons', {})
    d['weapons'] = Weapons(**w_data) if isinstance(w_data, dict) else Weapons()
    d['drug_prices'] = get_current_prices()['prices']
    return GameState(**d)

def save_game_state(gs):
    total = gs.money + gs.account
    gs.current_score = (total // 1000) + (gs.day * 100) + (gs.members * 50)
    save_json(PLAYER_FILE, asdict(gs))

def reset_game_state():
    path = os.path.join(os.path.dirname(__file__), '..', 'model', PLAYER_FILE)
    if os.path.exists(path): os.remove(path)
    return get_game_state()

def get_who_list():
    gs = get_game_state()
    res = [{"name": gs.player_name, "loc": gs.current_location, "type": "Player"}]
    for b in load_json(BOTS_FILE, []): res.append({"name": b['name'], "loc": b['location'], "type": "Bot"})
    return res

def get_top_list():
    res = []
    for hs in load_json(HIGH_SCORES_FILE, []): res.append({"name": hs.get('player_name'), "score": hs.get('score', 0)})
    for b in load_json(BOTS_FILE, []): res.append({"name": b['name'], "score": (b['money'] // 1000) + (b['members'] * 50)})
    gs = get_game_state()
    if gs.player_name: res.append({"name": gs.player_name, "score": gs.current_score})
    res.sort(key=lambda x: x['score'], reverse=True)
    return res[:10]

# ============
# Combat & Generation
# ============
def process_combat_action(gs, action, weapon, enemy_hp, enemy_type, enemy_count, is_boss=False):
    log = []
    if action == 'attack':
        dmg = random.randint(10, 20)
        if weapon == 'pistol' and gs.weapons.pistols > 0 and gs.weapons.bullets > 0: gs.weapons.bullets -= 1; dmg = random.randint(35, 60)
        elif weapon == 'ar15' and gs.weapons.ar15 > 0 and gs.weapons.bullets >= 3: gs.weapons.bullets -= 3; dmg = random.randint(70, 120)
        elif weapon == 'golden_gun' and gs.weapons.golden_gun > 0: dmg = random.randint(300, 750)
        elif weapon == 'katana' and gs.weapons.katana > 0: dmg = random.randint(60, 130)
        elif weapon == 'sawed_off_shotgun' and gs.weapons.sawed_off_shotgun > 0: dmg = random.randint(100, 190)
        
        if gs.members > 1:
            g_dmg = random.randint(10, 25) * (gs.members - 1); dmg += g_dmg; log.append(f"Gang fire support: +{g_dmg} damage!")
        enemy_hp -= dmg; log.append(f"You dealt {dmg} damage to {enemy_type}!")
        if enemy_hp > 0:
            e_dmg = random.randint(8, 20) * enemy_count
            if is_boss: e_dmg = int(e_dmg * 2.8)
            if gs.weapons.vest > 0: block = min(gs.weapons.vest, e_dmg // 2); gs.weapons.vest -= block; e_dmg -= block; log.append(f"Armor absorbed {block} damage.")
            gs.damage += e_dmg; log.append(f"{enemy_type} retaliates for {e_dmg} damage!")
    elif action == 'flee':
        if random.random() < 0.5: return True, enemy_hp, ["Escape successful!"], False
        else: e_dmg = random.randint(15, 35); gs.damage += e_dmg; log.append(f"Escape failed! Took {e_dmg} damage.")

    defeated = enemy_hp <= 0; dead = False
    if defeated:
        loot = random.randint(1000, 10000); gs.money += loot; log.append(f"VICTORY! Looted ${loot:,}.")
        if is_boss:
            for k, v in npcs_data.items():
                if v['name'] == enemy_type:
                    npcs_data[k]['is_alive'] = False
                    for d in v.get('unique_drops', []):
                        if hasattr(gs.weapons, d): setattr(gs.weapons, d, getattr(gs.weapons, d) + 1); log.append(f"ACQUIRED UNIQUE: {d.upper()}")
                        elif hasattr(gs.drugs, d): setattr(gs.drugs, d, getattr(gs.drugs, d) + 10); log.append(f"SEIZED 10kg {d.upper()}")
                    break
            save_json(NPCS_FILE, npcs_data)
    if gs.damage >= 30:
        gs.lives -= 1; gs.damage = 0; gs.health = 30; log.append("YOU WERE TAKEN OUT!"); dead = gs.lives <= 0
    save_game_state(gs); return defeated, enemy_hp, log, dead

def generate_random_room(prev_id):
    room_id = f"proc_{int(time.time())}_{random.randint(100, 999)}"
    new_room = {
        "title": random.choice(["Trap House", "Chem Lab", "Safehouse", "Secret Armory", "Smuggler's Cove"]),
        "description": "A fortified procedural sector smelling of narcotics and power.",
        "exits": {"south": prev_id}
    }
    if prev_id in rooms_config['rooms']: rooms_config['rooms'][prev_id]['exits']['north'] = room_id
    rooms_config['rooms'][room_id] = new_room
    save_json(ROOMS_FILE, rooms_config); return room_id
