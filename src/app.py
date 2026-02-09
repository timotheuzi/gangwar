# Check if running in PyInstaller bundle
import sys
import os
import time
import random
import json
import argparse
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this for production

# Check if running in PyInstaller bundle
is_frozen = getattr(sys, 'frozen', False)

# Load NPCs - look in model directory for data files
try:
    npc_file = os.path.join(os.path.dirname(__file__), '..', 'model', 'npcs.json')
    with open(npc_file, 'r') as f:
        npcs_data = json.load(f)
except FileNotFoundError:
    npcs_data = {}

# Load drug config
try:
    drug_config_file = os.path.join(os.path.dirname(__file__), '..', 'model', 'drug_config.json')
    with open(drug_config_file, 'r') as f:
        drug_config = json.load(f)
except FileNotFoundError:
    drug_config = {}
    print("DEBUG: drug_config file not found")

# Current drug prices file
CURRENT_DRUG_PRICES_FILE = os.path.join(os.path.dirname(__file__), '..', 'model', 'current_drug_prices.json')

def load_current_drug_prices():
    """Load current drug prices from file"""
    try:
        with open(CURRENT_DRUG_PRICES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        # Create default if file doesn't exist
        base_prices = {name: info['base_price'] for name, info in drug_config.get('drugs', {}).items()}
        return {
            "description": "Current day's fluctuating drug prices",
            "day": 1,
            "last_update": "",
            "prices": base_prices,
            "fluctuation_alert": "",
            "massive_change_drugs": []
        }

def save_current_drug_prices(current_prices):
    """Save current drug prices to file"""
    try:
        os.makedirs(os.path.dirname(CURRENT_DRUG_PRICES_FILE), exist_ok=True)
        with open(CURRENT_DRUG_PRICES_FILE, 'w') as f:
            json.dump(current_prices, f, indent=2)
    except Exception as e:
        print(f"Error saving current drug prices: {e}")

def update_daily_drug_prices():
    """Update drug prices for new day with fluctuations"""
    import time
    current_prices = load_current_drug_prices()

    # Load base prices for reference
    base_prices = {name: info['base_price'] for name, info in drug_config.get('drugs', {}).items()}

    # Fluctuation logic: sometimes skyrocket (busts/low inventory), sometimes plummet (flooded market)
    alerts = []
    massive_changes = []

    new_prices = {}
    for drug in base_prices.keys():
        # Base price as starting point
        price = base_prices[drug]

        # Random fluctuations: 70% normal variance, 20% big change, 10% massive change
        fluctuation_type = random.random()

        if fluctuation_type < 0.1:  # 10% chance of massive change
            # Massive change: 2-5x multiplier up or down
            if random.random() < 0.5:  # Busts → skyrocket
                multiplier = random.uniform(2.0, 5.0)
                alerts.append(f"MASSIVE BUSTS on {drug.upper()}! Prices through the roof!")
            else:  # Flooded market → plummet
                multiplier = random.uniform(0.2, 0.5)
                alerts.append(f"Market FLOODED with {drug.upper()}! Prices rock bottom!")
            massive_changes.append(drug)
        elif fluctuation_type < 0.3:  # 20% chance of big change
            if random.random() < 0.5:
                multiplier = random.uniform(1.5, 2.0)
            else:
                multiplier = random.uniform(0.5, 0.7)
        else:  # 70% normal variance
            multiplier = random.uniform(0.8, 1.3)

        new_prices[drug] = int(price * multiplier)

    # Update the file
    current_prices['prices'] = new_prices
    current_prices['fluctuation_alert'] = " | ".join(alerts[:2]) if alerts else ""  # Show up to 2 alerts
    current_prices['massive_change_drugs'] = massive_changes
    current_prices['last_update'] = time.strftime("%Y-%m-%d %H:%M:%S")

    save_current_drug_prices(current_prices)
    return current_prices

# ============
# High Scores
# ============

HIGH_SCORES_FILE = os.path.join(os.path.dirname(__file__), '..', 'model', 'high_scores.json')

@dataclass
class HighScore:
    player_name: str
    gang_name: str
    score: int
    money_earned: int
    days_survived: int
    gang_wars_won: int
    fights_won: int
    date_achieved: str

def load_high_scores() -> List[HighScore]:
    """Load high scores from file"""
    try:
        if os.path.exists(HIGH_SCORES_FILE):
            with open(HIGH_SCORES_FILE, 'r') as f:
                data = json.load(f)
                return [HighScore(**score) for score in data]
        else:
            # Create empty high scores file if it doesn't exist
            os.makedirs(os.path.dirname(HIGH_SCORES_FILE), exist_ok=True)
            with open(HIGH_SCORES_FILE, 'w') as f:
                json.dump([], f, indent=2)
            return []
    except Exception as e:
        print(f"Error loading high scores: {e}")
        # Create empty file on error too
        try:
            os.makedirs(os.path.dirname(HIGH_SCORES_FILE), exist_ok=True)
            with open(HIGH_SCORES_FILE, 'w') as f:
                json.dump([], f, indent=2)
        except:
            pass
        return []

def save_high_scores(scores: List[HighScore]):
    """Save high scores to file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(HIGH_SCORES_FILE), exist_ok=True)
        data = [asdict(score) for score in scores]
        with open(HIGH_SCORES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"High scores saved successfully with {len(scores)} entries")
    except Exception as e:
        print(f"Error saving high scores: {e}")

def calculate_score(money_earned: int, days_survived: int, gang_wars_won: int, fights_won: int) -> int:
    """Calculate total score based on achievements"""
    # Money earned contributes 1 point per $1000 (subtract starting money of $1000)
    money_score = max(0, (money_earned - 1000) // 1000)

    # Days survived contributes 100 points per day (subtract starting day 1)
    survival_score = max(0, (days_survived - 1) * 100)

    # Gang war victories contribute 1000 points each
    gang_war_score = gang_wars_won * 1000

    # Individual fights won contribute 50 points each
    fight_score = fights_won * 50

    return money_score + survival_score + gang_war_score + fight_score

# ============
# Polling-based Chat System (No WebSockets required!)
# ============

# In-memory message store (could be file-based for persistence)
chat_messages = []
chat_last_check = {}
CHAT_MAX_MESSAGES = 100

def add_chat_message(player_name, message):
    """Add a message to the chat"""
    import time
    msg = {
        'id': len(chat_messages) + 1,
        'player': player_name,
        'message': message,
        'timestamp': time.time(),
        'time_str': time.strftime('%H:%M:%S')
    }
    chat_messages.append(msg)
    
    # Keep only recent messages
    if len(chat_messages) > CHAT_MAX_MESSAGES:
        chat_messages.pop(0)
    
    # Update global last check timestamp
    chat_last_check['global'] = time.time()
    
    return msg

# ============
# Chat API Routes (Polling-based - works everywhere!)
# ============

@app.route('/api/chat/messages')
def get_chat_messages():
    """Get chat messages since timestamp - polling endpoint"""
    import time
    try:
        last_id = int(request.args.get('last_id', 0))
    except ValueError:
        last_id = 0
    
    # Get messages after the last received ID
    new_messages = [m for m in chat_messages if m['id'] > last_id]
    
    return jsonify({
        'messages': new_messages,
        'count': len(new_messages)
    })

@app.route('/api/chat/send', methods=['POST'])
def send_chat_message():
    """Send a chat message"""
    import time
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    player_name = data.get('player_name', '').strip()
    message = data.get('message', '').strip()
    
    if not player_name:
        # Try to get from session
        try:
            game_state = get_game_state()
            player_name = game_state.player_name or 'Anonymous'
        except:
            player_name = 'Anonymous'
    
    if not message:
        return jsonify({'error': 'Message is empty'}), 400
    
    if len(message) > 200:
        return jsonify({'error': 'Message too long (max 200 chars)'}), 400
    
    # Add the message
    msg = add_chat_message(player_name, message)
    
    return jsonify({
        'success': True,
        'message': msg
    })

@app.route('/api/chat/status')
def chat_status():
    """Get chat status (total messages, etc.)"""
    return jsonify({
        'total_messages': len(chat_messages),
        'online': True,
        'system': 'polling'
    })

@app.route('/api/player/info')
def get_player_info():
    """Get current player info for chat"""
    try:
        game_state = get_game_state()
        return jsonify({
            'player_name': game_state.player_name or 'Player',
            'location': game_state.current_location or 'city'
        })
    except:
        return jsonify({
            'player_name': 'Player',
            'location': 'city'
        })

# ============
# Legacy SocketIO handlers (kept for reference but not active)
# ============

# Global player tracking (for future use with PVP etc.)
connected_players = {}

socketio = None  # SocketIO is disabled - using polling instead

# ============
# Game State
# ============

@dataclass
class Flags:
    has_id: bool = False
    has_info: bool = False
    eric_met: bool = False
    steve_met: bool = False

@dataclass
class Drugs:
    weed: int = 0
    crack: int = 5
    coke: int = 0
    ice: int = 0
    percs: int = 0
    pixie_dust: int = 0

    def __contains__(self, drug):
        return hasattr(self, drug)

    def keys(self):
        return ['weed', 'crack', 'coke', 'ice', 'percs', 'pixie_dust']

@dataclass
class GangMember:
    id: int = 0
    name: str = ""
    health: int = 30
    max_health: int = 30
    is_alive: bool = True

@dataclass
class Weapons:
    pistols: int = 0
    bullets: int = 0
    grenades: int = 0
    vampire_bat: int = 0
    missile_launcher: int = 0
    missiles: int = 0
    vest: int = 0
    knife: int = 0
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
    pistol_automatic: bool = False
    ghost_gun_automatic: bool = False

    def can_fight_with_pistol(self):
        return self.pistols > 0 and self.bullets > 0

@dataclass
class GameState:
    player_name: str = ""
    gang_name: str = ""
    money: int = 1000
    account: int = 0
    loan: int = 0
    loan_days: int = 0
    members: int = 1
    squidies: int = 25
    squidies_pistols: int = 10
    squidies_bullets: int = 100
    squidies_grenades: int = 20
    squidies_missile_launcher: int = 2
    squidies_missiles: int = 10
    day: int = 1
    health: int = 30
    steps: int = 0
    max_steps: int = 7
    current_score: int = 0
    current_location: str = "city"
    drug_prices: Dict[str, int] = field(default_factory=lambda: {
        'weed': 500,
        'crack': 1000,
        'coke': 2000,
        'ice': 1500,
        'percs': 800,
        'pixie_dust': 3000
    })
    lives: int = 3
    damage: int = 0
    flags: Flags = field(default_factory=Flags)
    weapons: Weapons = field(default_factory=Weapons)
    drugs: Drugs = field(default_factory=Drugs)
    gang_members: List[GangMember] = field(default_factory=list)

    @property
    def max_health(self) -> int:
        """Calculate max health based on gang members: 30 base + 10 HP per member beyond the first"""
        return 30 + 10 * (self.members - 1)

# ============
# Game Logic
# ============

def get_game_state():
    """Get current game state from session"""
    if 'game_state' not in session:
        session['game_state'] = asdict(GameState())
    game_dict = session['game_state']
    # Convert nested dicts back to objects
    game_dict['flags'] = Flags(**game_dict.get('flags', {}))
    game_dict['weapons'] = Weapons(**game_dict.get('weapons', {}))
    game_dict['drugs'] = Drugs(**game_dict.get('drugs', {}))
    # Load current drug prices from global file
    drug_prices_data = load_current_drug_prices()
    game_dict['drug_prices'] = drug_prices_data.get('prices', {}) or {
        'weed': 500,
        'crack': 1000,
        'coke': 2000,
        'ice': 1500,
        'percs': 800,
        'pixie_dust': 3000
    }
    return GameState(**game_dict)

def update_current_score(game_state):
    """Update the current score based on achievements"""
    money_earned = game_state.money + game_state.account
    days_survived = game_state.day
    # For current score, we don't track gang wars/fights won in real-time,
    # so we'll base it on money and days survived for now
    game_state.current_score = calculate_score(money_earned, days_survived, 0, 0)

def process_daily_interest_and_loans(game_state):
    """Process daily interest on savings and loans, and check for loan shark attacks"""
    # Calculate interest on savings account
    if game_state.account > 0:
        interest_rate = 0.08  # Base 8% daily (increased from 5%)
        # Scale interest based on deposit amount (larger deposits get slightly better rates)
        if game_state.account >= 10000:
            interest_rate = 0.10  # 10% for large deposits (increased from 6%)
        elif game_state.account >= 5000:
            interest_rate = 0.09  # 9% for medium deposits (increased from 5.5%)

        interest_earned = int(game_state.account * interest_rate)
        game_state.account += interest_earned

    # Calculate loan interest and check for loan sharks
    if game_state.loan > 0:
        # High interest loans: 15% per day
        interest_due = int(game_state.loan * 0.15)
        game_state.loan += interest_due

        # Track days since loan was taken (we'll add a loan_days field to GameState)
        if not hasattr(game_state, 'loan_days'):
            game_state.loan_days = 0
        game_state.loan_days += 1

        # Loan shark attack after 2-3 days depending on loan amount
        attack_threshold = 2 if game_state.loan <= 50000 else 3  # Smaller loans get attacked sooner

        if game_state.loan_days >= attack_threshold:
            # Loan shark attack! This will redirect to combat
            num_sharks = random.randint(3, 6)
            message = f"LOAN SHARKS! {num_sharks} brutal loan collectors have come to collect on your ${game_state.loan:,} debt!"
            # We'll handle this in the calling function by setting a flag
            return {
                'loan_shark_attack': True,
                'num_sharks': num_sharks,
                'message': message
            }

    return {'loan_shark_attack': False}

def save_game_state(game_state):
    """Save game state to session"""
    # Update current score before saving
    update_current_score(game_state)
    session['game_state'] = asdict(game_state)
    session.modified = True

def check_and_update_high_scores(game_state: GameState, gang_wars_won: int = 0, fights_won: int = 0):
    """Check if current game qualifies for high score and update if necessary"""
    if not game_state.player_name or not game_state.gang_name:
        return

    # Calculate current achievements
    money_earned = game_state.money + game_state.account  # Include savings
    days_survived = game_state.day

    # Calculate score
    score = calculate_score(money_earned, days_survived, gang_wars_won, fights_won)

    # Load existing high scores
    high_scores = load_high_scores()

    # Check if this player already has a high score entry
    existing_entry = None
    for i, hs in enumerate(high_scores):
        if hs.player_name == game_state.player_name and hs.gang_name == game_state.gang_name:
            existing_entry = (i, hs)
            break

    # Create new high score entry
    new_score = HighScore(
        player_name=game_state.player_name,
        gang_name=game_state.gang_name,
        score=score,
        money_earned=money_earned,
        days_survived=days_survived,
        gang_wars_won=gang_wars_won,
        fights_won=fights_won,
        date_achieved=time.strftime("%Y-%m-%d %H:%M:%S")
    )

    if existing_entry:
        # Update existing entry if score improved
        index, old_score = existing_entry
        if score > old_score.score:
            high_scores[index] = new_score
    else:
        # Add new entry
        high_scores.append(new_score)

    # Sort by score (highest first)
    high_scores.sort(key=lambda x: x.score, reverse=True)

    # Keep only top 10 scores
    high_scores = high_scores[:10]

    # Save updated high scores
    save_high_scores(high_scores)

def update_daily_high_scores(game_state: GameState):
    """Update high scores daily for active players - called when they visit main pages"""
    if not game_state.player_name or not game_state.gang_name:
        return

    # Check if we need to update (once per day per player OR when day changes)
    today = time.strftime("%Y-%m-%d")
    last_update_key = f"last_high_score_update_{game_state.player_name}_{game_state.gang_name}"
    last_day_key = f"last_high_score_day_{game_state.player_name}_{game_state.gang_name}"
    
    last_update = session.get(last_update_key, '')
    last_day = session.get(last_day_key, 0)
    
    # Update if it's a new day OR if the game day has changed
    if last_update != today or last_day != game_state.day:
        # Update high scores with current progress
        check_and_update_high_scores(game_state, 0, 0)
        
        # Mark as updated today and record the game day
        session[last_update_key] = today
        session[last_day_key] = game_state.day
        session.modified = True


# Global drug price update function - called once per day
def update_global_drug_prices():
    """Update drug prices globally once per day - affects all players"""
    current_prices = load_current_drug_prices()

    # Check if we need to update (once per day)
    import time
    today = time.strftime("%Y-%m-%d")
    if current_prices.get('last_update_day') == today:
        return current_prices  # Already updated today

    # Update prices for new day
    new_prices = update_daily_drug_prices()

    # Mark as updated today
    new_prices['last_update_day'] = today
    save_current_drug_prices(new_prices)

    return new_prices

# ============
# Routes
# ============

@app.route('/')
def index():
    """Main index page"""
    return render_template('index.html', game_state=None)

@app.route('/high_scores')
def high_scores():
    """Display all-time high scores"""
    scores = load_high_scores()
    return render_template('high_scores.html', high_scores=scores, game_state=get_game_state())

@app.route('/credits')
def credits():
    """Display credits and high scores"""
    scores = load_high_scores()
    return render_template('credits.html', high_scores=scores, game_state=get_game_state())

@app.route('/city')
def city():
    """City hub"""
    game_state = get_game_state()
    game_state.current_location = "city"

    # Update global drug prices once per day (affects all players)
    update_global_drug_prices()

    # Update high scores daily for active players
    update_daily_high_scores(game_state)

    save_game_state(game_state)
    # Get current drug prices for alerts
    current_prices_data = load_current_drug_prices()
    city_alert = current_prices_data.get('fluctuation_alert', '')
    return render_template('city.html', game_state=game_state, city_alert=city_alert)

@app.route('/crackhouse')
def crackhouse():
    """Crackhouse"""
    game_state = get_game_state()
    game_state.current_location = "crackhouse"
    save_game_state(game_state)
    return render_template('crackhouse.html', game_state=game_state)

@app.route('/gunshack')
def gunshack():
    """Gun Pawn USA"""
    game_state = get_game_state()
    return render_template('gunshack.html', game_state=game_state)

@app.route('/buy_weapon', methods=['POST'])
def buy_weapon():
    """Handle weapon purchases"""
    game_state = get_game_state()
    weapon_type = request.form.get('weapon_type')
    quantity = int(request.form.get('quantity', 1))

    # Define weapon prices
    weapon_prices = {
        'pistol': 1200,
        'bullets': 100,
        'exploding_bullets': 2000,
        'hollow_point_bullets': 500,
        'grenade': 1000,
        'vampire_bat': 2500,
        'missile_launcher': 1000000,
        'missile': 100000,
        'vest_light': 5000,
        'vest_medium': 15000,
        'vest_heavy': 25000,
        'ar15': 10000,
        'ghost_gun': 600
    }

    if weapon_type not in weapon_prices:
        flash("Invalid weapon type!", "danger")
        return redirect(url_for('gunshack'))

    price = weapon_prices[weapon_type]
    total_cost = price * quantity

    if game_state.money < total_cost:
        flash(f"You don't have enough money! Need ${total_cost:,}.", "danger")
        return redirect(url_for('gunshack'))

    # Deduct money
    game_state.money -= total_cost

    # Add weapon to inventory
    game_state.current_score += 1  # Minor achievement: 1 point for buying weapons
    if weapon_type == 'pistol':
        game_state.weapons.pistols += quantity
    elif weapon_type == 'bullets':
        game_state.weapons.bullets += quantity * 50  # Bullets come in packs of 50
    elif weapon_type == 'exploding_bullets':
        game_state.weapons.exploding_bullets += quantity * 50  # Exploding bullets come in packs of 50
    elif weapon_type == 'hollow_point_bullets':
        game_state.weapons.hollow_point_bullets += quantity * 50  # Hollow point bullets come in packs of 50
    elif weapon_type == 'grenade':
        game_state.weapons.grenades += quantity
    elif weapon_type == 'vampire_bat':
        game_state.weapons.vampire_bat += quantity
    elif weapon_type == 'missile_launcher':
        game_state.weapons.missile_launcher += quantity
    elif weapon_type == 'missile':
        game_state.weapons.missiles += quantity
    elif weapon_type == 'vest_light':
        game_state.weapons.vest += 5  # Light vest gives 5 hits
    elif weapon_type == 'vest_medium':
        game_state.weapons.vest += 10  # Medium vest gives 10 hits
    elif weapon_type == 'vest_heavy':
        game_state.weapons.vest += 15  # Heavy vest gives 15 hits
    elif weapon_type == 'ar15':
        game_state.weapons.ar15 += quantity
    elif weapon_type == 'ghost_gun':
        game_state.weapons.ghost_guns += quantity

    # Save and flash success
    save_game_state(game_state)
    flash(f"You bought {quantity} {weapon_type.replace('_', ' ')}(s) for ${total_cost:,}!", "success")
    return redirect(url_for('gunshack'))

@app.route('/upgrade_weapon', methods=['POST'])
def upgrade_weapon():
    """Handle weapon upgrades"""
    game_state = get_game_state()
    weapon_type = request.form.get('weapon_type')

    # Define upgrade prices
    upgrade_prices = {
        'pistol': 2000,
        'ghost_gun': 2000
    }

    if weapon_type not in upgrade_prices:
        flash("Invalid weapon type for upgrade!", "danger")
        return redirect(url_for('gunshack'))

    price = upgrade_prices[weapon_type]

    if game_state.money < price:
        flash(f"You don't have enough money! Need ${price:,}.", "danger")
        return redirect(url_for('gunshack'))

    # Check if weapon exists and is not already upgraded
    if weapon_type == 'pistol':
        if game_state.weapons.pistols <= 0:
            flash("You don't have a pistol to upgrade!", "danger")
            return redirect(url_for('gunshack'))
        if game_state.weapons.pistol_automatic:
            flash("Your pistol is already automatic!", "info")
            return redirect(url_for('gunshack'))
        game_state.weapons.pistol_automatic = True
        weapon_name = "Pistol (Switch)"
    elif weapon_type == 'ghost_gun':
        if game_state.weapons.ghost_guns <= 0:
            flash("You don't have a ghost gun to upgrade!", "danger")
            return redirect(url_for('gunshack'))
        if game_state.weapons.ghost_gun_automatic:
            flash("Your ghost gun is already automatic!", "info")
            return redirect(url_for('gunshack'))
        game_state.weapons.ghost_gun_automatic = True
        weapon_name = "Ghost Gun"

    # Deduct money
    game_state.money -= price

    # Save and flash success
    save_game_state(game_state)
    flash(f"You upgraded your {weapon_name} to automatic for ${price:,}!", "success")
    return redirect(url_for('gunshack'))

@app.route('/bar', methods=['GET', 'POST'])
def bar():
    """The Local Pub"""
    game_state = get_game_state()
    if request.method == 'POST':
        contact = request.form.get('contact')

        # Make NPC interactions more difficult - require certain conditions
        if contact == 'nox':
            # Nox requires having some money and not being too aggressive - now harder
            success_chance = 0.25  # Base 25% chance (reduced from 40%)
            if game_state.money >= 2000:  # Having more money helps
                success_chance += 0.15
            if game_state.members <= 2:  # Very small gang is less intimidating
                success_chance += 0.15
            if game_state.flags.has_info:  # Having info helps
                success_chance += 0.1
            if game_state.account >= 10000:  # Savings show you're established
                success_chance += 0.1

            if random.random() < success_chance:
                game_state.flags.eric_met = True
                flash("You successfully meet Nox the Informant! He shares valuable information.", "success")
            else:
                # Failed interaction - various consequences
                failure_types = [
                    ("Nox doesn't trust you and walks away.", "warning"),
                    ("Nox thinks you're a cop and threatens you!", "danger"),
                    ("Nox demands money for information but you refuse.", "warning"),
                    ("The meeting goes badly - you offend Nox and he spreads rumors about you.", "danger"),
                    ("Nox sets you up for an ambush!", "danger")
                ]
                failure_msg, failure_type = random.choice(failure_types)
                flash(f"Failed to meet Nox: {failure_msg}", failure_type)

                # Some failures have consequences
                if "threatens you" in failure_msg:
                    game_state.health = max(0, game_state.health - random.randint(10, 20))
                elif "spreads rumors" in failure_msg:
                    # Lose a gang member due to bad reputation
                    if game_state.members > 1:
                        game_state.members -= 1
                        game_state.health = min(game_state.max_health, game_state.health)
                elif "sets you up" in failure_msg:
                    # Trigger a police encounter
                    game_state.flags.has_id = False  # Lose fake ID
                    flash("Police are now hunting you!", "danger")

        elif contact == 'raze':
            # Raze requires having drugs and being established - now much harder
            success_chance = 0.15  # Base 15% chance (reduced from 30%)
            total_drugs = sum([getattr(game_state.drugs, drug) for drug in ['weed', 'crack', 'coke', 'ice', 'percs', 'pixie_dust']])
            if total_drugs >= 20:  # Having lots of drugs helps
                success_chance += 0.25
            if game_state.members >= 8:  # Large gang commands respect
                success_chance += 0.15
            if game_state.account >= 25000:  # Substantial savings show stability
                success_chance += 0.1
            if game_state.money >= 5000:  # Cash on hand shows you're flush
                success_chance += 0.1

            if random.random() < success_chance:
                game_state.flags.steve_met = True
                flash("You successfully meet Raze the Supplier! He offers you special deals.", "success")
            else:
                # Failed interaction - various consequences
                failure_types = [
                    ("Raze doesn't deal with small-timers like you.", "warning"),
                    ("Raze suspects you're undercover and refuses to talk.", "danger"),
                    ("The deal goes sour - Raze's goons rough you up!", "danger"),
                    ("Raze demands a show of force but you back down.", "warning"),
                    ("Raze's men steal some of your drugs!", "danger")
                ]
                failure_msg, failure_type = random.choice(failure_types)
                flash(f"Failed to meet Raze: {failure_msg}", failure_type)

                # Some failures have consequences
                if "rough you up" in failure_msg:
                    damage = random.randint(15, 35)
                    game_state.health = max(0, game_state.health - damage)
                    flash(f"You take {damage} damage from Raze's goons!", "danger")
                elif "suspects you're undercover" in failure_msg:
                    # Police attention increases
                    game_state.flags.has_id = False  # Lose fake ID if you had one
                    flash("Your cover might be blown!", "warning")
                elif "steal some of your drugs" in failure_msg:
                    # Lose some drugs
                    drug_types = ['weed', 'crack', 'coke', 'ice', 'percs', 'pixie_dust']
                    available_drugs = [d for d in drug_types if getattr(game_state.drugs, d) > 0]
                    if available_drugs:
                        stolen_drug = random.choice(available_drugs)
                        stolen_amount = min(getattr(game_state.drugs, stolen_drug), random.randint(1, 3))
                        setattr(game_state.drugs, stolen_drug, getattr(game_state.drugs, stolen_drug) - stolen_amount)
                        flash(f"Raze's men stole {stolen_amount} kilos of {stolen_drug}!", "danger")

        save_game_state(game_state)
        return redirect(url_for('bar'))

    # Update drug prices every other day (every 2 days)
    current_prices_data = load_current_drug_prices()
    today = time.strftime("%Y-%m-%d")
    last_update_day = current_prices_data.get('last_update_day', '')
    last_update_count = current_prices_data.get('update_count', 0)

    # Check if we need to update (every 2 days)
    if last_update_day != today:
        # Increment update count
        new_update_count = last_update_count + 1
        # Update prices every 2 days
        if new_update_count >= 2:
            # Reset count and update prices
            new_update_count = 0
            update_global_drug_prices()
        # Save updated count
        current_prices_data['update_count'] = new_update_count
        current_prices_data['last_update_day'] = today
        save_current_drug_prices(current_prices_data)

    # Generate price mood based on current drug prices
    current_prices_data = load_current_drug_prices()
    current_prices = current_prices_data.get('prices', {})
    
    if current_prices:
        # Get base prices for comparison
        base_prices = {name: info['base_price'] for name, info in drug_config.get('drugs', {}).items()}
        
        # Analyze price trends
        price_comments = []
        for drug, current_price in current_prices.items():
            base_price = base_prices.get(drug, current_price)
            if base_price > 0:
                price_change = ((current_price - base_price) / base_price) * 100
                
                if price_change > 50:
                    price_comments.append(f"{drug.upper()} is EXPENSIVE ({price_change:+.0f}%)")
                elif price_change < -30:
                    price_comments.append(f"{drug.upper()} is CHEAP ({price_change:+.0f}%)")
        
        if price_comments:
            # Pick 1-2 random comments
            import random as rand
            rand.shuffle(price_comments)
            price_mood = " | ".join(price_comments[:2])
        else:
            price_mood = "Prices are stable today - normal fluctuations expected."
    else:
        price_mood = "Prices are crazy today - keep your eyes open!"

    return render_template('bar.html', game_state=game_state, price_mood=price_mood)

@app.route('/bank')
def bank():
    """Savings and Loan"""
    game_state = get_game_state()
    return render_template('bank.html', game_state=game_state)

@app.route('/bank_transaction', methods=['POST'])
def bank_transaction():
    """Handle bank transactions (deposit, withdraw, loan, pay_loan)"""
    game_state = get_game_state()
    action = request.form.get('action')
    amount = int(request.form.get('amount', 0))

    if action == 'deposit':
        if amount <= 0:
            flash("Deposit amount must be positive!", "danger")
        elif amount > game_state.money:
            flash("You don't have enough cash to deposit!", "danger")
        else:
            game_state.money -= amount
            game_state.account += amount
            # Interest calculation: 8-10% per day, compounded
            interest_rate = 0.08
            # Scale interest based on deposit amount (larger deposits get slightly better rates)
            if amount >= 10000:
                interest_rate = 0.10  # 10% for large deposits
            elif amount >= 5000:
                interest_rate = 0.09  # 9% for medium deposits
            flash(f"You deposited ${amount:,}! Your savings earn {interest_rate*100:.1f}% interest daily.", "success")

    elif action == 'withdraw':
        if amount <= 0:
            flash("Withdrawal amount must be positive!", "danger")
        elif amount > game_state.account:
            flash("You don't have enough in savings to withdraw!", "danger")
        else:
            game_state.account -= amount
            game_state.money += amount
            flash(f"You withdrew ${amount:,} from your savings!", "success")

    elif action == 'loan':
        # Max loan is 100,000 normally, but 500,000 if you have 10+ gang members
        max_loan = 100000
        if game_state.members >= 10:
            max_loan = 500000
        
        loan_options = {
            '5000': 5000,
            '10000': 10000,
            '25000': 25000,
            '50000': 50000,
            '100000': 100000
        }
        
        # Add 500000 option only if player has 10+ gang members
        if game_state.members >= 10:
            loan_options['500000'] = 500000
        
        if str(amount) not in loan_options:
            flash("Invalid loan amount!", "danger")
        elif amount > max_loan:
            flash(f"Maximum loan is ${max_loan:,}!", "danger")
        elif game_state.loan > 0:
            flash("You already have an outstanding loan! Pay it off first.", "danger")
        else:
            loan_amount = loan_options[str(amount)]
            # High interest loans: 15% per day
            game_state.loan = loan_amount
            game_state.loan_days = 0  # Reset loan days when taking new loan
            game_state.money += loan_amount
            flash(f"You took out a ${loan_amount:,} loan at 15% daily interest! Pay it back quickly to avoid loan sharks!", "warning")

    elif action == 'pay_loan':
        if amount <= 0:
            flash("Payment amount must be positive!", "danger")
        elif amount > game_state.money:
            flash("You don't have enough cash to pay!", "danger")
        elif amount > game_state.loan:
            flash("You're trying to pay more than you owe!", "danger")
        else:
            game_state.money -= amount
            game_state.loan -= amount
            if game_state.loan <= 0:
                game_state.loan = 0
                flash(f"You paid off your entire loan! You're debt-free!", "success")
            else:
                flash(f"You paid ${amount:,} towards your loan. You still owe ${game_state.loan:,}.", "info")

    save_game_state(game_state)
    return redirect(url_for('bank'))

@app.route('/infobooth')
def infobooth():
    """Info Booth"""
    game_state = get_game_state()
    return render_template('infobooth.html', game_state=game_state)

@app.route('/alleyway')
def alleyway():
    """Explore Dark Alleyway"""
    game_state = get_game_state()
    game_state.current_location = "alleyway"
    save_game_state(game_state)

    # Define alleyway rooms
    rooms = {
        'entrance': {
            'title': 'Dark Alley Entrance',
            'description': 'You stand at the entrance of a dark alleyway. The streetlights cast long shadows, and you can hear distant sounds echoing off the walls.',
            'exits': {
                'north': 'dead_end',
                'south': 'city',
                'east': 'side_street',
                'west': 'dumpster'
            }
        },
        'dead_end': {
            'title': 'Dead End',
            'description': 'You reach a dead end with graffiti-covered walls. There\'s nothing here but trash and shadows.',
            'exits': {
                'south': 'entrance'
            }
        },
        'side_street': {
            'title': 'Side Street',
            'description': 'You emerge onto a narrow side street. Cars occasionally drive by, and you see a few shady figures watching you.',
            'exits': {
                'west': 'entrance',
                'north': 'hidden_entrance',
                'east': 'abandoned_building'
            }
        },
        'dumpster': {
            'title': 'Behind the Dumpster',
            'description': 'You hide behind a large dumpster. The smell is awful, but you\'re well concealed. You find some discarded items.',
            'exits': {
                'east': 'entrance',
                'north': 'maintenance_shaft'
            }
        },
        'hidden_entrance': {
            'title': 'Hidden Entrance',
            'description': 'You find a hidden entrance to an underground network. This could lead to interesting places...',
            'exits': {
                'south': 'side_street',
                'down': 'underground',
                'east': 'sewer_entrance'
            }
        },
        'underground': {
            'title': 'Underground Passage',
            'description': 'You descend into a dimly lit underground passage. Water drips from the ceiling, and you hear echoes of distant footsteps.',
            'exits': {
                'up': 'hidden_entrance',
                'north': 'secret_room',
                'east': 'underground_market'
            }
        },
        'secret_room': {
            'title': 'Secret Room',
            'description': 'You enter a secret room filled with old crates and mysterious artifacts. There might be valuable items here.',
            'exits': {
                'south': 'underground',
                'west': 'storage_room'
            }
        },
        'abandoned_building': {
            'title': 'Abandoned Building',
            'description': 'You enter a crumbling abandoned building. The floors are covered in dust and debris, and you can hear rats scurrying in the walls.',
            'exits': {
                'west': 'side_street',
                'up': 'rooftop_access',
                'north': 'old_warehouse'
            }
        },
        'sewer_entrance': {
            'title': 'Sewer Entrance',
            'description': 'A rusty manhole cover leads down into the city\'s sewer system. The air smells of decay and chemicals.',
            'exits': {
                'west': 'hidden_entrance',
                'down': 'sewer_tunnels'
            }
        },
        'rooftop_access': {
            'title': 'Rooftop Access',
            'description': 'You climb a rickety ladder to the rooftop. The city lights spread out before you, and you can see other buildings nearby.',
            'exits': {
                'down': 'abandoned_building'
            }
        },
        'underground_market': {
            'title': 'Underground Market',
            'description': 'You stumble upon a hidden underground market. Shady merchants sell illegal goods under dim fluorescent lights.',
            'exits': {
                'west': 'underground',
                'north': 'hidden_lab'
            }
        },
        'storage_room': {
            'title': 'Storage Room',
            'description': 'This room is filled with old storage containers and forgotten equipment. Dust covers everything, but there might be valuables hidden here.',
            'exits': {
                'east': 'secret_room'
            }
        },
        'maintenance_shaft': {
            'title': 'Maintenance Shaft',
            'description': 'A narrow maintenance shaft runs along the alley. It\'s dark and cramped, but you can hear the hum of machinery nearby.',
            'exits': {
                'south': 'dumpster',
                'up': 'utility_room'
            }
        },
        'old_warehouse': {
            'title': 'Old Warehouse',
            'description': 'You enter an old warehouse filled with rusted machinery and broken crates. The air is thick with the smell of oil and decay.',
            'exits': {
                'south': 'abandoned_building'
            }
        },
        'sewer_tunnels': {
            'title': 'Sewer Tunnels',
            'description': 'The sewer tunnels are dark and damp. Water flows through channels, and you can hear the distant rumble of the city above.',
            'exits': {
                'up': 'sewer_entrance',
                'north': 'flooded_chamber'
            }
        },
        'hidden_lab': {
            'title': 'Hidden Lab',
            'description': 'You discover a clandestine laboratory hidden in the underground. Beakers bubble and strange equipment hums with activity.',
            'exits': {
                'south': 'underground_market'
            }
        },
        'utility_room': {
            'title': 'Utility Room',
            'description': 'This utility room contains electrical panels and plumbing. The walls are lined with pipes and conduits.',
            'exits': {
                'down': 'maintenance_shaft'
            }
        },
        'flooded_chamber': {
            'title': 'Flooded Chamber',
            'description': 'This chamber is partially flooded with murky water. Strange shapes move in the depths, and the air is thick with humidity.',
            'exits': {
                'south': 'sewer_tunnels'
            }
        }
    }

    # Get current room from session, default to entrance
    current_room_id = session.get('current_alleyway_room', 'entrance')
    current_room = rooms.get(current_room_id, rooms['entrance'])

    return render_template('alleyway.html', game_state=game_state, current_room=current_room)

@app.route('/stats')
def stats():
    """View Stats"""
    game_state = get_game_state()
    return render_template('stats.html', game_state=game_state)

@app.route('/final_battle')
def final_battle():
    """FINAL BATTLE: Destroy Squidies"""
    game_state = get_game_state()
    message = "You launch your final assault on the Squidies gang headquarters!"
    # Start MUD fight with Squidies
    enemy_health = game_state.squidies * 20  # Each Squidie has 20 health
    max_enemy_hp = enemy_health
    enemy_type = f"The Squidies Gang ({game_state.squidies} members)"
    combat_active = True
    fight_log = [message]
    combat_id = f"final_battle_{random.randint(1000, 9999)}"
    return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, max_enemy_hp=max_enemy_hp, enemy_type=enemy_type, enemy_count=game_state.squidies, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)

@app.route('/wander')
def wander():
    """Wander the Streets"""
    game_state = get_game_state()
    result = "You wander the streets uneventfully."  # Default result

    # Calculate cop encounter chance - reduced if you have a ghost gun
    base_cop_chance = 0.1  # 10% base chance
    if game_state.weapons.ghost_guns > 0:
        # Each ghost gun reduces cop encounters by 5%
        reduction = min(0.05 * game_state.weapons.ghost_guns, 0.04)  # Max 4% reduction
        base_cop_chance -= reduction
    
    # Check for police chase
    if random.random() < base_cop_chance:
        if game_state.flags.has_id:
            result = "You see a police patrol but your fake ID saves you from getting stopped!"
            flash("Your fake ID protected you from police harassment!", "success")
        else:
            # Police chase sequence - redirect to MUD fight
            num_cops = random.randint(2, 6)
            message = f"Oh no! {num_cops} police officers spot you and give chase!"
            save_game_state(game_state)
            enemy_health = num_cops * 10  # Each cop has 10 health
            enemy_type = f"{num_cops} Police Officers"
            combat_active = True
            fight_log = [message]
            combat_id = f"police_{random.randint(1000, 9999)}"
            return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=num_cops, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)

    # Check for baby momma incident (8% chance)
    elif random.random() < 0.08:
        baby_momma_messages = [
            "Your baby momma spots you from across the street and starts yelling about child support!",
            "You run into one of your many baby mommas who demands money for the kids!",
            "A woman approaches you claiming you're the father of her child and demands $500!",
            "You see your ex approaching with a determined look - she wants money for the kids!"
        ]
        result = random.choice(baby_momma_messages)
        # Lose money if you have it
        if game_state.money >= 200:
            game_state.money -= 200
            result += f" You pay her $200 to make her go away."
        elif game_state.money >= 100:
            game_state.money -= 100
            result += f" You give her $100 to calm her down."
        else:
            result += " You don't have any money to give her!"
            game_state.health = max(0, game_state.health - 10)  # She beats you up

    # Check for small gang fight (12% chance)
    elif random.random() < 0.12:
        enemy_members = random.randint(3, 8)
        message = f"You encounter {enemy_members} rival gang members looking for trouble!"
        save_game_state(game_state)
        # Start MUD fight
        enemy_health = enemy_members * 15  # Each gang member has 15 health
        max_enemy_hp = enemy_health
        enemy_type = f"{enemy_members} Rival Gang Members"
        combat_active = True
        fight_log = [message]
        combat_id = f"gang_{random.randint(1000, 9999)}"
        return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, max_enemy_hp=max_enemy_hp, enemy_type=enemy_type, enemy_count=enemy_members, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)

    # Check for random mugging/jumping (scales with money carried)
    elif game_state.money >= 1000:  # Only if carrying significant cash
        # Chance increases with more money carried
        base_chance = 0.05  # 5% base chance
        money_multiplier = min(game_state.money / 5000, 3.0)  # Up to 3x multiplier at $15k+
        total_chance = base_chance * money_multiplier

        if random.random() < total_chance:
            mugger_count = random.randint(2, 5)
            message = f"OH NO! You got jumped by {mugger_count} muggers who want your cash!"
            save_game_state(game_state)
            # Start MUD fight with muggers
            enemy_health = mugger_count * 20  # Muggers are moderately tough (20 HP each)
            max_enemy_hp = enemy_health
            enemy_type = f"{mugger_count} Street Muggers"
            combat_active = True
            fight_log = [message]
            combat_id = f"muggers_{random.randint(1000, 9999)}"
            return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, max_enemy_hp=max_enemy_hp, enemy_type=enemy_type, enemy_count=mugger_count, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)

    # Check for Squidie hit squad (scales with gang power)
    elif game_state.members >= 3:  # Only when you have some gang presence
        # Base chance starts low, increases with gang size and success
        base_chance = 0.02  # 2% base chance
        gang_multiplier = min(game_state.members / 10, 2.0)  # Up to 2x multiplier at 10+ members
        money_multiplier = min(game_state.money / 10000, 1.5)  # Up to 1.5x for $10k+
        total_chance = base_chance * gang_multiplier * money_multiplier

        if random.random() < total_chance:
            squidie_members = random.randint(2, min(6, max(2, game_state.members // 2 + 1)))
            message = f"Oh no! A Squidie hit squad of {squidie_members} members has tracked you down!"
            save_game_state(game_state)
            # Start MUD fight with Squidies
            enemy_health = squidie_members * 25  # Squidies are tougher (25 HP each)
            max_enemy_hp = enemy_health
            enemy_type = f"{squidie_members} Squidie Hit Squad"
            combat_active = True
            fight_log = [message]
            combat_id = f"squidie_{random.randint(1000, 9999)}"
            return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, max_enemy_hp=max_enemy_hp, enemy_type=enemy_type, enemy_count=squidie_members, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)

    # Regular wander results (remaining ~70% chance)
    else:
        # List of possible wander results - now ultra bloody and violent
        wander_messages = [
            "You stumble upon a gutted corpse in an alleyway, blood pooling around the severed limbs. You search the remains and find $500 in bloody cash!",
            "A street performer lies slaughtered on the sidewalk, throat slit ear to ear. You overhear whispers of upcoming turf wars from nearby shadows.",
            "You witness a drive-by shooting where rival gang members get their brains blown out onto the pavement, painting the walls red.",
            "You find a quiet spot littered with mangled body parts to rest, regaining health amidst the stench of death.",
            "You notice suspicious activity - a beheaded body hanging from a streetlight - but decide to keep moving before you're next.",
            "You bump into an old contact who's missing an eye and bleeding profusely, sharing gossip about the bloody underworld.",
            "You wander into a rough neighborhood where limbs are strewn across the streets and narrowly avoid getting gutted yourself.",
            "You find some discarded drugs worth $200 on the street, next to a tortured corpse with carved flesh.",
            "You help a local shopkeeper who's covered in blood from a recent massacre, getting rewarded with information about safe havens.",
            "You wander around the city, stepping over dismembered bodies without incident, the air thick with the coppery smell of blood.",
            "You see a police patrol investigating a pile of corpses and quickly hide in an alley reeking of rotting flesh.",
            "You find a hidden stash of weapons beneath a freshly killed body, blood still warm on the ground.",
            "You encounter a beggar missing limbs who tells you about secret locations while bleeding out from multiple stab wounds.",
            "You wander through a market district where bodies hang from hooks like meat, haggling for better prices amidst the gore.",
            "You stumble upon a gang recruitment drive where initiates are branded with hot irons and tortured to prove loyalty."
        ]

        # Ensure randomness by seeding with current time
        random.seed(time.time())
        # Select a random message
        result = random.choice(wander_messages)

        # Apply effects based on the result
        if "bloody cash" in result:
            # Random cash reward between $500-$1000
            cash_found = random.randint(500, 1000)
            game_state.money += cash_found
            result = result.replace("$500", f"${cash_found}")
        elif "discarded drugs" in result:
            # Increased chance to find drugs instead of just money
            if random.random() < 0.7:  # 70% chance to find drugs
                drug_types = ['weed', 'crack', 'coke', 'ice', 'percs', 'pixie_dust']
                drug = random.choice(drug_types)
                amount = random.randint(2, 5)
                setattr(game_state.drugs, drug, getattr(game_state.drugs, drug) + amount)
                result += f" You find {amount} kilos of {drug}!"
            else:
                # Higher cash fallback reward
                cash_found = random.randint(300, 800)
                game_state.money += cash_found
                result = result.replace("$200", f"${cash_found}")
        elif "quiet spot" in result:
            game_state.health = min(game_state.max_health, game_state.health + 10)
        elif "hidden stash of weapons" in result:
            game_state.weapons.bullets += 5
        elif "without incident" not in result and "trouble" not in result and "police" not in result:
            # Minor health damage for risky wanders - now with violent consequences
            if random.random() < 0.3:
                game_state.health = max(0, game_state.health - 5)

    # Increment steps
    game_state.steps += 1

    # Check if day ends
    if game_state.steps >= game_state.max_steps:
        game_state.day += 1
        game_state.steps = 0
        # Process daily interest and loan sharks
        loan_shark_result = process_daily_interest_and_loans(game_state)
        if loan_shark_result['loan_shark_attack']:
            save_game_state(game_state)
            # Redirect to loan shark combat
            enemy_health = loan_shark_result['num_sharks'] * 30  # Loan sharks are tougher
            enemy_type = f"{loan_shark_result['num_sharks']} Loan Sharks"
            combat_active = True
            fight_log = [loan_shark_result['message']]
            combat_id = f"loan_sharks_{random.randint(1000, 9999)}"
            return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=loan_shark_result['num_sharks'], combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)
        # Update drug prices for new day
        update_daily_drug_prices()
        # Update high scores daily for active players
        update_daily_high_scores(game_state)

    # Check for NPC encounter (15% chance, down from 30% since we have more events now)
    if random.random() < 0.15 and npcs_data:
        wander_npcs = [npc for npc in npcs_data.values() if npc['location'] == 'wander']
        if wander_npcs:
            npc = random.choice(wander_npcs)
            save_game_state(game_state)
            return render_template('npc_interaction.html', npc=npc, action='encounter', message=f"You encounter {npc['name']}. {npc['description']}", game_state=game_state)

    save_game_state(game_state)

    return render_template('wander_result.html', game_state=game_state, result=result)

@app.route('/picknsave')
def picknsave():
    """Pick n Save grocery store"""
    game_state = get_game_state()
    return render_template('picknsave.html', game_state=game_state)

@app.route('/search_picknsave')
def search_picknsave():
    """Investigate Secrets at Pick n Save"""
    game_state = get_game_state()

    # Generate random secret information
    secrets = [
        "You overhear the store manager talking about a special bulk discount program for gang leaders.",
        "You find a hidden safe behind the counter containing $1000!",
        "You discover that the store owner is actually an ex-gang member who might have useful connections.",
        "You notice a suspicious van parked in the back - looks like someone is unloading special 'merchandise'.",
        "You find some discarded documents mentioning a rival gang's hideout location.",
        "You overhear customers talking about underground weapon shipments arriving next week.",
        "You find a secret compartment with free medical supplies!",
        "You discover the store has a hidden basement where 'special meetings' take place.",
        "You notice security cameras that don't match the store's official security system.",
        "You find evidence that the pizza delivery boy is actually a drug courier.",
        "You overhear plans for a major gang war starting in two days.",
        "You discover a trap door leading to an underground tunnel system.",
        "You find $200 in loose change scattered around the back room.",
        "You notice the store owner's ring bears a familiar gang symbol from your past.",
        "You discover plans for a police raid on a nearby crackhouse."
    ]

    # Select 2-3 random secrets
    revealed_secrets = random.sample(secrets, random.randint(2, 3))

    # Sometimes provide actual benefits
    benefits_found = []
    if random.random() < 0.3:  # 30% chance for a real benefit
        benefit_type = random.choice(['money', 'drugs', 'health', 'info'])
        if benefit_type == 'money':
            money_found = random.randint(500, 2000)
            game_state.money += money_found
            benefits_found.append(f"You found ${money_found} hidden in a secret compartment!")
        elif benefit_type == 'drugs':
            drug_types = ['weed', 'crack']
            drug = random.choice(drug_types)
            amount = random.randint(1, 3)
            setattr(game_state.drugs, drug, getattr(game_state.drugs, drug) + amount)
            benefits_found.append(f"You discovered {amount} kilos of {drug} stashed away!")
        elif benefit_type == 'health':
            game_state.health = min(game_state.max_health, game_state.health + 10)
            benefits_found.append("You found some free medical supplies and healed yourself!")
        elif benefit_type == 'info':
            game_state.flags.has_info = True
            benefits_found.append("You overheard crucial information about police movements!")

    save_game_state(game_state)

    return render_template('search_picknsave.html', game_state=game_state, secrets=revealed_secrets, benefits=benefits_found)

@app.route('/picknsave_action', methods=['POST'])
def picknsave_action():
    """Handle Pick n Save actions"""
    game_state = get_game_state()
    action = request.form.get('action')

    if action == 'buy_food':
        if game_state.money >= 500:
            game_state.money -= 500
            flash("You bought food supplies for your gang! Morale is high.", "success")
        else:
            flash("You don't have enough money for food supplies!", "danger")

    elif action == 'buy_medical':
        if game_state.money >= 1000:
            game_state.money -= 1000
            game_state.health = min(game_state.max_health, game_state.health + 50)  # Heal up to max health
            flash("You bought medical supplies! Health restored.", "success")
        else:
            flash("You don't have enough money for medical supplies!", "danger")

    elif action == 'buy_id':
        if game_state.money >= 5000:
            game_state.money -= 5000
            game_state.flags.has_id = True
            flash("You bought a fake ID! You're now protected from random police checks.", "success")
        else:
            flash("You don't have enough money for a fake ID!", "danger")

    elif action == 'buy_info':
        if game_state.money >= 2000:
            game_state.money -= 2000
            game_state.flags.has_info = True
            flash("You bought information! You now have insider knowledge about police activity.", "success")
        else:
            flash("You don't have enough money for information!", "danger")

    elif action == 'recruit':
        if game_state.money >= 10000:
            game_state.money -= 10000
            game_state.members += 1
            game_state.health = min(game_state.max_health, game_state.health + 10)
            flash("You recruited a new gang member! Your gang grows stronger.", "success")
        else:
            flash("You don't have enough money to recruit a new member!", "danger")

    save_game_state(game_state)
    return redirect(url_for('picknsave'))

@app.route('/trade_drugs', methods=['POST'])
def trade_drugs():
    """Handle drug trading actions"""
    game_state = get_game_state()
    action = request.form.get('action')
    drug_type = request.form.get('drug_type')
    quantity = int(request.form.get('quantity', 1))

    if drug_type not in game_state.drug_prices:
        flash("Invalid drug type!", "danger")
        return redirect(url_for('crackhouse'))

    price = game_state.drug_prices[drug_type]

    if action == 'buy':
        cost = price * quantity
        if game_state.money >= cost:
            game_state.money -= cost
            setattr(game_state.drugs, drug_type, getattr(game_state.drugs, drug_type) + quantity)
            flash(f"You bought {quantity} kilo(s) of {drug_type} for ${cost:,}!", "success")
        else:
            flash(f"You don't have enough money! Need ${cost:,}.", "danger")
    elif action == 'sell':
        current_qty = getattr(game_state.drugs, drug_type)
        if current_qty >= quantity:
            setattr(game_state.drugs, drug_type, current_qty - quantity)
            revenue = price * quantity
            game_state.money += revenue
            flash(f"You sold {quantity} kilo(s) of {drug_type} for ${revenue:,}!", "success")

            # Chance to recruit new member from big drug sales
            if revenue >= 5000:  # Big sale threshold
                if random.random() < 0.25:  # 25% chance for big sales
                    game_state.members += 1
                    game_state.health = min(game_state.max_health, game_state.health + 10)
                    flash("Word of your successful drug operation spread! A new recruit joined your gang!", "success")
        else:
            flash(f"You don't have enough {drug_type} to sell!", "danger")

    save_game_state(game_state)
    return redirect(url_for('crackhouse'))

@app.route('/visit_prostitutes')
def visit_prostitutes():
    """Visit Prostitutes"""
    game_state = get_game_state()
    return render_template('prostitutes.html', game_state=game_state)

@app.route('/prostitute_action', methods=['POST'])
def prostitute_action():
    """Handle prostitute service actions"""
    game_state = get_game_state()
    action = request.form.get('action')

    if action == 'quick_service':
        if game_state.money >= 200:
            game_state.money -= 200
            game_state.damage = max(0, game_state.damage - 5)  # Reduce stress/damage
            flash("You enjoyed a quick service and feel more relaxed.", "success")
        else:
            flash("You don't have enough money for a quick service!", "danger")

    elif action == 'vip_experience':
        if game_state.money >= 500:
            game_state.money -= 500
            game_state.damage = max(0, game_state.damage - 15)  # Reduce more damage/stress
            game_state.health = min(game_state.max_health, game_state.health + 5)  # Small health boost
            flash("You had a VIP experience and feel rejuvenated!", "success")
        else:
            flash("You don't have enough money for a VIP experience!", "danger")

    elif action == 'recruit_hooker':
        if game_state.money >= 1000:
            game_state.money -= 1000
            if random.random() < 0.6:  # 60% chance to recruit
                game_state.members += 1
                game_state.health = min(game_state.max_health, game_state.health + 10)
                flash("You successfully recruited a prostitute to join your gang!", "success")
            else:
                flash("The prostitute took your money but decided to stay in her current line of work.", "warning")
        else:
            flash("You don't have enough money to recruit a hooker!", "danger")

    save_game_state(game_state)
    return redirect(url_for('visit_prostitutes'))

@app.route('/search_room')
def search_room():
    """Search the current room for hidden treasures or traps"""
    game_state = get_game_state()

    # Define alleyway rooms
    rooms = {
        'entrance': {
            'title': 'Dark Alley Entrance',
            'description': 'You stand at the entrance of a dark alleyway. The streetlights cast long shadows, and you can hear distant sounds echoing off the walls.',
            'exits': {
                'north': 'dead_end',
                'south': 'city',
                'east': 'side_street',
                'west': 'dumpster'
            }
        },
        'dead_end': {
            'title': 'Dead End',
            'description': 'You reach a dead end with graffiti-covered walls. There\'s nothing here but trash and shadows.',
            'exits': {
                'south': 'entrance'
            }
        },
        'side_street': {
            'title': 'Side Street',
            'description': 'You emerge onto a narrow side street. Cars occasionally drive by, and you see a few shady figures watching you.',
            'exits': {
                'west': 'entrance',
                'north': 'hidden_entrance',
                'east': 'abandoned_building'
            }
        },
        'dumpster': {
            'title': 'Behind the Dumpster',
            'description': 'You hide behind a large dumpster. The smell is awful, but you\'re well concealed. You find some discarded items.',
            'exits': {
                'east': 'entrance',
                'north': 'maintenance_shaft'
            }
        },
        'hidden_entrance': {
            'title': 'Hidden Entrance',
            'description': 'You find a hidden entrance to an underground network. This could lead to interesting places...',
            'exits': {
                'south': 'side_street',
                'down': 'underground',
                'east': 'sewer_entrance'
            }
        },
        'underground': {
            'title': 'Underground Passage',
            'description': 'You descend into a dimly lit underground passage. Water drips from the ceiling, and you hear echoes of distant footsteps.',
            'exits': {
                'up': 'hidden_entrance',
                'north': 'secret_room',
                'east': 'underground_market'
            }
        },
        'secret_room': {
            'title': 'Secret Room',
            'description': 'You enter a secret room filled with old crates and mysterious artifacts. There might be valuable items here.',
            'exits': {
                'south': 'underground',
                'west': 'storage_room'
            }
        },
        'abandoned_building': {
            'title': 'Abandoned Building',
            'description': 'You enter a crumbling abandoned building. The floors are covered in dust and debris, and you can hear rats scurrying in the walls.',
            'exits': {
                'west': 'side_street',
                'up': 'rooftop_access',
                'north': 'old_warehouse'
            }
        },
        'sewer_entrance': {
            'title': 'Sewer Entrance',
            'description': 'A rusty manhole cover leads down into the city\'s sewer system. The air smells of decay and chemicals.',
            'exits': {
                'west': 'hidden_entrance',
                'down': 'sewer_tunnels'
            }
        },
        'rooftop_access': {
            'title': 'Rooftop Access',
            'description': 'You climb a rickety ladder to the rooftop. The city lights spread out before you, and you can see other buildings nearby.',
            'exits': {
                'down': 'abandoned_building'
            }
        },
        'underground_market': {
            'title': 'Underground Market',
            'description': 'You stumble upon a hidden underground market. Shady merchants sell illegal goods under dim fluorescent lights.',
            'exits': {
                'west': 'underground',
                'north': 'hidden_lab'
            }
        },
        'storage_room': {
            'title': 'Storage Room',
            'description': 'This room is filled with old storage containers and forgotten equipment. Dust covers everything, but there might be valuables hidden here.',
            'exits': {
                'east': 'secret_room'
            }
        },
        'maintenance_shaft': {
            'title': 'Maintenance Shaft',
            'description': 'A narrow maintenance shaft runs along the alley. It\'s dark and cramped, but you can hear the hum of machinery nearby.',
            'exits': {
                'south': 'dumpster',
                'up': 'utility_room'
            }
        },
        'old_warehouse': {
            'title': 'Old Warehouse',
            'description': 'You enter an old warehouse filled with rusted machinery and broken crates. The air is thick with the smell of oil and decay.',
            'exits': {
                'south': 'abandoned_building'
            }
        },
        'sewer_tunnels': {
            'title': 'Sewer Tunnels',
            'description': 'The sewer tunnels are dark and damp. Water flows through channels, and you can hear the distant rumble of the city above.',
            'exits': {
                'up': 'sewer_entrance',
                'north': 'flooded_chamber'
            }
        },
        'hidden_lab': {
            'title': 'Hidden Lab',
            'description': 'You discover a clandestine laboratory hidden in the underground. Beakers bubble and strange equipment hums with activity.',
            'exits': {
                'south': 'underground_market'
            }
        },
        'utility_room': {
            'title': 'Utility Room',
            'description': 'This utility room contains electrical panels and plumbing. The walls are lined with pipes and conduits.',
            'exits': {
                'down': 'maintenance_shaft'
            }
        },
        'flooded_chamber': {
            'title': 'Flooded Chamber',
            'description': 'This chamber is partially flooded with murky water. Strange shapes move in the depths, and the air is thick with humidity.',
            'exits': {
                'south': 'sewer_tunnels'
            }
        }
    }

    # Get current room from session
    current_room_id = session.get('current_alleyway_room', 'entrance')
    current_room = rooms.get(current_room_id, rooms['entrance'])

    # Check if this room can be searched
    if not ('secret' in current_room['title'].lower() or 'mysterious' in current_room['description'].lower() or 'hidden' in current_room['title'].lower()):
        flash("There's nothing special to search for here.", "info")
        return redirect(url_for('alleyway'))

    # Determine search result based on room and random chance
    search_result = random.random()

    if current_room_id == 'secret_room':
        # Secret room has better rewards but also traps
        if search_result < 0.1:  # 10% chance - trap
            damage = random.randint(15, 35)
            game_state.health = max(0, game_state.health - damage)
            result = f"You trigger a trap! A hidden spike pit injures you for {damage} damage!"
            flash(result, "danger")
        elif search_result < 0.3:  # 20% chance - weapon cache
            game_state.weapons.bullets += random.randint(10, 25)
            result = f"You find a hidden weapon cache! You gain {game_state.weapons.bullets} bullets!"
            flash(result, "success")
        elif search_result < 0.5:  # 20% chance - drug stash
            drug_types = ['weed', 'crack', 'coke']
            drug = random.choice(drug_types)
            amount = random.randint(2, 5)
            setattr(game_state.drugs, drug, getattr(game_state.drugs, drug) + amount)
            result = f"You discover a drug stash! You find {amount} kilos of {drug}!"
            flash(result, "success")
        elif search_result < 0.7:  # 20% chance - money
            money_found = random.randint(200, 800)
            game_state.money += money_found
            result = f"You find a hidden stash of cash! You gain ${money_found}!"
            flash(result, "success")
        else:  # 30% chance - nothing special
            result = "You search thoroughly but find nothing of value."
            flash(result, "info")

    elif current_room_id == 'hidden_entrance':
        # Hidden entrance has moderate rewards
        if search_result < 0.15:  # 15% chance - trap
            damage = random.randint(10, 25)
            game_state.health = max(0, game_state.health - damage)
            result = f"You disturb a sleeping rat colony! They attack you for {damage} damage!"
            flash(result, "danger")
        elif search_result < 0.4:  # 25% chance - small reward
            money_found = random.randint(50, 200)
            game_state.money += money_found
            result = f"You find some loose change and bills! You gain ${money_found}!"
            flash(result, "success")
        elif search_result < 0.6:  # 20% chance - ammo
            game_state.weapons.bullets += random.randint(5, 15)
            result = f"You find some discarded ammo! You gain {game_state.weapons.bullets} bullets!"
            flash(result, "success")
        else:  # 40% chance - nothing
            result = "The area looks like it's been searched before. Nothing here."
            flash(result, "info")

    elif current_room_id == 'underground':
        # Underground passage has mixed results
        if search_result < 0.2:  # 20% chance - trap
            damage = random.randint(20, 40)
            game_state.health = max(0, game_state.health - damage)
            result = f"You step on a pressure plate! Poison darts shoot out, dealing {damage} damage!"
            flash(result, "danger")
        elif search_result < 0.5:  # 30% chance - good reward
            if random.random() < 0.5:
                # Money
                money_found = random.randint(300, 600)
                game_state.money += money_found
                result = f"You find a waterproof bag with cash! You gain ${money_found}!"
            else:
                # Drugs
                drug_types = ['weed', 'crack']
                drug = random.choice(drug_types)
                amount = random.randint(3, 7)
                setattr(game_state.drugs, drug, getattr(game_state.drugs, drug) + amount)
                result = f"You find a hidden compartment with drugs! You gain {amount} kilos of {drug}!"
            flash(result, "success")
        else:  # 50% chance - minor find or nothing
            if random.random() < 0.3:
                game_state.weapons.bullets += random.randint(3, 8)
                result = f"You find a few loose bullets! You gain {game_state.weapons.bullets} bullets!"
                flash(result, "success")
            else:
                result = "The underground passage is damp and empty. Nothing of interest."
                flash(result, "info")

    else:
        # Generic secret areas
        if search_result < 0.25:  # 25% chance - trap
            damage = random.randint(5, 20)
            game_state.health = max(0, game_state.health - damage)
            result = f"You find a trap! You take {damage} damage!"
            flash(result, "danger")
        elif search_result < 0.6:  # 35% chance - small reward
            money_found = random.randint(25, 150)
            game_state.money += money_found
            result = f"You find some hidden money! You gain ${money_found}!"
            flash(result, "success")
        else:  # 40% chance - nothing
            result = "You search carefully but find nothing special."
            flash(result, "info")

    # Increment steps for searching
    game_state.steps += 1
    if game_state.steps >= game_state.max_steps:
        game_state.day += 1
        game_state.steps = 0

    save_game_state(game_state)
    return redirect(url_for('alleyway'))

@app.route('/move_room/<direction>')
def move_room(direction):
    """Move to a different room in the alleyway"""
    game_state = get_game_state()

    # Define alleyway rooms
    rooms = {
        'entrance': {
            'title': 'Dark Alley Entrance',
            'description': 'You stand at the entrance of a dark alleyway. The streetlights cast long shadows, and you can hear distant sounds echoing off the walls.',
            'exits': {
                'north': 'dead_end',
                'south': 'city',
                'east': 'side_street',
                'west': 'dumpster'
            }
        },
        'dead_end': {
            'title': 'Dead End',
            'description': 'You reach a dead end with graffiti-covered walls. There\'s nothing here but trash and shadows.',
            'exits': {
                'south': 'entrance'
            }
        },
        'side_street': {
            'title': 'Side Street',
            'description': 'You emerge onto a narrow side street. Cars occasionally drive by, and you see a few shady figures watching you.',
            'exits': {
                'west': 'entrance',
                'north': 'hidden_entrance',
                'east': 'abandoned_building'
            }
        },
        'dumpster': {
            'title': 'Behind the Dumpster',
            'description': 'You hide behind a large dumpster. The smell is awful, but you\'re well concealed. You find some discarded items.',
            'exits': {
                'east': 'entrance',
                'north': 'maintenance_shaft'
            }
        },
        'hidden_entrance': {
            'title': 'Hidden Entrance',
            'description': 'You find a hidden entrance to an underground network. This could lead to interesting places...',
            'exits': {
                'south': 'side_street',
                'down': 'underground',
                'east': 'sewer_entrance'
            }
        },
        'underground': {
            'title': 'Underground Passage',
            'description': 'You descend into a dimly lit underground passage. Water drips from the ceiling, and you hear echoes of distant footsteps.',
            'exits': {
                'up': 'hidden_entrance',
                'north': 'secret_room',
                'east': 'underground_market'
            }
        },
        'secret_room': {
            'title': 'Secret Room',
            'description': 'You enter a secret room filled with old crates and mysterious artifacts. There might be valuable items here.',
            'exits': {
                'south': 'underground',
                'west': 'storage_room'
            }
        },
        'abandoned_building': {
            'title': 'Abandoned Building',
            'description': 'You enter a crumbling abandoned building. The floors are covered in dust and debris, and you can hear rats scurrying in the walls.',
            'exits': {
                'west': 'side_street',
                'up': 'rooftop_access',
                'north': 'old_warehouse'
            }
        },
        'sewer_entrance': {
            'title': 'Sewer Entrance',
            'description': 'A rusty manhole cover leads down into the city\'s sewer system. The air smells of decay and chemicals.',
            'exits': {
                'west': 'hidden_entrance',
                'down': 'sewer_tunnels'
            }
        },
        'rooftop_access': {
            'title': 'Rooftop Access',
            'description': 'You climb a rickety ladder to the rooftop. The city lights spread out before you, and you can see other buildings nearby.',
            'exits': {
                'down': 'abandoned_building'
            }
        },
        'underground_market': {
            'title': 'Underground Market',
            'description': 'You stumble upon a hidden underground market. Shady merchants sell illegal goods under dim fluorescent lights.',
            'exits': {
                'west': 'underground',
                'north': 'hidden_lab'
            }
        },
        'storage_room': {
            'title': 'Storage Room',
            'description': 'This room is filled with old storage containers and forgotten equipment. Dust covers everything, but there might be valuables hidden here.',
            'exits': {
                'east': 'secret_room'
            }
        },
        'maintenance_shaft': {
            'title': 'Maintenance Shaft',
            'description': 'A narrow maintenance shaft runs along the alley. It\'s dark and cramped, but you can hear the hum of machinery nearby.',
            'exits': {
                'south': 'dumpster',
                'up': 'utility_room'
            }
        },
        'old_warehouse': {
            'title': 'Old Warehouse',
            'description': 'You enter an old warehouse filled with rusted machinery and broken crates. The air is thick with the smell of oil and decay.',
            'exits': {
                'south': 'abandoned_building'
            }
        },
        'sewer_tunnels': {
            'title': 'Sewer Tunnels',
            'description': 'The sewer tunnels are dark and damp. Water flows through channels, and you can hear the distant rumble of the city above.',
            'exits': {
                'up': 'sewer_entrance',
                'north': 'flooded_chamber'
            }
        },
        'hidden_lab': {
            'title': 'Hidden Lab',
            'description': 'You discover a clandestine laboratory hidden in the underground. Beakers bubble and strange equipment hums with activity.',
            'exits': {
                'south': 'underground_market'
            }
        },
        'utility_room': {
            'title': 'Utility Room',
            'description': 'This utility room contains electrical panels and plumbing. The walls are lined with pipes and conduits.',
            'exits': {
                'down': 'maintenance_shaft'
            }
        },
        'flooded_chamber': {
            'title': 'Flooded Chamber',
            'description': 'This chamber is partially flooded with murky water. Strange shapes move in the depths, and the air is thick with humidity.',
            'exits': {
                'south': 'sewer_tunnels'
            }
        }
    }

    # Get current room from session, default to entrance
    current_room_id = session.get('current_alleyway_room', 'entrance')

    # Get the exit for the given direction
    if current_room_id in rooms and direction in rooms[current_room_id]['exits']:
        next_room = rooms[current_room_id]['exits'][direction]
        if next_room == 'city':
            # Special case: exit to city
            session['current_alleyway_room'] = 'entrance'  # Reset for next time
            session.modified = True
            return redirect(url_for('city'))
        else:
            # Move to new room
            session['current_alleyway_room'] = next_room
            session.modified = True
    else:
        # Invalid direction, stay in current room
        pass

    # Increment steps for exploration
    game_state.steps += 1
    if game_state.steps >= game_state.max_steps:
        game_state.day += 1
        game_state.steps = 0

    # Check for NPC encounter in alleyway
    if random.random() < 0.2 and npcs_data:
        alley_npcs = [npc for npc in npcs_data.values() if npc['location'] == 'alleyway']
        if alley_npcs:
            npc = random.choice(alley_npcs)
            message = f"You encounter {npc['name']}! They look hostile..."
            # Start MUD fight with NPC
            enemy_health = npc.get('hp', 50)  # Default 50 HP if not specified
            enemy_type = npc['name']
            combat_active = True
            fight_log = [message]
            combat_id = f"npc_{list(npcs_data.keys())[list(npcs_data.values()).index(npc)]}_{random.randint(1000, 9999)}"
            return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=1, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id, npc_id=list(npcs_data.keys())[list(npcs_data.values()).index(npc)])

    save_game_state(game_state)

    return redirect(url_for('alleyway'))

@app.route('/new_game', methods=['GET', 'POST'])
def new_game():
    """Start a new game"""
    if request.method == 'POST':
        player_name = request.form.get('player_name', '').strip()
        gang_name = request.form.get('gang_name', '').strip()
        gender = request.form.get('gender', 'male')

        if not player_name or not gang_name:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('new_game'))

        # Initialize new game state
        game_state = GameState()
        game_state.player_name = player_name
        game_state.gang_name = gang_name
        game_state.current_score = 0  # Start with score 0
        # Note: gender is collected but not currently used in game logic

        # Initialize starting weapons
        game_state.weapons.pistols = 1
        game_state.weapons.bullets = 10
        game_state.weapons.knife = 1

        # Initialize gang_members list will be empty at start (just the player)

        # Ensure the game state is properly saved to session
        session['game_state'] = asdict(game_state)
        session.modified = True

        return redirect(url_for('city'))

    return render_template('new_game.html', game_state=get_game_state())

@app.route('/npc_interaction/<npc_id>')
def npc_interaction(npc_id):
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    npc = npcs_data[npc_id]
    game_state = get_game_state()
    return render_template('npc_interaction.html', npc=npc, action='encounter', message=f"You encounter {npc['name']}. {npc['description']}", game_state=game_state)

@app.route('/talk_to_npc/<npc_id>')
def talk_to_npc(npc_id):
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    npc = npcs_data[npc_id]
    game_state = get_game_state()
    message = f"{npc['name']} says: Hello, {game_state.player_name}. What can I do for you?"
    return render_template('npc_interaction.html', npc=npc, action='talk', message=message, game_state=game_state)

@app.route('/look_at_npc/<npc_id>')
def look_at_npc(npc_id):
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    npc = npcs_data[npc_id]
    game_state = get_game_state()
    message = f"You look closely at {npc['name']}. {npc['description']}"
    return render_template('npc_interaction.html', npc=npc, action='look', message=message, game_state=game_state)

@app.route('/trade_with_npc/<npc_id>')
def trade_with_npc(npc_id):
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    npc = npcs_data[npc_id]
    game_state = get_game_state()
    return render_template('npc_trade.html', npc=npc, game_state=game_state)

@app.route('/npc_trade_action/<npc_id>', methods=['POST'])
def npc_trade_action(npc_id):
    if npc_id not in npcs_data:
        return redirect(url_for('city'))

    npc = npcs_data[npc_id]
    game_state = get_game_state()
    action = request.form.get('action')
    item_type = request.form.get('item_type')
    quantity = int(request.form.get('quantity', 1))

    if action == 'buy':
        # NPC selling to player
        if item_type not in game_state.drug_prices:
            flash("Invalid item type!", "danger")
            return redirect(url_for('trade_with_npc', npc_id=npc_id))

        # Check if NPC has the item (simulate NPC inventory)
        npc_drugs = npc.get('drugs', {})
        npc_amount = npc_drugs.get(item_type, 0)

        if npc_amount < quantity:
            flash(f"{npc['name']} doesn't have enough {item_type}!", "danger")
            return redirect(url_for('trade_with_npc', npc_id=npc_id))

        price = game_state.drug_prices[item_type]
        # NPCs sell at 150% of base price
        sell_price = int(price * 1.5)
        total_cost = sell_price * quantity

        if game_state.money < total_cost:
            flash(f"You don't have enough money! Need ${total_cost:,}.", "danger")
            return redirect(url_for('trade_with_npc', npc_id=npc_id))

        # Complete the transaction
        game_state.money -= total_cost
        setattr(game_state.drugs, item_type, getattr(game_state.drugs, item_type) + quantity)

        # Update NPC inventory (simulate)
        npc_drugs[item_type] = npc_amount - quantity
        npc['drugs'] = npc_drugs

        flash(f"You bought {quantity} kilo(s) of {item_type} from {npc['name']} for ${total_cost:,}!", "success")

    elif action == 'sell':
        # Player selling to NPC
        if item_type not in game_state.drug_prices:
            flash("Invalid item type!", "danger")
            return redirect(url_for('trade_with_npc', npc_id=npc_id))

        current_qty = getattr(game_state.drugs, item_type)
        if current_qty < quantity:
            flash(f"You don't have enough {item_type} to sell!", "danger")
            return redirect(url_for('trade_with_npc', npc_id=npc_id))

        price = game_state.drug_prices[item_type]
        # NPCs buy at 50% of base price
        buy_price = int(price * 0.5)
        total_revenue = buy_price * quantity

        # Complete the transaction
        game_state.money += total_revenue
        setattr(game_state.drugs, item_type, current_qty - quantity)

        # Update NPC inventory (simulate)
        npc_drugs = npc.get('drugs', {})
        npc_drugs[item_type] = npc_drugs.get(item_type, 0) + quantity
        npc['drugs'] = npc_drugs

        flash(f"You sold {quantity} kilo(s) of {item_type} to {npc['name']} for ${total_revenue:,}!", "success")

    # Save game state and NPC data
    save_game_state(game_state)

    # Save updated NPC data
    npc_file = os.path.join(os.path.dirname(__file__), '..', 'model', 'npcs.json')
    with open(npc_file, 'w') as f:
        json.dump(npcs_data, f, indent=2)

    return redirect(url_for('trade_with_npc', npc_id=npc_id))

@app.route('/fight_npc/<npc_id>', methods=['POST'])
def fight_npc(npc_id):
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    npc = npcs_data[npc_id]
    game_state = get_game_state()
    message = f"You engage in combat with {npc['name']}!"
    # Start MUD fight with NPC
    enemy_health = npc.get('hp', 50)  # Default 50 HP if not specified
    max_enemy_hp = npc.get('max_hp', 50)  # Default 50 max HP if not specified
    enemy_type = npc['name']
    combat_active = True
    fight_log = [message]
    combat_id = f"npc_{npc_id}_{random.randint(1000, 9999)}"
    return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, max_enemy_hp=max_enemy_hp, enemy_type=enemy_type, enemy_count=1, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id, npc_id=npc_id)

@app.route('/pickup_loot/<npc_id>')
def pickup_loot(npc_id):
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    npc = npcs_data[npc_id]
    game_state = get_game_state()
    if not npc['is_alive']:
        game_state.money += 100
        message = f"You search {npc['name']}'s body and find $100!"
    else:
        message = "You can't loot a living person."
    save_game_state(game_state)
    return render_template('npc_interaction.html', npc=npc, action='loot', message=message, game_state=game_state)

@app.route('/attempt_flee_npc/<npc_id>')
def attempt_flee_npc(npc_id):
    """Attempt to flee from an NPC encounter - might fail!"""
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    npc = npcs_data[npc_id]
    game_state = get_game_state()
    
    # 50% chance to flee successfully
    if random.random() < 0.5:
        flash("You managed to escape!", "success")
        save_game_state(game_state)
        return redirect(url_for('city'))
    else:
        # Failed to flee - NPC attacks!
        damage = random.randint(5, 15)
        game_state.damage += damage
        flash(f"You tried to flee but {npc['name']} caught you! You take {damage} damage!", "danger")
        
        if game_state.damage >= 30:
            # Player is defeated
            game_state.lives -= 1
            game_state.damage = 0
            game_state.health = 30
            if game_state.lives <= 0:
                save_game_state(game_state)
                return render_template('fight_defeat.html', game_state=game_state, enemy_type=npc['name'], enemy_count=1, fight_log=[f"You have been defeated by {npc['name']}!"], final_damage=damage)
            else:
                flash(f"You survived but lost a life! {game_state.lives} lives remaining.", "warning")
        
        save_game_state(game_state)
        return render_template('npc_interaction.html', npc=npc, action='encounter', 
                             message=f"You encountered {npc['name']}. {npc['description']}", 
                             game_state=game_state)

# ============
# NPC Dialogue System
# ============

# Load dialogues from JSON file
def load_npc_dialogues():
    """Load NPC dialogues from JSON file"""
    try:
        dialogue_file = os.path.join(os.path.dirname(__file__), '..', 'model', 'npc_dialogues.json')
        with open(dialogue_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading NPC dialogues: {e}")
        return {}

# Load dialogues at module level
NPC_DIALOGUES = load_npc_dialogues()


@app.route('/npc_dialogue/<npc_id>')
def npc_dialogue(npc_id):
    """Start a dialogue with an NPC"""
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    npc = npcs_data[npc_id]
    game_state = get_game_state()
    
    # Get dialogue for this NPC
    if npc_id in NPC_DIALOGUES:
        dialogue_data = NPC_DIALOGUES[npc_id]
        greeting = random.choice(dialogue_data['greetings'])
        topics = list(dialogue_data['topics'].keys())
    else:
        greeting = f"{npc['name']} looks at you. 'What do you want?'"
        topics = []
        dialogue_data = None
    
    return render_template('npc_dialogue.html', npc=npc, greeting=greeting, topics=topics, dialogue_data=dialogue_data, game_state=game_state)

@app.route('/npc_dialogue/<npc_id>/topic/<topic>')
def npc_dialogue_topic(npc_id, topic):
    """Handle NPC dialogue topic selection"""
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    npc = npcs_data[npc_id]
    game_state = get_game_state()
    
    if npc_id not in NPC_DIALOGUES:
        flash("This NPC doesn't have dialogue options.", "info")
        return redirect(url_for('city'))
    
    dialogue_data = NPC_DIALOGUES[npc_id]
    
    if topic not in dialogue_data['topics']:
        flash("Invalid dialogue topic.", "warning")
        return redirect(url_for('npc_dialogue', npc_id=npc_id))
    
    topic_data = dialogue_data['topics'][topic]
    question = topic_data['question']
    responses = topic_data['responses']
    
    return render_template('npc_dialogue_topic.html', npc=npc, topic=topic, question=question, responses=responses, game_state=game_state)

@app.route('/npc_dialogue/<npc_id>/respond', methods=['POST'])
def npc_dialogue_respond(npc_id):
    """Handle NPC dialogue response selection"""
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    
    game_state = get_game_state()
    response_index = int(request.form.get('response_index', 0))
    topic = request.form.get('topic', '')
    
    if npc_id not in NPC_DIALOGUES:
        flash("Invalid NPC.", "warning")
        return redirect(url_for('city'))
    
    dialogue_data = NPC_DIALOGUES[npc_id]
    
    if topic not in dialogue_data['topics']:
        flash("Invalid topic.", "warning")
        return redirect(url_for('npc_dialogue', npc_id=npc_id))
    
    topic_data = dialogue_data['topics'][topic]
    responses = topic_data['responses']
    
    if response_index >= len(responses):
        flash("Invalid response selection.", "warning")
        return redirect(url_for('npc_dialogue_topic', npc_id=npc_id, topic=topic))
    
    selected_response = responses[response_index]
    response_text = selected_response['text']
    cost = selected_response.get('cost', 0)
    effect = selected_response.get('effect', None)
    
    # Handle cost
    if cost > 0:
        if game_state.money >= cost:
            game_state.money -= cost
            flash(f"You paid ${cost} for information.", "info")
        else:
            flash(f"You can't afford the ${cost} cost for this information!", "danger")
            return redirect(url_for('npc_dialogue_topic', npc_id=npc_id, topic=topic))
    
    # Handle effects
    if effect == 'has_info':
        game_state.flags.has_info = True
        flash("You gained valuable information!", "success")
    elif effect == 'lose_id':
        game_state.flags.has_id = False
        flash("You lost your fake ID!", "danger")
    
    save_game_state(game_state)
    
    return render_template('npc_dialogue_response.html', npc=npcs_data[npc_id], response=response_text, topic=topic, game_state=game_state)

@app.route('/npcs')
def npcs():
    """View NPCs in current location"""
    game_state = get_game_state()
    location_npcs = [npc for npc in npcs_data.values() if npc.get('location') == game_state.current_location]
    return render_template('npcs.html', npcs=location_npcs, game_state=game_state)

@app.route('/cop_chase')
def cop_chase():
    """Police chase encounter - redirect to MUD fight system"""
    game_state = get_game_state()
    num_cops = random.randint(2, 6)
    message = f"Oh no! {num_cops} police officers spot you and give chase!"
    # Initialize MUD fight variables
    enemy_health = num_cops * 10  # Each cop has 10 health
    enemy_type = f"{num_cops} Police Officers"
    combat_active = True
    fight_log = [message]
    combat_id = f"police_{random.randint(1000, 9999)}"
    return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=num_cops, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)

@app.route('/fight_cops', methods=['POST'])
def fight_cops():
    """Handle police fight actions"""
    game_state = get_game_state()
    action = request.form.get('action')
    weapon = request.form.get('weapon')
    num_cops = int(request.form.get('num_cops', 2))

    if action == 'run':
        # Try to escape
        escape_chance = random.random()
        if escape_chance < 0.5:  # 50% chance to escape
            flash("You manage to escape the police chase!", "success")
            # Chance to recruit a impressed bystander
            if random.random() < 0.2:  # 20% chance
                game_state.members += 1
                game_state.health = min(game_state.max_health, game_state.health + 10)
                flash("A bystander was impressed by your escape and joined your gang!", "success")
            save_game_state(game_state)
            return redirect(url_for('city'))
        else:
            # Failed to escape, take damage
            damage = random.randint(10, 30)
            if game_state.weapons.vest > 0:
                game_state.weapons.vest -= 1
                damage = max(0, damage - 20)  # Vest reduces damage
                message = f"You failed to escape! Your vest absorbed some damage but you still took {damage} damage."
            else:
                message = f"You failed to escape and took {damage} damage from police gunfire!"

            game_state.damage += damage
            if game_state.damage >= 30:
                game_state.lives -= 1
                final_damage = game_state.damage  # Store before resetting
                game_state.damage = 0
                game_state.health = 30
                enemy_type = f"{num_cops} Police Officers"
                enemy_count = num_cops
                fight_log = [message]
                if game_state.lives <= 0:
                    save_game_state(game_state)
                    return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, fight_log=fight_log, final_damage=final_damage)
                else:
                    save_game_state(game_state)
                    return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, fight_log=fight_log, final_damage=final_damage)

            # Return to MUD fight with updated state
            enemy_health = num_cops * 10
            enemy_type = f"{num_cops} Police Officers"
            combat_active = True
            fight_log = [message]
            combat_id = f"police_{random.randint(1000, 9999)}"
            return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=num_cops, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)

    elif action == 'shoot':
        # Combat with police
        if weapon == 'pistol' and game_state.weapons.bullets > 0:
            game_state.weapons.bullets -= 1
            cops_killed = min(num_cops, random.randint(1, 3))
            num_cops -= cops_killed

            # Police shoot back
            damage = random.randint(5, 25) * (num_cops if num_cops > 0 else 1)
            if game_state.weapons.vest > 0:
                game_state.weapons.vest -= 1
                damage = max(0, damage - 20)

            game_state.damage += damage

            if num_cops <= 0:
                flash(f"You killed all the cops and escaped! {cops_killed} officers down!", "success")
                save_game_state(game_state)
                return redirect(url_for('city'))
            else:
                message = f"You killed {cops_killed} cop(s) but {num_cops} remain and shot back! You took {damage} damage."
                if game_state.damage >= 30:
                    game_state.lives -= 1
                    final_damage = game_state.damage  # Store before resetting
                    game_state.damage = 0
                    game_state.health = 30
                    enemy_type = f"{num_cops} Police Officers"
                    enemy_count = num_cops
                    fight_log = [message]
                    if game_state.lives <= 0:
                        save_game_state(game_state)
                        return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, fight_log=fight_log, final_damage=final_damage)
                    else:
                        save_game_state(game_state)
                        return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, fight_log=fight_log, final_damage=final_damage)



        elif weapon == 'grenade' and game_state.weapons.grenades > 0:
            game_state.weapons.grenades -= 1
            cops_killed = min(num_cops, random.randint(3, 6))
            num_cops -= cops_killed

            if num_cops <= 0:
                flash(f"Grenade explosion! {cops_killed} cops eliminated!", "success")
                save_game_state(game_state)
                return redirect(url_for('city'))
            else:
                damage = random.randint(20, 50)
                if game_state.weapons.vest > 0:
                    game_state.weapons.vest -= 1
                    damage = max(0, damage - 20)
                game_state.damage += damage
                message = f"Grenade blast killed {cops_killed} cops but you're hurt too! {damage} damage."

        elif weapon == 'missile_launcher' and game_state.weapons.missiles > 0:
            game_state.weapons.missiles -= 1
            cops_killed = num_cops  # Missile kills all remaining cops
            num_cops = 0

            damage = random.randint(30, 60)
            if game_state.weapons.vest > 0:
                game_state.weapons.vest -= 1
                damage = max(0, damage - 20)
            game_state.damage += damage

            flash(f"RPG blast! All {cops_killed} cops eliminated!", "success")
            save_game_state(game_state)
            return redirect(url_for('city'))

        elif weapon == 'knife':
            damage_to_player = random.randint(15, 35) * num_cops
            if game_state.weapons.vest > 0:
                game_state.weapons.vest -= 1
                damage_to_player = max(0, damage_to_player - 20)
            game_state.damage += damage_to_player
            message = f"You tried to fight with a knife but got overwhelmed! {damage_to_player} damage from {num_cops} cops."

        elif weapon == 'vampire_bat' and game_state.weapons.vampire_bat > 0:
            cops_killed = min(num_cops, random.randint(1, 2))  # Vampire bat kills 1-2 cops
            num_cops -= cops_killed

            damage = random.randint(5, 25) * (num_cops if num_cops > 0 else 1)
            if game_state.weapons.vest > 0:
                game_state.weapons.vest -= 1
                damage = max(0, damage - 20)
            game_state.damage += damage

            if num_cops <= 0:
                flash(f"You beat the cops senseless with your vampire bat! {cops_killed} officers down!", "success")
                save_game_state(game_state)
                return redirect(url_for('city'))
            else:
                message = f"You smashed {cops_killed} cop(s) with your vampire bat but {num_cops} remain! You took {damage} damage."

        # Check if player died
        if game_state.damage >= 30:
            game_state.lives -= 1
            final_damage = game_state.damage  # Store before resetting
            game_state.damage = 0
            game_state.health = 30
            enemy_type = f"{num_cops} Police Officers"
            enemy_count = num_cops
            fight_log = [message] if 'message' in locals() else ["Combat with police officers"]
            if game_state.lives <= 0:
                save_game_state(game_state)
                return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, fight_log=fight_log, final_damage=final_damage)
            else:
                save_game_state(game_state)
                return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, fight_log=fight_log, final_damage=final_damage)

        # Return to MUD fight with updated state
        enemy_health = num_cops * 10
        enemy_type = f"{num_cops} Police Officers"
        combat_active = True
        fight_log = [message] if 'message' in locals() else ["Combat continues..."]
        combat_id = f"police_{random.randint(1000, 9999)}"
        return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=num_cops, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)

    save_game_state(game_state)
    return redirect(url_for('city'))

@app.route('/process_fight_action', methods=['POST'])
def process_fight_action():
    """Handle MUD-style fight actions"""
    game_state = get_game_state()
    combat_id = request.form.get('combat_id')
    action = request.form.get('action')
    weapon = request.form.get('weapon', 'pistol')
    ammo = request.form.get('ammo', 'normal')
    drug = request.args.get('drug')

    # Check if this is an AJAX request - proper detection
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/x-www-form-urlencoded'
    print(f"process_fight_action called: action={action}, weapon={weapon}, is_ajax={is_ajax}")
    print(f"Player weapons: knife={game_state.weapons.knife}, pistol={game_state.weapons.pistols}, bullets={game_state.weapons.bullets}")

    # Get combat state from session (simplified - in real implementation you'd store full combat state)
    enemy_health = int(request.form.get('enemy_health', 30))
    enemy_type = request.form.get('enemy_type', 'Enemy')
    enemy_count = int(request.form.get('enemy_count', 1))
    fight_log = list(dict.fromkeys(request.form.getlist('fight_log'))) or ["Combat begins!"]

    print(f"Enemy health before: {enemy_health}, fight_log length: {len(fight_log)}")

    # Process action
    print(f"Processing action: {action}, weapon: {weapon}, fight_log before: {len(fight_log)}")
    if action == 'attack':
        print("Entered attack action")
        use_exploding = ammo == 'exploding' and weapon in ['pistol', 'ghost_gun', 'ar15'] and game_state.weapons.exploding_bullets > 0
        use_hollow_point = ammo == 'hollow_point' and weapon in ['pistol', 'ghost_gun', 'ar15'] and game_state.weapons.hollow_point_bullets > 0

        # Get weapon-specific attack descriptions
        attack_descriptions = {
            'pistol': [
                "You squeeze off a precise shot from your pistol, the barrel flashing as the bullet screams toward your target!",
                "Your pistol bucks in your hand as you fire, sending a slug hurtling through the air with deadly intent!",
                "You line up the sights and pull the trigger, your pistol roaring as it launches death toward your enemy!",
                "With practiced precision, you fire your pistol, the shot echoing like thunder in the confined space!",
                "Your finger tightens on the trigger, unleashing a devastating round that finds its mark unerringly!"
            ],
            'ghost_gun': [
                "Your ghost gun whispers death in silence, the untraceable shot eliminating your target with surgical precision!",
                "The ghost gun does its deadly work, firing a shot that leaves no evidence but a corpse cooling on the ground!",
                "You employ the untraceable firearm, its muffled report barely audible as it extinguishes another life!",
                "The ghost gun lives up to its name, firing a shot that disappears like smoke, leaving only death behind!",
                "Your untraceable weapon speaks volumes in silence, the shot finding its target with lethal accuracy!"
            ],
            'ar15': [
                "You unleash a burst from your AR-15, the rifle chattering like an angry mechanical demon!",
                "The AR-15 roars in your hands, spitting a stream of lead that tears through your enemies!",
                "You squeeze the trigger and your AR-15 responds with fury, unleashing a hailstorm of bullets!",
                "Your assault rifle bucks against your shoulder as it unleashes controlled devastation on your foes!",
                "The AR-15 sings its song of destruction, each burst finding targets with mechanical precision!"
            ],
            'exploding_bullets': [
                "You fire an exploding bullet that detonates on impact, shredding flesh and bone in a horrific explosion!",
                "The exploding round screams toward your target and erupts in a devastating blast of shrapnel and fire!",
                "Your special ammunition detonates with terrifying force, turning your enemy into a cloud of blood and gore!",
                "The exploding bullet finds its mark and unleashes hell, the detonation ripping through everything in its path!",
                "You watch as your explosive projectile impacts and erupts, painting the surroundings in crimson destruction!"
            ],
            'hollow_point_bullets': [
                "You fire a hollow point bullet that expands on impact, creating devastating wound channels!",
                "The hollow point round mushrooms dramatically as it strikes, maximizing tissue damage and stopping power!",
                "Your specialized ammunition fragments inside the target, causing massive internal trauma and blood loss!",
                "The hollow point bullet transfers all its energy into the target, creating a devastating hydrostatic shock!",
                "You watch as the hollow point round creates a devastating exit wound, the bullet having expanded to three times its size!"
            ],
            'grenade': [
                "You hurl a grenade that bounces toward your enemies, the fuse hissing as it counts down to oblivion!",
                "The grenade leaves your hand in a perfect arc, exploding in a shower of deadly shrapnel moments later!",
                "You cook off a grenade and throw it, the explosion ripping through your enemies like divine judgment!",
                "Your grenade finds its target and detonates with earth-shaking force, scattering foes like broken dolls!",
                "The grenade explodes in a cataclysm of fire and metal, leaving nothing but silence and death in its wake!"
            ],
            'missile_launcher': [
                "You fire the missile launcher, the rocket screaming toward your target like the wrath of an angry god!",
                "The missile streaks from the launcher, its contrail marking a path of inevitable destruction!",
                "You unleash hell with the missile launcher, the projectile reducing everything in its path to rubble!",
                "The rocket-propelled death leaves your launcher, homing in on your enemies with mechanical precision!",
                "Your missile finds its mark and detonates in a massive explosion that shakes the very foundations!"
            ],
            'barbed_wire_bat': [
                "You swing your barbed wire bat with savage force, the cruel spikes tearing through flesh and bone!",
                "The barbed wire-wrapped bat connects with devastating impact, ripping and tearing everything it touches!",
                "You bring the brutal weapon down in a crushing arc, the barbed wire leaving trails of blood and agony!",
                "Your spiked bat finds its target, the barbs digging deep and tearing flesh in a symphony of pain!",
                "The barbed wire bat swings in a deadly arc, connecting with bone-crunching force and horrific tearing!"
            ],
            'knife': [
                "You lunge forward with your knife, the blade flashing as it seeks out vital arteries and organs!",
                "Your knife strikes with surgical precision, slipping between ribs to find the enemy's beating heart!",
                "You drive the blade home with lethal force, twisting and tearing through flesh and muscle!",
                "The knife finds its mark in a spray of crimson, your strike both swift and merciless!",
                "You stab with calculated brutality, the blade drinking deep of your enemy's lifeblood!"
            ]
        }

        # Handle weapon attacks with enhanced descriptions
        if weapon == 'pistol' and game_state.weapons.pistols > 0 and game_state.weapons.bullets > 0:
            game_state.weapons.bullets -= 1
            base_damage = random.randint(15, 25)
            # Add ±30% damage variance per shot (making each swing truly random)
            damage_variance = random.uniform(0.7, 1.3)
            base_damage = int(base_damage * damage_variance)
            if use_exploding:
                game_state.weapons.exploding_bullets -= 1
                base_damage *= 2  # Exploding bullet doubles damage
            elif use_hollow_point:
                game_state.weapons.hollow_point_bullets -= 1
                base_damage = int(base_damage * 1.2)  # Hollow point bullets are 20% stronger
            if game_state.weapons.pistol_automatic:
                # Automatic pistol fires 3 shots - show each shot separately
                total_damage = 0
                for shot in range(3):
                    shot_damage = base_damage
                    total_damage += shot_damage
                    attack_desc = random.choice(attack_descriptions.get('pistol', ["You fire your automatic pistol!"]))
                    ammo_type = ""
                    if use_exploding:
                        ammo_type = " (exploding bullet!)"
                    elif use_hollow_point:
                        ammo_type = " (hollow point bullet!)"
                    fight_log.append(f"{attack_desc} [Shot {shot + 1}] You deal {shot_damage} damage{ammo_type}!")
                ammo_desc = ""
                if use_exploding:
                    ammo_desc = " (exploding bullets have devastating effect!)"
                elif use_hollow_point:
                    ammo_desc = " (hollow point bullets maximize damage!)"
                fight_log.append(f"Total damage from automatic pistol: {total_damage} damage{ammo_desc}!")
            else:
                damage = base_damage
                attack_desc = random.choice(attack_descriptions.get('pistol', ["You fire your pistol!"]))
                ammo_type = ""
                if use_exploding:
                    ammo_type = " (exploding bullet!)"
                elif use_hollow_point:
                    ammo_type = " (hollow point bullet!)"
                fight_log.append(f"{attack_desc} You deal {damage} damage{ammo_type}!")
            enemy_health -= damage if not game_state.weapons.pistol_automatic else total_damage
        elif weapon == 'ar15' and game_state.weapons.ar15 > 0 and game_state.weapons.bullets > 0:
            game_state.weapons.bullets -= 1
            base_damage = random.randint(25, 45)
            # Add ±30% damage variance per shot (making each swing truly random)
            damage_variance = random.uniform(0.7, 1.3)
            damage = int(base_damage * damage_variance)
            if use_exploding:
                game_state.weapons.exploding_bullets -= 1
                damage *= 2  # Exploding bullet doubles damage
            elif use_hollow_point:
                game_state.weapons.hollow_point_bullets -= 1
                damage = int(damage * 1.2)  # Hollow point bullets are 20% stronger
            enemy_health -= damage
            ammo_desc = ""
            if use_exploding:
                ammo_desc = " (exploding ammunition shreds through!)"
            elif use_hollow_point:
                ammo_desc = " (hollow point bullets maximize damage!)"
            fight_log.append(f"You fire your AR-15 and deal {damage} damage{ammo_desc}!")
        elif weapon == 'ghost_gun' and game_state.weapons.ghost_guns > 0 and game_state.weapons.bullets > 0:
            game_state.weapons.bullets -= 1
            base_damage = random.randint(15, 25)
            # Ghost gun jam chance - 30% chance to jam
            if random.random() < 0.3:
                # When ghost gun jams, 5% chance it EXPLODES in your face
                if random.random() < 0.05:
                    # GHOST GUN EXPLOSION - lose weapon and take damage!
                    explosion_damage = random.randint(5, 20)
                    game_state.damage += explosion_damage
                    # Lose the ghost gun!
                    game_state.weapons.ghost_guns = max(0, game_state.weapons.ghost_guns - 1)
                    
                    # Bloody explosion descriptions
                    explosion_descriptions = [
                        f"CATASTROPHIC FAILURE! Your ghost gun explodes in a shower of molten metal and burning propellant! The blast chars your face and hands with sizzling burns, sending jagged shards of the weapon tearing through your flesh!",
                        f"OH GOD! The ghost gun backfires with terrifying force, the weapon shattering into a thousand red-hot fragments that embed themselves deep in your arm! Blood and burning oil spray across your chest as you scream in agony!",
                        f"FIRE IN THE HOLE! Your ghost gun's chamber ruptures in a thunderous explosion! Your hand is reduced to a bloody pulp, fingers blown completely off as the weapon disintegrates in your grip!",
                        f"MERCIFUL MOTHER OF GOD! The ghost gun detonates, sending a cone of molten steel and shattered casing into your face! Your cheek is ripped clean off, exposing raw, bleeding muscle beneath!",
                        f"THE GUN JUST BLEW UP! A gout of flame erupts from the breach, engulfing your arm in burning gases! Your flesh sizzles and blackens as the weapon tears itself apart in a spray of blood and twisted metal!"
                    ]
                    fight_log.append(random.choice(explosion_descriptions))
                    fight_log.append(f"YOUR GHOST GUN IS DESTROYED! You take {explosion_damage} damage and the weapon is lost forever!")
                    damage = 0
                else:
                    fight_log.append("Your ghost gun jammed! No damage dealt.")
                    damage = 0
            else:
                if use_exploding:
                    game_state.weapons.exploding_bullets -= 1
                    base_damage *= 2  # Exploding bullet doubles damage
                if game_state.weapons.ghost_gun_automatic:
                    # Automatic ghost gun fires 3 shots - show each shot separately
                    total_damage = 0
                    for shot in range(3):
                        shot_damage = base_damage
                        total_damage += shot_damage
                        attack_desc = random.choice(attack_descriptions.get('ghost_gun', ["You fire your automatic ghost gun!"]))
                        fight_log.append(f"{attack_desc} [Burst {shot + 1}] You deal {shot_damage} damage{' (exploding bullet!)' if use_exploding else ''}!")
                    fight_log.append(f"Total damage from automatic ghost gun: {total_damage} damage{' (exploding bullets have devastating effect!)' if use_exploding else ''}!")
                    damage = total_damage
                else:
                    damage = base_damage
                    attack_desc = random.choice(attack_descriptions.get('ghost_gun', ["You fire your ghost gun!"]))
                    fight_log.append(f"{attack_desc} You deal {damage} damage{' (exploding bullet!)' if use_exploding else ''}!")
            enemy_health -= damage
        elif weapon == 'grenade' and game_state.weapons.grenades > 0:
            game_state.weapons.grenades -= 1
            damage = random.randint(30, 60)
            enemy_health -= damage
            fight_log.append(f"You throw a grenade and deal {damage} damage!")
        elif weapon == 'missile_launcher' and game_state.weapons.missile_launcher > 0 and game_state.weapons.missiles > 0:
            game_state.weapons.missiles -= 1
            damage = random.randint(50, 100)
            enemy_health -= damage
            fight_log.append(f"You fire a missile and deal {damage} damage!")
        elif weapon == 'vampire_bat' and game_state.weapons.vampire_bat > 0:
            # Vampire bat gets 4 swings - show each swing separately
            total_damage = 0
            for swing in range(4):
                # Random damage per swing: 20-50 (more variance)
                base_swing_damage = random.randint(20, 50)
                # Add ±30% damage variance per swing
                damage_variance = random.uniform(0.7, 1.3)
                swing_damage = int(base_swing_damage * damage_variance)
                total_damage += swing_damage
                attack_desc = random.choice(attack_descriptions.get('barbed_wire_bat', ["You swing your vampire bat!"]))
                fight_log.append(f"{attack_desc} [Swing {swing + 1}] You deal {swing_damage} damage!")
            fight_log.append(f"Total damage from vampire bat: {total_damage} damage!")
            damage = total_damage
            enemy_health -= damage
        elif weapon == 'knife' and game_state.weapons.knife > 0:
            # Knife gets 5 attacks per turn with increased miss chance
            total_damage = 0
            for stab in range(5):
                # 15% miss chance per stab (increased from ~0%)
                if random.random() < 0.15:
                    attack_desc = random.choice(attack_descriptions.get('knife', ["You swing your knife!"]))
                    fight_log.append(f"{attack_desc} [Stab {stab + 1}] You MISS completely!")
                else:
                    # Random damage per stab: 8-25 (more variance)
                    base_stab_damage = random.randint(8, 25)
                    # Add ±25% damage variance per stab
                    damage_variance = random.uniform(0.75, 1.25)
                    stab_damage = int(base_stab_damage * damage_variance)
                    total_damage += stab_damage
                    attack_desc = random.choice(attack_descriptions.get('knife', ["You stab with your knife!"]))
                    fight_log.append(f"{attack_desc} [Stab {stab + 1}] You deal {stab_damage} damage!")
            fight_log.append(f"Total damage from knife: {total_damage} damage!")
            damage = total_damage
            enemy_health -= damage
        elif weapon == 'sword' and game_state.weapons.sword > 0:
            damage = random.randint(50, 80)
            enemy_health -= damage
            fight_log.append(f"You slash with your sword and deal {damage} damage!")
        elif weapon == 'axe' and game_state.weapons.axe > 0:
            damage = random.randint(60, 90)
            enemy_health -= damage
            fight_log.append(f"You swing your mighty axe and deal {damage} damage!")
        elif weapon == 'golden_gun' and game_state.weapons.golden_gun > 0:
            # Golden gun deals massive damage but has a chance to jam
            if random.random() < 0.1:  # 10% chance to jam
                fight_log.append("Your golden gun JAMMED! No damage dealt, but it's still beautiful.")
            else:
                damage = random.randint(80, 120)  # Massive damage
                enemy_health -= damage
                fight_log.append(f"You fire the GOLDEN GUN and deal {damage} damage! It's truly magnificent!")
        elif weapon == 'poison_blowgun' and game_state.weapons.poison_blowgun > 0:
            # Poison blowgun with dart delay effect
            damage = random.randint(10, 20)  # Initial low damage
            enemy_health -= damage
            fight_log.append(f"You blow a poisoned dart and deal {damage} damage! The poison begins to take effect...")
            # Poison damage over time - this would need to be handled in multiple turns in a full implementation
            # For now, just add additional damage
            poison_damage = random.randint(15, 30)
            # Since this is single-turn combat, we'll apply poison damage immediately
            enemy_health -= poison_damage
            fight_log.append(f"The poison coursing through their veins deals an additional {poison_damage} damage!")
        elif weapon == 'chain_whip' and game_state.weapons.chain_whip > 0:
            damage = random.randint(40, 70)
            enemy_health -= damage
            fight_log.append(f"You whip your chain with deadly force and deal {damage} damage!")
        elif weapon == 'plasma_cutter' and game_state.weapons.plasma_cutter > 0:
            damage = random.randint(70, 100)
            enemy_health -= damage
            fight_log.append(f"You slice through your enemy with the plasma cutter and deal {damage} damage!")
        else:
            fight_log.append("You don't have that weapon or ammo!")
            print(f"DEBUG: Weapon {weapon} not available or no ammo")

        print(f"DEBUG: After attack - enemy_health={enemy_health}, fight_log length={len(fight_log)}")

        # Gang members attack if available - each uses ONE weapon per turn
        if game_state.members > 1:
            # Track which weapons are available for gang members
            available_weapons = []
            if game_state.weapons.pistols > 0 and game_state.weapons.bullets > 0:
                available_weapons.append('pistol')
            if game_state.weapons.ar15 > 0 and game_state.weapons.bullets > 0:
                available_weapons.append('ar15')
            if game_state.weapons.ghost_guns > 0 and game_state.weapons.bullets > 0:
                available_weapons.append('ghost_gun')
            if game_state.weapons.knife > 0:
                available_weapons.append('knife')
            if game_state.weapons.vampire_bat > 0:
                available_weapons.append('vampire_bat')

            # Each gang member gets one weapon to use this turn
            for member_num in range(1, game_state.members):  # Start from 1 since player is member 0
                member_weapon = None
                member_damage = 0

                # Member names
                member_names = [
                    f"Squad Member {member_num}",
                    f"Your Lieutenant {member_num}",
                    f"Gang Member #{member_num}",
                    f"Your Enforcer {member_num}",
                    f"Squad Soldier {member_num}"
                ]
                member_name = random.choice(member_names)

                # Assign weapon to this member - gang members use weapons WITHOUT depleting player's inventory
                # Each member uses their best available weapon with strongest ammo
                if available_weapons:
                    member_weapon = random.choice(available_weapons)  # Random weapon for flavor, no consumption
                else:
                    # No weapons available - member uses fists
                    member_weapon = 'fists'

                # Determine ammo type for gang members - use strongest available
                member_ammo_type = 'normal'
                if game_state.weapons.exploding_bullets > 0:
                    member_ammo_type = 'exploding'
                    game_state.weapons.exploding_bullets -= 1
                elif game_state.weapons.hollow_point_bullets > 0:
                    member_ammo_type = 'hollow_point'
                    game_state.weapons.hollow_point_bullets -= 1
                elif game_state.weapons.bullets > 0:
                    game_state.weapons.bullets -= 1

                # Calculate member damage and ammo usage based on weapon
                if member_weapon == 'pistol':
                    # Add damage fluctuation and miss chance
                    if random.random() < 0.05:  # 5% miss chance
                        attack_desc = f"{member_name} fires their pistol but misses completely!"
                        member_damage = 0
                    else:
                        base_damage = random.randint(8, 15)
                        # Damage fluctuation: ±20%
                        damage_multiplier = random.uniform(0.8, 1.2)
                        member_damage = int(base_damage * damage_multiplier)
                        # Apply ammo bonuses
                        if member_ammo_type == 'exploding':
                            member_damage *= 2
                        elif member_ammo_type == 'hollow_point':
                            member_damage = int(member_damage * 1.2)
                        attack_desc = random.choice([
                            f"{member_name} fires a precise shot from their pistol!",
                            f"{member_name} squeezes off a round, the bullet finding its target!",
                            f"{member_name}'s pistol roars as they take careful aim and fire!",
                            f"{member_name} draws their pistol and fires a lethal shot!"
                        ])
                        if member_ammo_type == 'exploding':
                            attack_desc += " (exploding bullet!)"
                        elif member_ammo_type == 'hollow_point':
                            attack_desc += " (hollow point bullet!)"
                elif member_weapon == 'ar15':
                    if random.random() < 0.03:  # 3% jam chance for AR-15
                        attack_desc = f"{member_name}'s AR-15 jams! No damage dealt."
                        member_damage = 0
                    else:
                        base_damage = random.randint(12, 20)
                        damage_multiplier = random.uniform(0.85, 1.15)
                        member_damage = int(base_damage * damage_multiplier)
                        # Apply ammo bonuses
                        if member_ammo_type == 'exploding':
                            member_damage *= 2
                        elif member_ammo_type == 'hollow_point':
                            member_damage = int(member_damage * 1.2)
                        attack_desc = random.choice([
                            f"{member_name} unleashes a burst from their AR-15!",
                            f"{member_name}'s assault rifle chatters as they fire!",
                            f"{member_name} opens up with their AR-15, spraying bullets!",
                            f"{member_name} fires controlled bursts from their rifle!"
                        ])
                        if member_ammo_type == 'exploding':
                            attack_desc += " (exploding ammunition!)"
                        elif member_ammo_type == 'hollow_point':
                            attack_desc += " (hollow point ammo!)"
                elif member_weapon == 'ghost_gun':
                    if random.random() < 0.2:  # 20% jam chance for ghost gun
                        attack_desc = f"{member_name}'s ghost gun jammed! No damage dealt."
                        member_damage = 0
                    elif random.random() < 0.05:  # Additional 5% miss chance
                        attack_desc = f"{member_name} fires their ghost gun but the shot goes wide!"
                        member_damage = 0
                    else:
                        base_damage = random.randint(10, 18)
                        damage_multiplier = random.uniform(0.75, 1.25)
                        member_damage = int(base_damage * damage_multiplier)
                        # Apply ammo bonuses
                        if member_ammo_type == 'exploding':
                            member_damage *= 2
                        elif member_ammo_type == 'hollow_point':
                            member_damage = int(member_damage * 1.2)
                        attack_desc = random.choice([
                            f"{member_name} fires their ghost gun with deadly precision!",
                            f"{member_name}'s untraceable weapon whispers death!",
                            f"{member_name} employs a ghost gun, the shot barely audible!"
                        ])
                        if member_ammo_type == 'exploding':
                            attack_desc += " (exploding bullet!)"
                        elif member_ammo_type == 'hollow_point':
                            attack_desc += " (hollow point bullet!)"
                elif member_weapon == 'knife':
                    if random.random() < 0.08:  # 8% miss chance for knife
                        attack_desc = f"{member_name} swings their knife but misses the target!"
                        member_damage = 0
                    else:
                        base_damage = random.randint(5, 10)
                        damage_multiplier = random.uniform(0.9, 1.1)
                        member_damage = int(base_damage * damage_multiplier)
                        attack_desc = random.choice([
                            f"{member_name} slashes with their knife!",
                            f"{member_name} stabs viciously with their blade!",
                            f"{member_name} lunges forward with their knife!",
                            f"{member_name} drives their knife home!"
                        ])
                elif member_weapon == 'vampire_bat':
                    if random.random() < 0.06:  # 6% miss chance for bat
                        attack_desc = f"{member_name} swings their vampire bat but misses wildly!"
                        member_damage = 0
                    else:
                        base_damage = random.randint(15, 25)
                        damage_multiplier = random.uniform(0.8, 1.2)
                        member_damage = int(base_damage * damage_multiplier)
                        attack_desc = random.choice([
                            f"{member_name} swings their vampire bat with brutal force!",
                            f"{member_name} brings the spiked bat down crushing!",
                            f"{member_name}'s vampire bat connects with bone-shattering impact!",
                            f"{member_name} wields the bat like a weapon of destruction!"
                        ])
                elif member_weapon == 'fists':
                    # No ammo usage for fists
                    if random.random() < 0.1:  # 10% miss chance for fists
                        attack_desc = f"{member_name} swings their fists but misses completely!"
                        member_damage = 0
                    else:
                        base_damage = random.randint(2, 6)  # Much weaker with fists
                        damage_multiplier = random.uniform(0.8, 1.2)
                        member_damage = int(base_damage * damage_multiplier)
                        attack_desc = random.choice([
                            f"{member_name} lands a solid punch with their fists!",
                            f"{member_name} connects with a brutal haymaker!",
                            f"{member_name} fights bare-handed, landing a crushing blow!",
                            f"{member_name} uses their fists effectively despite being unarmed!"
                        ])

                if member_damage > 0:
                    fight_log.append(f"{attack_desc} {member_name} deals {member_damage} damage!")
                    enemy_health -= member_damage
                else:
                    fight_log.append(f"{attack_desc}")

        # Enemy attacks back with enhanced descriptions
        if enemy_health > 0:
            # Get enemy-specific attack descriptions
            enemy_attack_descriptions = {
                'police': [
                    "A police officer fires their service pistol, the shot narrowly missing your vital organs!",
                    "The cop squeezes off a round that grazes your shoulder, leaving a burning trail of pain!",
                    "Police gunfire echoes as a bullet finds your leg, the impact sending shockwaves through your body!",
                    "An officer's pistol shot catches you in the side, the bullet burning a path through your flesh!",
                    "The police officer fires with trained precision, their bullet finding a home in your torso!"
                ],
                'gang': [
                    "A gang member fires wildly, their pistol shots spraying the area with hot lead!",
                    "The gangster's pistol bucks as they fire, bullets whizzing past your head dangerously close!",
                    "Gang gunfire erupts as a pistol shot catches you in the arm, the impact spinning you around!",
                    "A rival thug unloads their pistol, one shot finding its mark in your chest with burning force!",
                    "The gang member's pistol shot tears through your defenses, leaving you gasping in pain!"
                ],
                'squidie': [
                    "A Squidie fires their customized pistol, the shot enhanced with their signature brutality!",
                    "The Squidie gangster's pistol shot burns a path across your body, their aim unnaturally accurate!",
                    "Squidie gunfire echoes as their bullet finds your flesh, the wound burning with unnatural heat!",
                    "A Squidie thug's pistol shot catches you off guard, the impact sending waves of agony through you!",
                    "The Squidie's enhanced pistol fires with deadly precision, their bullet ripping through your defenses!"
                ]
            }

            # Determine enemy type for appropriate descriptions
            # First check for NPC-specific attack descriptions
            enemy_type_lower = enemy_type.lower().replace(' ', '_')
            enemy_type_key = None

            # Load battle descriptions to check for NPC-specific keys
            try:
                battle_desc_file = os.path.join(os.path.dirname(__file__), '..', 'model', 'battle_descriptions.json')
                with open(battle_desc_file, 'r') as f:
                    battle_descriptions = json.load(f)
                enemy_attack_descriptions = battle_descriptions.get('enemy_attack_descriptions', {})
            except:
                enemy_attack_descriptions = {}

            # Check if there's an NPC-specific description for pistol attacks
            npc_specific_key = f"{enemy_type_lower}_pistol"
            if npc_specific_key in enemy_attack_descriptions:
                enemy_type_key = npc_specific_key
            else:
                # Fall back to generic enemy type logic
                if 'police' in enemy_type.lower():
                    enemy_type_key = 'police'
                elif 'squidie' in enemy_type.lower():
                    enemy_type_key = 'squidie'
                else:
                    enemy_type_key = 'gang'

            enemy_damage = random.randint(5, 15) * enemy_count

            # First, determine if attack targets a gang member (40% chance if members > 1)
            killed_member = False
            if game_state.members > 1 and random.random() < 0.4:  # 40% chance to target a gang member
                killed_member = True
                game_state.members -= 1
                # Recalculate health cap immediately after losing a member
                old_max_health = game_state.max_health + 10  # What it was before
                game_state.health = min(game_state.health, game_state.max_health)  # Cap to new max
                grim_death_descriptions = [
                    f"A hail of bullets rips through Squad Member #{game_state.members + 1}, their body jerking violently as blood sprays across the ground in gruesome arcs!",
                    f"Your loyal Lieutenant #{game_state.members + 1} screams as gunfire shreds their chest, collapsing in a pool of their own viscera!",
                    f"Gang Member #{game_state.members + 1} takes a fatal shot to the throat, gurgling wetly as blood pours from the ragged wound!",
                    f"Enemy fire catches Soldier #{game_state.members + 1} in the gut, their intestines spilling onto the filthy street in a steaming pile!",
                    f"A bullet punches through Trooper #{game_state.members + 1}'s skull, brain matter splattering with a sickening crack!",
                    f"Loyal Squad Member #{game_state.members + 1} collapses with multiple gunshot wounds, their blood mixing with the dirt in dark, sticky pools!",
                    f"Your Enforcer #{game_state.members + 1} takes a final, fatal shot, their eyes glazing over as life drains from their perforated body!",
                    f"Companion #{game_state.members + 1} falls with a guttural cry, their comrades forced to step over their still-twitching corpse!"
                ]
                fight_log.append(random.choice(grim_death_descriptions))
                fight_log.append(f"Your gang shrinks to {game_state.members} members. Max health reduced to {game_state.max_health}!")
            else:
                # Regular damage to player
                if game_state.weapons.vest > 0 and random.random() < 0.5:
                    game_state.weapons.vest -= 1
                    enemy_damage = max(0, enemy_damage - 20)
                    attack_desc = random.choice(enemy_attack_descriptions.get(enemy_type_key, ["Enemy attacks!"]))
                    fight_log.append(f"{attack_desc} Your vest absorbs some damage, you take {enemy_damage} damage!")
                else:
                    attack_desc = random.choice(enemy_attack_descriptions.get(enemy_type_key, ["Enemy attacks!"]))
                    fight_log.append(f"{attack_desc} You take {enemy_damage} damage!")
                game_state.damage += enemy_damage

                # Additional grim mechanic: if damage isn't fatal but you're taking damage, 15% chance a gang member also dies
                current_total_health = game_state.health - game_state.damage
                if current_total_health > enemy_damage and game_state.members > 1 and random.random() < 0.15:  # 15% chance
                    game_state.members -= 1
                    old_max_health = game_state.max_health + 10  # What it was before
                    game_state.health = min(game_state.health, game_state.max_health)  # Cap to new max
                    collateral_member_deaths = [
                        f"In the chaos of battle, a stray bullet catches Squad Member #{game_state.members + 1} in the temple - their skull explodes in a fountain of gore!",
                        f"The crossfire is merciless - Trooper #{game_state.members + 1} takes shrapnel to the neck, arterial blood spraying like a macabre sprinkler!",
                        f"A ricochet claims Gang Member #{game_state.members + 1}, their screams cut short as they claw futilely at the hole in their chest!",
                        f"Enforcer #{game_state.members + 1} drops silently, a bullet having passed through their spine and severed their central nervous system!",
                        f"The close-quarters combat turns deadly - Lieutenant #{game_state.members + 1}'s arm is blown off at the shoulder, bleeding out in agonizing seconds!",
                        f"Bullets fly everywhere - Soldier #{game_state.members + 1} catches one in the eye socket, their orbital cavity erupting in bloody ruin!",
                        f"The battle's salvage claims Companion #{game_state.members + 1}, whose abdomen is torn open by automatic weapon fire!",
                        f"In this meat grinder of violence, Squad Member #{game_state.members + 1}'s femoral artery is severed, pumping blood in rhythmic spurts!"
                    ]
                    fight_log.append(random.choice(collateral_member_deaths))
                    fight_log.append(f"Collateral damage! Your gang shrinks to {game_state.members} members. Max health reduced to {game_state.max_health}!")

    elif action == 'defend':
        fight_log.append("You take a defensive stance, reducing incoming damage!")
        # Reduced enemy damage
        if enemy_health > 0:
            enemy_damage = random.randint(2, 10) * enemy_count
            fight_log.append(f"Enemy attacks! You take {enemy_damage} damage (reduced by defense)!")
            game_state.damage += enemy_damage

    elif action == 'flee':
        if random.random() < 0.5:  # 50% chance to flee
            fight_log.append("You successfully flee from combat!")
            save_game_state(game_state)
            return redirect(url_for('city'))
        else:
            fight_log.append("You try to flee but fail!")
            # Enemy attacks during flee attempt
            enemy_damage = random.randint(10, 20) * enemy_count
            fight_log.append(f"Enemy attacks while you flee! You take {enemy_damage} damage!")
            game_state.damage += enemy_damage

    elif action == 'use_drug':
        # Handle drug usage
        if drug and hasattr(game_state.drugs, drug) and getattr(game_state.drugs, drug) > 0:
            setattr(game_state.drugs, drug, getattr(game_state.drugs, drug) - 1)
            if drug == 'weed':
                fight_log.append("You smoke weed - your accuracy decreases but you feel relaxed!")
            elif drug == 'crack':
                fight_log.append("You smoke crack - you feel powerful but your health suffers!")
                game_state.damage += 5
            elif drug == 'coke':
                fight_log.append("You snort coke - your accuracy improves!")
            elif drug == 'ice':
                fight_log.append("You use ice - you feel incredibly strong!")
            elif drug == 'percs':
                fight_log.append("You take percs - pain fades away!")
                game_state.damage = max(0, game_state.damage - 10)
            elif drug == 'pixie_dust':
                fight_log.append("You use pixie dust - ??? Something magical happens!")
        else:
            fight_log.append("You don't have that drug!")

    # Check win/lose conditions
    if enemy_health <= 0:
        # Handle NPC-specific victory logic
        npc_id = request.form.get('npc_id')
        if npc_id and npc_id in npcs_data:
            npc = npcs_data[npc_id]
            npcs_data[npc_id]['is_alive'] = False
            npc_file = os.path.join(os.path.dirname(__file__), '..', 'model', 'npcs.json')
            with open(npc_file, 'w') as f:
                json.dump(npcs_data, f, indent=2)

            game_state.money += 100  # Loot from defeated NPC
            fight_log.append(f"You defeated {npc['name']} and looted $100!")

            # Check for unique weapon drops
            unique_drops = npc.get('unique_drops', [])
            for weapon in unique_drops:
                if weapon == 'sword':
                    game_state.weapons.sword += 1
                    fight_log.append(f"You found a unique SWORD dropped by {npc['name']}!")
                elif weapon == 'axe':
                    game_state.weapons.axe += 1
                    fight_log.append(f"You found a unique AXE dropped by {npc['name']}!")
                elif weapon == 'golden_gun':
                    game_state.weapons.golden_gun += 1
                    fight_log.append(f"You found a unique GOLDEN GUN dropped by {npc['name']}!")
                elif weapon == 'poison_blowgun':
                    game_state.weapons.poison_blowgun += 1
                    fight_log.append(f"You found a unique POISON BLOWGUN dropped by {npc['name']}!")
                elif weapon == 'chain_whip':
                    game_state.weapons.chain_whip += 1
                    fight_log.append(f"You found a unique CHAIN WHIP dropped by {npc['name']}!")
                elif weapon == 'plasma_cutter':
                    game_state.weapons.plasma_cutter += 1
                    fight_log.append(f"You found a unique PLASMA CUTTER dropped by {npc['name']}!")

            # NPCs have a chance to drop drugs
            drug_types = ['weed', 'crack', 'coke', 'ice', 'percs', 'pixie_dust']
            for drug in drug_types:
                if random.random() < 0.3:  # 30% chance per drug type
                    amount = random.randint(1, 3)
                    setattr(game_state.drugs, drug, getattr(game_state.drugs, drug) + amount)
                    fight_log.append(f"You found {amount} kilos of {drug} on {npc['name']}!")

        # All enemies are defeated, but some defect or flee instead of dying
        killed = enemy_count

        # Chance to recruit defeated enemies
        if enemy_type != "Police Officers":
            recruits = random.randint(0, min(2, enemy_count))
        else:
            recruits = 0

        # Some of those defeated flee or surrender
        if recruits < enemy_count:
            fled_count = random.randint(0, enemy_count - recruits)
        else:
            fled_count = 0

        killed = enemy_count - recruits - fled_count

        # Recruit the defectors
        if recruits > 0:
            game_state.members += recruits
            game_state.health = min(game_state.max_health, game_state.health + 10 * recruits)
            fight_log.append(f"{recruits} of the defeated enemies joined your gang!")

        # Chance to find drugs on defeated enemies
        if random.random() < 0.4:  # 40% chance to find drugs
            drug_types = ['weed', 'crack', 'coke', 'ice', 'percs']
            drug = random.choice(drug_types)
            amount = random.randint(1, 2)
            setattr(game_state.drugs, drug, getattr(game_state.drugs, drug) + amount)
            fight_log.append(f"You found {amount} kilos of {drug} on the defeated enemy!")

        # Victory outcome breakdown
        fight_log.append(f"VICTORY! You have defeated the {enemy_type}!")
        fight_log.append(f"Battle outcome: {killed} killed, {fled_count} fled, {recruits} defected.")
        save_game_state(game_state)

        # Check for game win condition (defeating all squidies)
        if "squidie" in enemy_type.lower():
            # Game victory! Update high scores and redirect to win screen
            game_state.current_score += 5  # Major achievement: 5 points for defeating Squidies
            check_and_update_high_scores(game_state, 1, 0)  # Game win counts as a gang war won
            check_and_update_high_scores(game_state, 1, 0)  # Game win counts as a gang war won
            if is_ajax:
                return jsonify({
                    'success': True,
                    'game_win': True,
                    'combat_active': False,
                    'redirect_url': url_for('game_win')
                })
            else:
                return redirect(url_for('game_win'))

        if is_ajax:
            # Return JSON response for AJAX requests
            return jsonify({
                'success': True,
                'combat_active': False,
                'enemy_health': enemy_health,
                'fight_log': fight_log,
                'game_state': {
                    'health': game_state.health - game_state.damage,
                    'money': game_state.money,
                    'members': game_state.members,
                    'damage': game_state.damage
                }
            })
        else:
            # Stay on battle screen with combat inactive, showing victory in combat log
            combat_active = False
            return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=enemy_count, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)
    elif game_state.damage >= 30:
        # Special handling for muggers - they rob you but you survive with 1 HP
        if "mugger" in enemy_type.lower():
            # Muggers rob you but you live with 1 HP
            robbed_amount = game_state.money  # Lose all cash that's not in savings
            game_state.money = 0
            game_state.damage = 29  # Set to 29 so you have 1 HP remaining (30 - 29 = 1)
            game_state.health = 1  # Explicitly set to 1 HP

            fight_log.append(f"You have been defeated by the {enemy_type}!")
            fight_log.append(f"The muggers rob you of ${robbed_amount:,} but spare your life!")
            fight_log.append("You crawl away with 1 HP remaining, your pockets empty.")

            save_game_state(game_state)

            if is_ajax:
                return jsonify({
                    'success': True,
                    'defeat': True,
                    'mugged': True,
                    'robbed_amount': robbed_amount,
                    'combat_active': False,
                    'enemy_health': enemy_health,
                    'fight_log': fight_log,
                    'game_state': {
                        'health': game_state.health - game_state.damage,
                        'money': game_state.money,
                        'members': game_state.members,
                        'damage': game_state.damage,
                        'lives': game_state.lives
                    }
                })
            else:
                # Stay on battle screen with combat inactive, showing mugging in combat log
                combat_active = False
                return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=enemy_count, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)
        else:
            # Normal defeat - lose a life and all but $500
            game_state.lives -= 1
            final_damage = game_state.damage  # Store the final damage before resetting
            game_state.damage = 0
            game_state.health = 30
            
            # Lose money when you die (keep $500 safe if you have enough, otherwise keep all)
            if game_state.money > 500:
                lost_money = game_state.money - 500
                game_state.money = 500
                fight_log.append(f"You have been defeated by the {enemy_type}!")
                fight_log.append(f"They took all your money except $500 you had hidden in your sock! You now have ${game_state.money}.")
            else:
                fight_log.append(f"You have been defeated by the {enemy_type}!")
                fight_log.append(f"You didn't have enough money to lose anything extra! You keep your ${game_state.money}.")

            if game_state.lives <= 0:
                # Update high scores when player dies
                check_and_update_high_scores(game_state)
                save_game_state(game_state)

                fight_log.append("GAME OVER! You have run out of lives.")
                fight_log.append("Your gang war has ended in defeat.")

                if is_ajax:
                    return jsonify({
                        'success': True,
                        'defeat': True,
                        'game_over': True,
                        'combat_active': False,
                        'enemy_health': enemy_health,
                        'fight_log': fight_log,
                        'game_state': {
                            'health': game_state.health - game_state.damage,
                            'money': game_state.money,
                            'members': game_state.members,
                            'damage': game_state.damage,
                            'lives': game_state.lives
                        },
                        'final_damage': final_damage
                    })
                else:
                    # Stay on battle screen with combat inactive, showing defeat in combat log
                    combat_active = False
                    return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=enemy_count, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)
            else:
                save_game_state(game_state)

                fight_log.append("You survived this defeat, but you have lost a life.")
                fight_log.append(f"You have {game_state.lives} lives remaining.")

                if is_ajax:
                    return jsonify({
                        'success': True,
                        'defeat': True,
                        'continue_combat': True,
                        'combat_active': False,
                        'enemy_health': enemy_health,
                        'fight_log': fight_log,
                        'game_state': {
                            'health': game_state.health - game_state.damage,
                            'money': game_state.money,
                            'members': game_state.members,
                            'damage': game_state.damage,
                            'lives': game_state.lives
                        },
                        'final_damage': final_damage
                    })
                else:
                    # Stay on battle screen with combat inactive, showing defeat in combat log
                    combat_active = False
                    return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=enemy_count, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)

    # Continue combat
    save_game_state(game_state)
    combat_active = enemy_health > 0

    print(f"DEBUG: Sending AJAX response - enemy_health={enemy_health}, combat_active={combat_active}, fight_log length={len(fight_log)}")

    if is_ajax:
        response_data = {
            'success': True,
            'combat_active': combat_active,
            'enemy_health': enemy_health,
            'fight_log': fight_log,
            'game_state': {
                'health': game_state.health - game_state.damage,
                'money': game_state.money,
                'members': game_state.members,
                'damage': game_state.damage
            }
        }
        print(f"DEBUG: AJAX response data: {response_data}")
        return jsonify(response_data)
    else:
        return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=enemy_count, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)

@app.route('/game_over')
def game_over():
    """Game Over screen"""
    game_state = get_game_state()
    # Update high scores when game ends
    check_and_update_high_scores(game_state)
    return render_template('game_over.html', game_state=game_state)

@app.route('/game_win')
def game_win():
    """Game Win screen"""
    game_state = get_game_state()
    # Update high scores when game is won
    check_and_update_high_scores(game_state)
    return render_template('game_win.html', game_state=game_state)

# ============
# SocketIO Events - Always enabled for chat functionality
# ============

if socketio:
    @socketio.on("join")
    def handle_join(data):
        """Handle player joining a room"""
        room = data.get("room", "global")
        location_room = data.get("location_room", "city")
        player_name = data.get("player_name", "Unknown Player")

        # Always join global room for universal chat
        join_room("global")
        join_room(room)
        join_room(location_room)

        # Override with session data if available
        try:
            game_state = get_game_state()
            if game_state.player_name:
                player_name = game_state.player_name
        except:
            pass

        # Remove old player entry if exists (prevent duplicates)
        connected_players.pop(request.sid, None)

        # Check if this player name already exists and remove old entry
        for sid, player_info in list(connected_players.items()):
            if player_info["name"] == player_name:
                del connected_players[sid]

        # Store player info
        connected_players[request.sid] = {
            "id": request.sid,
            "name": player_name,
            "room": location_room,
            "in_fight": False,
            "joined_at": time.time()
        }

        emit("status", {"msg": f"{player_name} joined the chat"}, broadcast=True)
        update_player_lists()

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle player disconnecting"""
        if request.sid in connected_players:
            player_name = connected_players[request.sid]["name"]
            del connected_players[request.sid]
            emit("status", {"msg": f"{player_name} left the chat"}, broadcast=True)
            update_player_lists()

    @socketio.on("chat_message")
    def handle_chat_message(data):
        """Handle chat messages - universal chat to all connected players"""
        room = data.get("room", "global")

        # Try to get player name from connected players first, then from session
        player_name = connected_players.get(request.sid, {}).get("name", "")

        # If not available, try to get from session
        if not player_name:
            try:
                game_state = get_game_state()
                player_name = game_state.player_name or "Anonymous User"
            except:
                player_name = "Anonymous User"

        # Fallback to what was sent
        if not player_name:
            player_name = data.get("player_name", "Anonymous User")

        message = data.get("message", "")

        if message.strip():
            # Send to ALL connected clients for universal chat
            emit("chat_message", {
                "player": player_name,
                "message": message,
                "room": "global"
            }, broadcast=True)

    @socketio.on("get_player_list")
    def handle_get_player_list(data):
        """Send complete player list to requesting client - shows ALL online players"""
        room = data.get("room", "city")
        # Return ALL connected players
        all_players_online = []
        seen_names = set()
        
        for player in connected_players.values():
            if player["name"] not in seen_names:
                seen_names.add(player["name"])
                all_players_online.append({
                    "id": player["id"],
                    "name": player["name"],
                    "location": player["room"]
                })
                
        emit("player_list", {"players": all_players_online})

    @socketio.on("pvp_challenge")
    def handle_pvp_challenge(data):
        """Handle PVP challenge requests"""
        target_id = data.get("target_id")
        room = data.get("room", "city")

        if target_id in connected_players:
            emit("pvp_response", {
                "success": True,
                "message": "PVP challenge sent!"
            })
        else:
            emit("pvp_response", {
                "success": False,
                "message": "Player not found or unavailable."
            })

    def update_player_lists():
        """Update player lists for all connected clients"""
        players_list = list(connected_players.values())
        socketio.emit("player_list", {"players": players_list}, room="global")


if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Gangwar Game Server')
    parser.add_argument('--port', type=int, default=6009, help='Port to run the server on (default: 6009)')
    args = parser.parse_args()

    port = args.port

    # Start the app with SocketIO if available
    if socketio:
        print("Initializing SocketIO for chat support...")
        socketio.run(app, debug=True, allow_unsafe_werkzeug=True, host='0.0.0.0', port=port)
    else:
        print("Warning: Flask-SocketIO not available - starting without chat functionality...")
        app.run(debug=True, host='0.0.0.0', port=port)
