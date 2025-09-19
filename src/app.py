import os
import random
import secrets
import subprocess
import sys
import time
import threading
import json
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, flash

# Load NPCs
try:
    with open('model/npcs.json', 'r') as f:
        npcs_data = json.load(f)
except FileNotFoundError:
    npcs_data = {}

# Load battle descriptions
try:
    with open('model/battle_descriptions.json', 'r') as f:
        battle_descriptions = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading battle descriptions: {e}")
    battle_descriptions = {
        "attack_messages": {
            "pistol": "You fire your pistol!",
            "ghost_gun": "You fire your ghost gun!",
            "uzi": "You fire your Uzi!",
            "grenade": "You throw a grenade!",
            "missile_launcher": "You fire a missile!",
            "barbed_wire_bat": "You swing your barbed wire bat!",
            "knife": "You stab with your knife!"
        },
        "kill_messages": {
            "police_singular": "You killed a police officer!",
            "police_plural": "You killed {count} police officers!",
            "gang_singular": "You killed a gang member!",
            "gang_plural": "You killed {count} gang members!",
            "squidie_singular": "You killed a Squidie!",
            "squidie_plural": "You killed {count} Squiddies!",
            "generic_singular": "You killed an enemy!",
            "generic_plural": "You killed {count} enemies!"
        },
        "victory_messages": {
            "complete_victory": "Victory! You defeated all enemies!",
            "partial_victory": "Victory! You killed {killed} enemies!"
        },
        "defeat_messages": {
            "final_death": "Game Over! You have died!",
            "standard": "Defeat! You were defeated!",
            "damage_taken": "You took {damage} damage!"
        },
        "combat_status": {
            "use_drug_crack": "You used crack!",
            "use_drug_percs": "You healed {healed} damage with painkillers!",
            "drug_generic": "You used {drug_name}!"
        },
        "squidie_specific": {
            "gang_loss": "The Squiddies lost {count} members!"
        }
    }

# Load room configurations
try:
    with open('model/rooms_config.json', 'r') as f:
        rooms_config = json.load(f)
except FileNotFoundError:
    rooms_config = {}

# Load room descriptions
try:
    with open('model/rooms.json', 'r') as f:
        rooms_data = json.load(f)
except FileNotFoundError:
    rooms_data = {}

# ============t
# High Scores
# ============

HIGH_SCORES_FILE = 'high_scores.json'

def load_high_scores():
    """Load high scores from file"""
    try:
        if os.path.exists(HIGH_SCORES_FILE):
            with open(HIGH_SCORES_FILE, 'r') as f:
                data = json.load(f)
                return data
    except Exception as e:
        print(f"Error loading high scores: {e}")
    return []

def save_high_scores(scores):
    """Save high scores to file"""
    try:
        with open(HIGH_SCORES_FILE, 'w') as f:
            json.dump(scores, f, indent=2)
    except Exception as e:
        print(f"Error saving high scores: {e}")

def calculate_score(money_earned: int, days_survived: int, gang_wars_won: int, fights_won: int) -> int:
    """Calculate total score based on achievements"""
    # Money earned contributes 1 point per $1000
    money_score = money_earned // 1000

    # Days survived contributes 100 points per day
    survival_score = days_survived * 100

    # Gang war victories contribute 1000 points each
    gang_war_score = gang_wars_won * 1000

    # Individual fights won contribute 50 points each
    fight_score = fights_won * 50

    return money_score + survival_score + gang_war_score + fight_score

# ============
# Game State
# ============

# ============
# Data Classes (now loaded from JSON files in model/ directory)
# ============

# ============
# Game Logic
# ============

def get_game_state():
    """Get current game state from session"""
    if 'game_state' not in session:
        # Initialize default game state as dictionary
        session['game_state'] = {
            'player_name': '',
            'gang_name': '',
            'money': 1000,
            'account': 0,
            'loan': 0,
            'members': 1,
            'squidies': 25,
            'squidies_pistols': 10,
            'squidies_uzis': 5,
            'squidies_bullets': 100,
            'squidies_grenades': 20,
            'squidies_missile_launcher': 2,
            'squidies_missiles': 10,
            'day': 1,
            'health': 30,
            'steps': 0,
            'max_steps': 15,
            'current_score': 0,
            'current_location': 'city',
            'drug_prices': {
                'weed': 500,
                'crack': 1000,
                'coke': 2000,
                'ice': 1500,
                'percs': 800,
                'pixie_dust': 3000
            },
            'lives': 3,
            'damage': 0,
            'flags': {'has_id': False, 'has_info': False},
            'weapons': {
                'pistols': 0,
                'bullets': 0,
                'uzis': 0,
                'grenades': 0,
                'barbed_wire_bat': 0,
                'missile_launcher': 0,
                'missiles': 0,
                'vest': 0,
                'knife': 0,
                'ghost_guns': 0
            },
            'drugs': {
                'weed': 0,
                'crack': 5,
                'coke': 0,
                'ice': 0,
                'percs': 0,
                'pixie_dust': 0
            }
        }
    return session['game_state']

def update_current_score(game_state):
    """Update the current score based on achievements"""
    money_earned = game_state['money'] + game_state['account']
    days_survived = game_state['day']
    # For current score, we don't track gang wars/fights won in real-time,
    # so we'll base it on money and days survived for now
    game_state['current_score'] = calculate_score(money_earned, days_survived, 0, 0)

def save_game_state(game_state):
    """Save game state to session"""
    # Update current score before saving
    update_current_score(game_state)
    session['game_state'] = game_state
    session.modified = True

def check_and_update_high_scores(game_state, gang_wars_won: int = 0, fights_won: int = 0):
    """Check if current game qualifies for high score and update if necessary"""
    if not game_state['player_name'] or not game_state['gang_name']:
        return

    # Calculate current achievements
    money_earned = game_state['money'] + game_state['account']  # Include savings
    days_survived = game_state['day']

    # Calculate score
    score = calculate_score(money_earned, days_survived, gang_wars_won, fights_won)

    # Load existing high scores
    high_scores = load_high_scores()

    # Create new high score entry as dictionary
    new_score = {
        'player_name': game_state['player_name'],
        'gang_name': game_state['gang_name'],
        'score': score,
        'money_earned': money_earned,
        'days_survived': days_survived,
        'gang_wars_won': gang_wars_won,
        'fights_won': fights_won,
        'date_achieved': time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Add to list and sort by score (highest first)
    high_scores.append(new_score)
    high_scores.sort(key=lambda x: x['score'], reverse=True)

    # Keep only top 10 scores
    high_scores = high_scores[:10]

    # Save updated high scores
    save_high_scores(high_scores)


# ============
# Flask App
# ============

app = Flask(__name__)
app.secret_key = 'gangwar_secret_key_2024'

# Check if running in PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle - use bundled templates and static files
    app.template_folder = os.path.join(sys._MEIPASS, 'templates')
    app.static_folder = os.path.join(sys._MEIPASS, 'static')
else:
    # Running in development - use relative paths
    app.template_folder = os.path.join(os.path.dirname(__file__), '..', 'templates')
    app.static_folder = os.path.join(os.path.dirname(__file__), '..', 'static')

# Check if running in PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle - disable SocketIO for now
    socketio = None
else:
    # Running in development - enable SocketIO
    from flask_socketio import SocketIO, emit, join_room, leave_room
    socketio = SocketIO(app)

# Global player tracking
connected_players = {}

# ============
# Routes
# ============

@app.route('/')
def index():
    """Main index page"""
    return render_template('index.html')

@app.route('/high_scores')
def high_scores():
    """Display all-time high scores"""
    scores = load_high_scores()
    return render_template('high_scores.html', high_scores=scores)

@app.route('/credits')
def credits():
    """Display credits and high scores"""
    scores = load_high_scores()
    return render_template('credits.html', high_scores=scores)

@app.route('/city')
def city():
    """City hub"""
    game_state = get_game_state()
    game_state['current_location'] = "city"
    save_game_state(game_state)
    return render_template('city.html', game_state=game_state)

@app.route('/crackhouse')
def crackhouse():
    """Big Johnny's Crack House"""
    game_state = get_game_state()
    game_state['current_location'] = "crackhouse"
    save_game_state(game_state)
    return render_template('crackhouse.html', game_state=game_state)

@app.route('/gunshack')
def gunshack():
    """Little Johnny's Gun Shack"""
    game_state = get_game_state()
    return render_template('gunshack.html', game_state=game_state)

@app.route('/buy_weapon', methods=['POST'])
def buy_weapon():
    """Handle weapon purchases"""
    game_state = get_game_state()
    weapon_type = request.form.get('weapon_type')
    quantity = int(request.form.get('quantity', 1))

    weapon_prices = {
        'pistol': 1200,
        'ghost_gun': 600,
        'bullets': 100,
        'uzi': 100000,
        'grenade': 1000,
        'barbed_wire_bat': 2500,
        'missile_launcher': 1000000,
        'missile': 100000,
        'vest_light': 30000,
        'vest_medium': 55000,
        'vest_heavy': 75000,
        'pistol_switch': 2500,
        'ghost_gun_switch': 1500
    }

    if weapon_type not in weapon_prices:
        flash("Invalid weapon type!", "danger")
        return redirect(url_for('gunshack'))

    price = weapon_prices[weapon_type]
    total_cost = price * quantity

    if game_state['money'] >= total_cost:
        game_state['money'] -= total_cost

        if weapon_type == 'pistol':
            game_state['weapons']['pistols'] += quantity
        elif weapon_type == 'bullets':
            game_state['weapons']['bullets'] += quantity * 50  # 50 bullets per pack
        elif weapon_type == 'uzi':
            game_state['weapons']['uzis'] += quantity
        elif weapon_type == 'grenade':
            game_state['weapons']['grenades'] += quantity
        elif weapon_type == 'barbed_wire_bat':
            game_state['weapons']['barbed_wire_bat'] += quantity
        elif weapon_type == 'missile_launcher':
            game_state['weapons']['missile_launcher'] += quantity
        elif weapon_type == 'missile':
            game_state['weapons']['missiles'] += quantity
        elif weapon_type == 'pistol_switch':
            # Upgrade all pistols to full auto
            if game_state['weapons']['pistols'] > 0:
                if 'upgraded_pistols' not in game_state['weapons']:
                    game_state['weapons']['upgraded_pistols'] = 0
                game_state['weapons']['upgraded_pistols'] += game_state['weapons']['pistols']
                game_state['weapons']['pistols'] = 0
                flash("All pistols upgraded with switch! They now fire full auto.", "success")
            else:
                flash("You don't have any pistols to upgrade!", "danger")
                return redirect(url_for('gunshack'))
        elif weapon_type == 'ghost_gun_switch':
            # Upgrade all ghost guns to full auto
            if game_state['weapons']['ghost_guns'] > 0:
                if 'upgraded_ghost_guns' not in game_state['weapons']:
                    game_state['weapons']['upgraded_ghost_guns'] = 0
                game_state['weapons']['upgraded_ghost_guns'] += game_state['weapons']['ghost_guns']
                game_state['weapons']['ghost_guns'] = 0
                flash("All ghost guns upgraded with switch! They now fire full auto.", "success")
            else:
                flash("You don't have any ghost guns to upgrade!", "danger")
                return redirect(url_for('gunshack'))
        elif weapon_type.startswith('vest_'):
            if weapon_type == 'vest_light':
                game_state['weapons']['vest'] += 5
            elif weapon_type == 'vest_medium':
                game_state['weapons']['vest'] += 10
            elif weapon_type == 'vest_heavy':
                game_state['weapons']['vest'] += 15

        flash(f"You bought {quantity} {weapon_type.replace('_', ' ')}(s) for ${total_cost:,}!", "success")
    else:
        flash(f"You don't have enough money! Need ${total_cost:,}.", "danger")

    save_game_state(game_state)
    return redirect(url_for('gunshack'))

@app.route('/bar')
def bar():
    """Vagabond's Pub"""
    game_state = get_game_state()
    return render_template('bar.html', game_state=game_state)

@app.route('/bank')
def bank():
    """Savings and Loan"""
    game_state = get_game_state()
    return render_template('bank.html', game_state=game_state)

@app.route('/infobooth')
def infobooth():
    """Info Booth"""
    game_state = get_game_state()
    return render_template('infobooth.html', game_state=game_state)

@app.route('/alleyway')
def alleyway():
    """Explore Dark Alleyway"""
    game_state = get_game_state()
    game_state['current_location'] = "alleyway"
    save_game_state(game_state)

    # Get current room from session, default to entrance
    current_room_id = session.get('current_alleyway_room', 'entrance')

    # Use room data from JSON files
    if rooms_data and current_room_id in rooms_data:
        current_room = {
            'title': rooms_data[current_room_id]['title'],
            'description': rooms_data[current_room_id]['description'],
            'exits': rooms_data[current_room_id]['exits']
        }
    elif rooms_config and 'rooms' in rooms_config and current_room_id in rooms_config['rooms']:
        current_room = rooms_config['rooms'][current_room_id]
    else:
        # Fallback if JSON files are not available
        current_room = {
            'title': 'Dark Alley Entrance',
            'description': 'You stand at the entrance of a dark alleyway. The streetlights cast long shadows, and you can hear distant sounds echoing off the walls.',
            'exits': {
                'north': 'dead_end',
                'south': 'city',
                'east': 'side_street',
                'west': 'dumpster'
            }
        }

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
    enemy_health = game_state['squidies'] * 20  # Each Squidie has 20 health
    enemy_type = f"The Squidies Gang ({game_state['squidies']} members)"
    combat_active = True
    combat_id = f"final_battle_{random.randint(1000, 9999)}"

    # Initialize fight log
    fight_log = [f"You launch your final assault on the Squidies gang headquarters!", f"Combat begins against {enemy_type}!"]
    session['fight_log'] = fight_log
    session.modified = True

    return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=game_state['squidies'], combat_active=combat_active, combat_id=combat_id, fight_log=fight_log)

@app.route('/wander')
def wander():
    """Wander the Streets"""
    game_state = get_game_state()
    result = ""  # Initialize result variable

    # Check for police chase (10% chance)
    if random.random() < 0.1:
        if game_state['flags']['has_id']:
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
            combat_id = f"police_{random.randint(1000, 9999)}"

            # Initialize fight log
            fight_log = [f"Oh no! {num_cops} police officers spot you and give chase!", f"Combat begins against {enemy_type}!"]
            session['fight_log'] = fight_log
            session.modified = True

            return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=num_cops, combat_active=combat_active, combat_id=combat_id, fight_log=fight_log)

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
        if game_state['money'] >= 200:
            game_state['money'] -= 200
            result += f" You pay her $200 to make her go away."
        elif game_state['money'] >= 100:
            game_state['money'] -= 100
            result += f" You give her $100 to calm her down."
        else:
            result += " You don't have any money to give her!"
            game_state['health'] = max(0, game_state['health'] - 10)  # She beats you up

    # Check for small gang fight (12% chance)
    elif random.random() < 0.12:
        enemy_members = random.randint(3, 8)
        message = f"You encounter {enemy_members} rival gang members looking for trouble!"
        save_game_state(game_state)
        # Start MUD fight
        enemy_health = enemy_members * 15  # Each gang member has 15 health
        enemy_type = f"{enemy_members} Rival Gang Members"
        combat_active = True
        combat_id = f"gang_{random.randint(1000, 9999)}"

        # Initialize fight log
        fight_log = [f"You encounter {enemy_members} rival gang members looking for trouble!", f"Combat begins against {enemy_type}!"]
        session['fight_log'] = fight_log
        session.modified = True

        return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=enemy_members, combat_active=combat_active, combat_id=combat_id, fight_log=fight_log)

    # Check for Squidie hit squad (scales with gang power)
    elif game_state['members'] >= 3:  # Only when you have some gang presence
        # Base chance starts low, increases with gang size and success
        base_chance = 0.02  # 2% base chance
        gang_multiplier = min(game_state['members'] / 10, 2.0)  # Up to 2x multiplier at 10+ members
        money_multiplier = min(game_state['money'] / 10000, 1.5)  # Up to 1.5x for $10k+
        total_chance = base_chance * gang_multiplier * money_multiplier

        if random.random() < total_chance:
            squidie_members = random.randint(2, min(6, max(2, game_state['members'] // 2 + 1)))
            message = f"Oh no! A Squidie hit squad of {squidie_members} members has tracked you down!"
            save_game_state(game_state)
            # Start MUD fight with Squidies
            enemy_health = squidie_members * 25  # Squidies are tougher (25 HP each)
            enemy_type = f"{squidie_members} Squidie Hit Squad"
            combat_active = True
            combat_id = f"squidie_{random.randint(1000, 9999)}"

            # Initialize fight log
            fight_log = [f"Oh no! A Squidie hit squad of {squidie_members} members has tracked you down!", f"Combat begins against {enemy_type}!"]
            session['fight_log'] = fight_log
            session.modified = True

            return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=squidie_members, combat_active=combat_active, combat_id=combat_id, fight_log=fight_log)

    # Regular wander results (remaining ~70% chance)
    else:
        # List of possible wander results
        wander_messages = [
            "You wander the streets and find a discarded wallet with $50!",
            "You encounter a street performer who gives you some tips on the local scene.",
            "You overhear some gang members talking about upcoming turf wars.",
            "You find a quiet spot to rest and regain some health.",
            "You notice some suspicious activity but decide to keep moving.",
            "You bump into an old contact who shares some gossip.",
            "You wander into a rough neighborhood and narrowly avoid trouble.",
            "You find some discarded drugs worth $200 on the street.",
            "You help a local shopkeeper and get rewarded with information.",
            "You wander around the city without incident.",
            "You see a police patrol and quickly hide in an alley.",
            "You find a hidden stash of weapons.",
            "You encounter a beggar who tells you about secret locations.",
            "You wander through a market district and haggle for better prices.",
            "You stumble upon a gang recruitment drive."
        ]

        # Ensure randomness by seeding with current time
        random.seed(time.time())
        # Select a random message
        result = random.choice(wander_messages)

        # Apply effects based on the result
        if "wallet with $50" in result:
            game_state['money'] += 50
        elif "discarded drugs worth $200" in result:
            game_state['money'] += 200
        elif "find a quiet spot" in result:
            game_state['health'] = min(100, game_state['health'] + 10)
        elif "hidden stash of weapons" in result:
            game_state['weapons']['bullets'] += 5
        elif "without incident" not in result and "trouble" not in result and "police" not in result:
            # Minor health damage for risky wanders
            if random.random() < 0.3:
                game_state['health'] = max(0, game_state['health'] - 5)

    # Increment steps
    game_state['steps'] += 1

    # Check if day ends
    if game_state['steps'] >= game_state['max_steps']:
        game_state['day'] += 1
        game_state['steps'] = 0
        # Reset some daily things if needed

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
    game_state['current_location'] = "picknsave"
    save_game_state(game_state)
    return render_template('picknsave.html', game_state=game_state)

@app.route('/picknsave_action', methods=['POST'])
def picknsave_action():
    """Handle Pick n Save actions"""
    game_state = get_game_state()
    action = request.form.get('action')

    if action == 'buy_food':
        if game_state['money'] >= 500:
            game_state['money'] -= 500
            flash("You bought food supplies for your gang! Morale is high.", "success")
        else:
            flash("You don't have enough money for food supplies!", "danger")

    elif action == 'buy_medical':
        if game_state['money'] >= 1000:
            game_state['money'] -= 1000
            game_state['health'] = min(100, game_state['health'] + 50)  # Heal up to 100
            flash("You bought medical supplies! Health restored.", "success")
        else:
            flash("You don't have enough money for medical supplies!", "danger")

    elif action == 'buy_id':
        if game_state['money'] >= 5000:
            game_state['money'] -= 5000
            game_state['flags']['has_id'] = True
            flash("You bought a fake ID! You're now protected from random police checks.", "success")
        else:
            flash("You don't have enough money for a fake ID!", "danger")

    elif action == 'buy_info':
        if game_state['money'] >= 2000:
            game_state['money'] -= 2000
            game_state['flags']['has_info'] = True
            flash("You bought information! You now have insider knowledge about police activity.", "success")
        else:
            flash("You don't have enough money for information!", "danger")

    elif action == 'recruit':
        if game_state['money'] >= 10000:
            game_state['money'] -= 10000
            game_state['members'] += 1
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

    if drug_type not in game_state['drug_prices']:
        flash("Invalid drug type!", "danger")
        return redirect(url_for('crackhouse'))

    price = game_state['drug_prices'][drug_type]

    if action == 'buy':
        cost = price * quantity
        if game_state['money'] >= cost:
            game_state['money'] -= cost
            game_state['drugs'][drug_type] += quantity
            flash(f"You bought {quantity} kilo(s) of {drug_type} for ${cost:,}!", "success")
        else:
            flash(f"You don't have enough money! Need ${cost:,}.", "danger")
    elif action == 'sell':
        current_qty = game_state['drugs'][drug_type]
        if current_qty >= quantity:
            game_state['drugs'][drug_type] -= quantity
            revenue = price * quantity
            game_state['money'] += revenue
            flash(f"You sold {quantity} kilo(s) of {drug_type} for ${revenue:,}!", "success")

            # Chance to recruit new member from big drug sales
            if revenue >= 5000:  # Big sale threshold
                if random.random() < 0.25:  # 25% chance for big sales
                    game_state['members'] += 1
                    flash("Word of your successful drug operation spread! A new recruit joined your gang!", "success")
        else:
            flash(f"You don't have enough {drug_type} to sell!", "danger")

    save_game_state(game_state)
    return redirect(url_for('crackhouse'))

@app.route('/bulk_purchase', methods=['POST'])
def bulk_purchase():
    """Handle bulk drug purchases from Steve's Closet"""
    game_state = get_game_state()
    drug_type = request.form.get('drug_type')
    quantity = int(request.form.get('quantity', 1))

    if drug_type not in game_state['drug_prices']:
        flash("Invalid drug type!", "danger")
        return redirect(url_for('closet'))

    regular_price = game_state['drug_prices'][drug_type]
    bulk_price = int(regular_price * 0.8)  # 20% discount for 10+ kilos
    total_cost = bulk_price * quantity

    if game_state['money'] >= total_cost:
        game_state['money'] -= total_cost
        game_state['drugs'][drug_type] += quantity
        flash(f"Bulk purchase successful! Bought {quantity} kilos of {drug_type} for ${total_cost:,} (20% discount applied)!", "success")
    else:
        flash(f"You don't have enough money! Need ${total_cost:,}.", "danger")

    save_game_state(game_state)
    return redirect(url_for('closet'))

@app.route('/closet')
def closet():
    """Steve's Secret Closet"""
    game_state = get_game_state()
    game_state['current_location'] = "closet"
    save_game_state(game_state)
    return render_template('closet.html', game_state=game_state)

@app.route('/search_closet')
def search_closet():
    """Search Steve's Secret Closet for hidden treasures"""
    game_state = get_game_state()

    # Only allow searching if in closet
    if game_state['current_location'] != "closet":
        flash("You need to be in Steve's Closet to search it!", "warning")
        return redirect(url_for('bar'))

    search_result = random.random()

    if search_result < 0.05:  # 5% chance - major drug stash
        drug_types = ['weed', 'crack', 'coke', 'ice', 'pixie_dust']
        drug = random.choice(drug_types)
        amount = random.randint(15, 30)
        game_state['drugs'][drug] += amount
        result = f"You find a hidden compartment! Steve must have forgotten about this stash. You gain {amount} kilos of {drug}!"
        flash(result, "success")

    elif search_result < 0.15:  # 10% chance - weapon cache
        weapons = [
            ('pistols', 1, "an extra pistol"),
            ('bullets', random.randint(20, 50), "bullets"),
            ('grenades', random.randint(2, 5), "grenades"),
            ('vampire_bat', 1, "a vampire bat"),
            ('uzis', 1, "an Uzi with 25 bullets")
        ]
        weapon_choice = random.choice(weapons)
        if weapon_choice[0] == 'uzis':
            game_state['weapons']['uzis'] += weapon_choice[1]
            game_state['weapons']['bullets'] += 25
            result = f"You find a dusty crate containing {weapon_choice[2]}!"
        else:
            game_state['weapons'][weapon_choice[0]] += weapon_choice[1]
            result = f"You find a hidden weapons cache containing {weapon_choice[1]} {weapon_choice[2]}!"
        flash(result, "success")

    elif search_result < 0.25:  # 10% chance - money
        money_found = random.randint(500, 2000)
        game_state['money'] += money_found
        result = f"You discover an old safe hidden behind some boxes! You gain ${money_found:,}!"
        flash(result, "success")

    elif search_result < 0.35:  # 10% chance - trap/alarm
        damage = random.randint(5, 15)
        game_state['health'] = max(0, game_state['health'] - damage)
        result = f"You trigger a silent alarm system! Security arrives and roughs you up for {damage} damage!"
        flash(result, "danger")

    elif search_result < 0.50:  # 15% chance - small find
        small_finds = [
            ("some loose change", lambda: setattr(game_state, 'money', game_state['money'] + random.randint(25, 100))),
            ("a few stray bullets", lambda: setattr(game_state, 'weapons', {**game_state['weapons'], 'bullets': game_state['weapons']['bullets'] + random.randint(5, 15)})),
            ("an old knife", lambda: setattr(game_state, 'weapons', {**game_state['weapons'], 'knife': game_state['weapons']['knife'] + 1}))
        ]
        find = random.choice(small_finds)
        find[1]()
        result = f"You find {find[0]} while rummaging through the storage."
        flash(result, "info")

    else:  # 50% chance - nothing
        result = "You search thoroughly but find nothing out of the ordinary. Steve keeps his closet well-organized."
        flash(result, "info")

    # Increment steps for searching
    game_state['steps'] += 1
    if game_state['steps'] >= game_state['max_steps']:
        game_state['day'] += 1
        game_state['steps'] = 0

    save_game_state(game_state)
    return redirect(url_for('closet'))

@app.route('/search_picknsave')
def search_picknsave():
    """Search Pick n' Save for hidden secrets"""
    game_state = get_game_state()

    # Only allow searching if in picknsave
    if game_state['current_location'] != "picknsave":
        flash("You need to be in Pick n' Save to search it!", "warning")
        return redirect(url_for('city'))

    search_result = random.random()

    if search_result < 0.03:  # 3% chance - rare item
        # Chance for special items
        special_items = [
            ("a fake ID kit", lambda: setattr(game_state, 'flags', {**game_state['flags'], 'has_id': True})),
            ("classified police documents", lambda: setattr(game_state, 'flags', {**game_state['flags'], 'has_info': True})),
            ("a gang recruitment flyer", lambda: setattr(game_state, 'members', game_state['members'] + 1))
        ]
        item = random.choice(special_items)
        item[1]()
        result = f"You find {item[0]} hidden in the store's back office!"
        flash(result, "success")

    elif search_result < 0.13:  # 10% chance - weapon
        weapons = [
            ('bullets', random.randint(10, 30), "bullets"),
            ('grenades', random.randint(1, 3), "grenades"),
            ('knife', 1, "a knife")
        ]
        weapon_choice = random.choice(weapons)
        game_state['weapons'][weapon_choice[0]] += weapon_choice[1]
        result = f"You find a hidden compartment containing {weapon_choice[1]} {weapon_choice[2]}!"
        flash(result, "success")

    elif search_result < 0.23:  # 10% chance - drugs
        drug_types = ['weed', 'crack', 'percs']
        drug = random.choice(drug_types)
        amount = random.randint(3, 8)
        game_state['drugs'][drug] += amount
        result = f"You discover some contraband hidden in the storage room! You gain {amount} kilos of {drug}!"
        flash(result, "success")

    elif search_result < 0.33:  # 10% chance - money
        money_found = random.randint(200, 600)
        game_state['money'] += money_found
        result = f"You find a forgotten cash register drawer! You gain ${money_found:,}!"
        flash(result, "success")

    elif search_result < 0.43:  # 10% chance - trap
        damage = random.randint(8, 20)
        game_state['health'] = max(0, game_state['health'] - damage)
        result = f"You accidentally knock over some cleaning supplies! The store manager confronts you and deals {damage} damage!"
        flash(result, "danger")

    elif search_result < 0.58:  # 15% chance - small find
        small_finds = [
            ("some spare change", lambda: setattr(game_state, 'money', game_state['money'] + random.randint(15, 75))),
            ("a few loose bullets", lambda: setattr(game_state, 'weapons', {**game_state['weapons'], 'bullets': game_state['weapons']['bullets'] + random.randint(3, 10)})),
            ("a candy bar", lambda: setattr(game_state, 'health', min(100, game_state['health'] + 5)))
        ]
        find = random.choice(small_finds)
        find[1]()
        result = f"You find {find[0]} while searching the shelves."
        flash(result, "info")

    else:  # 42% chance - nothing
        result = "You search the store discreetly but find nothing unusual. The employees are watching you closely."
        flash(result, "info")

    # Increment steps for searching
    game_state['steps'] += 1
    if game_state['steps'] >= game_state['max_steps']:
        game_state['day'] += 1
        game_state['steps'] = 0

    save_game_state(game_state)
    return redirect(url_for('picknsave'))

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
        if game_state['money'] >= 200:
            game_state['money'] -= 200
            # Quick service restores some health
            health_gain = random.randint(5, 15)
            game_state['health'] = min(100, game_state['health'] + health_gain)
            flash(f"You enjoyed a quick service and gained {health_gain} health!", "success")
        else:
            flash("You don't have enough money for a quick service!", "danger")

    elif action == 'vip_experience':
        if game_state['money'] >= 500:
            game_state['money'] -= 500
            # VIP experience restores more health
            health_gain = random.randint(15, 30)
            game_state['health'] = min(100, game_state['health'] + health_gain)
            flash(f"You had a VIP experience and gained {health_gain} health!", "success")
        else:
            flash("You don't have enough money for a VIP experience!", "danger")

    elif action == 'recruit_hooker':
        if game_state['money'] >= 1000:
            game_state['money'] -= 1000
            game_state['members'] += 1
            # Recruiting also gives health boost
            health_gain = random.randint(10, 20)
            game_state['health'] = min(100, game_state['health'] + health_gain)
            flash(f"You recruited a hooker to your gang and gained {health_gain} health!", "success")
        else:
            flash("You don't have enough money to recruit a hooker!", "danger")

    save_game_state(game_state)
    return redirect(url_for('visit_prostitutes'))

@app.route('/search_deeper')
def search_deeper():
    """Search deeper when a secret has been found"""
    game_state = get_game_state()

    # Check if a secret was found
    if not session.get('secret_found', False):
        flash("You haven't found any secrets to search deeper for.", "info")
        return redirect(url_for('alleyway'))

    secret_room = session.get('secret_room', 'secret_room')

    # Clear the secret found flag
    session['secret_found'] = False
    session.modified = True

    # Better rewards for deeper search
    deeper_result = random.random()

    if deeper_result < 0.3:  # 30% chance - great reward
        if random.random() < 0.5:
            # Massive money find
            money_found = random.randint(1000, 3000)
            game_state['money'] += money_found
            result = f"You discover a hidden vault! You gain ${money_found:,}!"
            flash(result, "success")
        else:
            # Rare weapon
            rare_weapons = ['uzi', 'grenade', 'missile_launcher']
            weapon = random.choice(rare_weapons)
            if weapon == 'uzi':
                game_state['weapons']['uzis'] += 1
                game_state['weapons']['bullets'] += 50
                result = "You find a hidden Uzi with 50 bullets!"
            elif weapon == 'grenade':
                game_state['weapons']['grenades'] += random.randint(2, 5)
                result = f"You find a crate of grenades! You gain {game_state['weapons']['grenades']} grenades!"
            elif weapon == 'missile_launcher':
                game_state['weapons']['missile_launcher'] += 1
                game_state['weapons']['missiles'] += random.randint(3, 8)
                result = f"You find a missile launcher with {game_state['weapons']['missiles']} missiles!"
            flash(result, "success")

    elif deeper_result < 0.6:  # 30% chance - good reward
        # Large drug stash
        drug_types = ['weed', 'crack', 'coke', 'ice']
        drug = random.choice(drug_types)
        amount = random.randint(8, 15)
        game_state['drugs'][drug] += amount
        result = f"You find a major drug operation stash! You gain {amount} kilos of {drug}!"
        flash(result, "success")

    elif deeper_result < 0.8:  # 20% chance - trap
        damage = random.randint(25, 50)
        game_state['health'] = max(0, game_state['health'] - damage)
        result = f"You trigger a deadly trap! A collapsing wall crushes you for {damage} damage!"
        flash(result, "danger")

    else:  # 20% chance - moderate reward
        money_found = random.randint(500, 1500)
        game_state['money'] += money_found
        result = f"You find a concealed safe! You gain ${money_found:,}!"
        flash(result, "success")

    # Increment steps for deeper searching
    game_state['steps'] += 2  # Deeper search costs more time
    if game_state['steps'] >= game_state['max_steps']:
        game_state['day'] += 1
        game_state['steps'] = 0

    save_game_state(game_state)
    return redirect(url_for('alleyway'))

@app.route('/search_room')
def search_room():
    """Search the current room for hidden treasures or traps"""
    game_state = get_game_state()

    # Get current room from session
    current_room_id = session.get('current_alleyway_room', 'entrance')

    # Get room data from JSON files
    if rooms_data and current_room_id in rooms_data:
        current_room = {
            'title': rooms_data[current_room_id]['title'],
            'description': rooms_data[current_room_id]['description'],
            'exits': rooms_data[current_room_id]['exits']
        }
    elif rooms_config and 'rooms' in rooms_config and current_room_id in rooms_config['rooms']:
        current_room = rooms_config['rooms'][current_room_id]
    else:
        # Fallback
        current_room = {
            'title': 'Dark Alley Entrance',
            'description': 'You stand at the entrance of a dark alleyway. The streetlights cast long shadows, and you can hear distant sounds echoing off the walls.',
            'exits': {
                'north': 'dead_end',
                'south': 'city',
                'east': 'side_street',
                'west': 'dumpster'
            }
        }

    # Check if this room can be searched
    if not ('secret' in current_room['title'].lower() or 'mysterious' in current_room['description'].lower() or 'hidden' in current_room['title'].lower()):
        flash("There's nothing special to search for here.", "info")
        return redirect(url_for('alleyway'))

    # Use search results from rooms_config.json if available
    if rooms_config and 'searchable_rooms' in rooms_config and current_room_id in rooms_config['searchable_rooms']:
        search_results = rooms_config['searchable_rooms'][current_room_id]['search_results']
        search_result = random.random()

        # Find the appropriate result based on probability ranges
        for threshold, result_data in search_results.items():
            threshold_float = float(threshold)
            if search_result <= threshold_float:
                result_type = result_data.get('description', 'nothing')

                if result_type == 'trap':
                    damage_range = result_data.get('damage', [5, 20])
                    damage = random.randint(damage_range[0], damage_range[1])
                    game_state['health'] = max(0, game_state['health'] - damage)
                    result = result_data.get('message', f"You find a trap! You take {damage} damage!").format(damage=damage)
                    flash(result, "danger")
                elif result_type == 'secret_hint':
                    result = result_data.get('message', "You find something mysterious!")
                    if result_data.get('sets_secret_found', False):
                        session['secret_found'] = True
                        session['secret_room'] = current_room_id
                        session.modified = True
                    flash(result, "warning")
                elif result_type == 'weapon_cache':
                    bullets_range = result_data.get('bullets', [5, 15])
                    bullets = random.randint(bullets_range[0], bullets_range[1])
                    game_state['weapons']['bullets'] += bullets
                    result = result_data.get('message', f"You find {bullets} bullets!").format(bullets=bullets)
                    flash(result, "success")
                elif result_type == 'drug_stash':
                    drug_types = result_data.get('drugs', ['weed'])
                    drug = random.choice(drug_types)
                    amount_range = result_data.get('amount', [1, 3])
                    amount = random.randint(amount_range[0], amount_range[1])
                    game_state['drugs'][drug] += amount
                    result = result_data.get('message', f"You find {amount} kilos of {drug}!").format(amount=amount, drug=drug)
                    flash(result, "success")
                elif result_type == 'money':
                    money_range = result_data.get('money_range', [50, 200])
                    money_found = random.randint(money_range[0], money_range[1])
                    game_state['money'] += money_found
                    result = result_data.get('message', f"You find ${money_found}!").format(money=money_found)
                    flash(result, "success")
                else:  # nothing or other
                    result = result_data.get('message', "You search thoroughly but find nothing.")
                    flash(result, "info")
                break
    else:
        # Fallback to hardcoded logic for rooms not in config
        search_result = random.random()

        if current_room_id == 'secret_room':
            # Secret room has better rewards but also traps
            if search_result < 0.1:  # 10% chance - trap
                damage = random.randint(15, 35)
                game_state['health'] = max(0, game_state['health'] - damage)
                result = f"You trigger a trap! A hidden spike pit injures you for {damage} damage!"
                flash(result, "danger")
            elif search_result < 0.25:  # 15% chance - secret hint
                result = "You find a mysterious inscription on the wall: 'The true treasure lies deeper within.' You sense there might be more to discover!"
                flash(result, "warning")
                # Store that a secret was found for deeper search
                session['secret_found'] = True
                session['secret_room'] = current_room_id
                session.modified = True
            elif search_result < 0.45:  # 20% chance - weapon cache
                game_state['weapons']['bullets'] += random.randint(10, 25)
                result = f"You find a hidden weapon cache! You gain {game_state['weapons']['bullets']} bullets!"
                flash(result, "success")
            elif search_result < 0.65:  # 20% chance - drug stash
                drug_types = ['weed', 'crack', 'coke']
                drug = random.choice(drug_types)
                amount = random.randint(2, 5)
                game_state['drugs'][drug] += amount
                result = f"You discover a drug stash! You find {amount} kilos of {drug}!"
                flash(result, "success")
            elif search_result < 0.85:  # 20% chance - money
                money_found = random.randint(200, 800)
                game_state['money'] += money_found
                result = f"You find a hidden stash of cash! You gain ${money_found}!"
                flash(result, "success")
            else:  # 15% chance - nothing special
                result = "You search thoroughly but find nothing of value."
                flash(result, "info")

        elif current_room_id == 'hidden_entrance':
            # Hidden entrance has moderate rewards
            if search_result < 0.15:  # 15% chance - trap
                damage = random.randint(10, 25)
                game_state['health'] = max(0, game_state['health'] - damage)
                result = f"You disturb a sleeping rat colony! They attack you for {damage} damage!"
                flash(result, "danger")
            elif search_result < 0.4:  # 25% chance - small reward
                money_found = random.randint(50, 200)
                game_state['money'] += money_found
                result = f"You find some loose change and bills! You gain ${money_found}!"
                flash(result, "success")
            elif search_result < 0.6:  # 20% chance - ammo
                game_state['weapons']['bullets'] += random.randint(5, 15)
                result = f"You find some discarded ammo! You gain {game_state['weapons']['bullets']} bullets!"
                flash(result, "success")
            else:  # 40% chance - nothing
                result = "The area looks like it's been searched before. Nothing here."
                flash(result, "info")

        elif current_room_id == 'underground':
            # Underground passage has mixed results
            if search_result < 0.2:  # 20% chance - trap
                damage = random.randint(20, 40)
                game_state['health'] = max(0, game_state['health'] - damage)
                result = f"You step on a pressure plate! Poison darts shoot out, dealing {damage} damage!"
                flash(result, "danger")
            elif search_result < 0.5:  # 30% chance - good reward
                if random.random() < 0.5:
                    # Money
                    money_found = random.randint(300, 600)
                    game_state['money'] += money_found
                    result = f"You find a waterproof bag with cash! You gain ${money_found}!"
                else:
                    # Drugs
                    drug_types = ['weed', 'crack']
                    drug = random.choice(drug_types)
                    amount = random.randint(3, 7)
                    game_state['drugs'][drug] += amount
                    result = f"You find a hidden compartment with drugs! You gain {amount} kilos of {drug}!"
                flash(result, "success")
            else:  # 50% chance - minor find or nothing
                if random.random() < 0.3:
                    game_state['weapons']['bullets'] += random.randint(3, 8)
                    result = f"You find a few loose bullets! You gain {game_state['weapons']['bullets']} bullets!"
                    flash(result, "success")
                else:
                    result = "The underground passage is damp and empty. Nothing of interest."
                    flash(result, "info")

        else:
            # Generic secret areas
            if search_result < 0.25:  # 25% chance - trap
                damage = random.randint(5, 20)
                game_state['health'] = max(0, game_state['health'] - damage)
                result = f"You find a trap! You take {damage} damage!"
                flash(result, "danger")
            elif search_result < 0.6:  # 35% chance - small reward
                money_found = random.randint(25, 150)
                game_state['money'] += money_found
                result = f"You find some hidden money! You gain ${money_found}!"
                flash(result, "success")
            else:  # 40% chance - nothing
                result = "You search carefully but find nothing special."
                flash(result, "info")

    # Increment steps for searching
    game_state['steps'] += 1
    if game_state['steps'] >= game_state['max_steps']:
        game_state['day'] += 1
        game_state['steps'] = 0

    save_game_state(game_state)
    return redirect(url_for('alleyway'))

@app.route('/move_room/<direction>')
def move_room(direction):
    """Move to a different room in the alleyway"""
    game_state = get_game_state()

    # Get current room from session, default to entrance
    current_room_id = session.get('current_alleyway_room', 'entrance')

    # Get room exits from JSON files
    if rooms_data and current_room_id in rooms_data and 'exits' in rooms_data[current_room_id]:
        exits = rooms_data[current_room_id]['exits']
    elif rooms_config and 'rooms' in rooms_config and current_room_id in rooms_config['rooms']:
        exits = rooms_config['rooms'][current_room_id]['exits']
    else:
        # Fallback exits
        exits = {
            'north': 'dead_end',
            'south': 'city',
            'east': 'side_street',
            'west': 'dumpster'
        }

    # Get the exit for the given direction
    if direction in exits:
        next_room = exits[direction]
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
    game_state['steps'] += 1
    if game_state['steps'] >= game_state['max_steps']:
        game_state['day'] += 1
        game_state['steps'] = 0

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
            combat_id = f"npc_{list(npcs_data.keys())[list(npcs_data.values()).index(npc)]}_{random.randint(1000, 9999)}"

            # Initialize fight log
            fight_log = [f"You encounter {npc['name']}! They look hostile...", f"Combat begins against {enemy_type}!"]
            session['fight_log'] = fight_log
            session.modified = True

            return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=1, combat_active=combat_active, combat_id=combat_id, npc_id=list(npcs_data.keys())[list(npcs_data.values()).index(npc)], fight_log=fight_log)

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
        game_state = {
            'player_name': player_name,
            'gang_name': gang_name,
            'money': 1000,
            'account': 0,
            'loan': 0,
            'members': 1,
            'squidies': 25,
            'squidies_pistols': 10,
            'squidies_uzis': 5,
            'squidies_bullets': 100,
            'squidies_grenades': 20,
            'squidies_missile_launcher': 2,
            'squidies_missiles': 10,
            'day': 1,
            'health': 30,
            'steps': 0,
            'max_steps': 15,
            'current_score': 0,
            'current_location': 'city',
            'drug_prices': {
                'weed': 500,
                'crack': 1000,
                'coke': 2000,
                'ice': 1500,
                'percs': 800,
                'pixie_dust': 3000
            },
            'lives': 3,
            'damage': 0,
            'flags': {'has_id': False, 'has_info': False},
            'weapons': {
                'pistols': 1,  # Start with 1 pistol
                'bullets': 10,  # Start with 10 bullets
                'uzis': 0,
                'grenades': 0,
                'barbed_wire_bat': 0,
                'missile_launcher': 0,
                'missiles': 0,
                'vest': 0,
                'knife': 0,
                'ghost_guns': 0
            },
            'drugs': {
                'weed': 0,
                'crack': 5,
                'coke': 0,
                'ice': 0,
                'percs': 0,
                'pixie_dust': 0
            }
        }

        save_game_state(game_state)
        return redirect(url_for('city'))

    return render_template('new_game.html')

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
    message = f"{npc['name']} says: Hello, {game_state['player_name']}. What can I do for you?"
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
    message = f"{npc['name']} offers to trade with you."
    return render_template('npc_interaction.html', npc=npc, action='trade', message=message, game_state=game_state)

@app.route('/fight_npc/<npc_id>', methods=['POST'])
def fight_npc(npc_id):
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    npc = npcs_data[npc_id]
    game_state = get_game_state()
    message = f"You engage in combat with {npc['name']}!"
    # Start MUD fight with NPC
    enemy_health = npc.get('hp', 50)  # Default 50 HP if not specified
    enemy_type = npc['name']
    combat_active = True
    combat_id = f"npc_{npc_id}_{random.randint(1000, 9999)}"

    # Initialize fight log
    fight_log = [f"You engage in combat with {npc['name']}!", f"Combat begins against {enemy_type}!"]
    session['fight_log'] = fight_log
    session.modified = True

    return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=1, combat_active=combat_active, combat_id=combat_id, npc_id=npc_id, fight_log=fight_log)

@app.route('/pickup_loot/<npc_id>')
def pickup_loot(npc_id):
    if npc_id not in npcs_data:
        return redirect(url_for('city'))
    npc = npcs_data[npc_id]
    game_state = get_game_state()
    if not npc['is_alive']:
        game_state['money'] += 100
        message = f"You search {npc['name']}'s body and find $100!"
    else:
        message = "You can't loot a living person."
    save_game_state(game_state)
    return render_template('npc_interaction.html', npc=npc, action='loot', message=message, game_state=game_state)

@app.route('/npcs')
def npcs():
    """View NPCs in current location"""
    game_state = get_game_state()
    location_npcs = [npc for npc in npcs_data.values() if npc.get('location') == game_state['current_location']]
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
    combat_id = f"police_{random.randint(1000, 9999)}"

    # Initialize fight log
    fight_log = [f"Oh no! {num_cops} police officers spot you and give chase!", f"Combat begins against {enemy_type}!"]
    session['fight_log'] = fight_log
    session.modified = True

    return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=num_cops, combat_active=combat_active, combat_id=combat_id, fight_log=fight_log)

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
        if escape_chance < 0.6:  # 60% chance to escape
            flash("You manage to escape the police chase!", "success")
            # Chance to recruit a impressed bystander
            if random.random() < 0.2:  # 20% chance
                game_state['members'] += 1
                flash("A bystander was impressed by your escape and joined your gang!", "success")
            save_game_state(game_state)
            return redirect(url_for('city'))
        else:
            # Failed to escape, take damage
            damage = random.randint(10, 30)
            if game_state['weapons']['vest'] > 0:
                game_state['weapons']['vest'] -= 1
                damage = max(0, damage - 20)  # Vest reduces damage
                message = f"You failed to escape! Your vest absorbed some damage but you still took {damage} damage."
            else:
                message = f"You failed to escape and took {damage} damage from police gunfire!"

            game_state['damage'] += damage
            if game_state['damage'] >= 10:
                game_state['lives'] -= 1
                final_damage = game_state['damage']  # Store before resetting
                game_state['damage'] = 0
                game_state['health'] = 30
                enemy_type = f"{num_cops} Police Officers"
                enemy_count = num_cops
                if game_state['lives'] <= 0:
                    save_game_state(game_state)
                    fight_log = [f"You were defeated by {enemy_type} and took {final_damage} damage. This was your final life."]
                    return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, final_damage=final_damage, fight_log=fight_log)
                else:
                    save_game_state(game_state)
                    fight_log = [f"You were defeated by {enemy_type} and took {final_damage} damage. You lost a life but can continue."]
                    return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, final_damage=final_damage, fight_log=fight_log)

            # Return to MUD fight with updated state
            enemy_health = num_cops * 10
            enemy_type = f"{num_cops} Police Officers"
            combat_active = True
            combat_id = f"police_{random.randint(1000, 9999)}"
            return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=num_cops, combat_active=combat_active, combat_id=combat_id)

    elif action == 'shoot':
        # Combat with police
        if weapon == 'pistol' and game_state['weapons']['bullets'] > 0:
            game_state['weapons']['bullets'] -= 1
            cops_killed = min(num_cops, random.randint(1, 3))
            num_cops -= cops_killed

            # Police shoot back
            damage = random.randint(5, 25) * (num_cops if num_cops > 0 else 1)
            if game_state['weapons']['vest'] > 0:
                game_state['weapons']['vest'] -= 1
                damage = max(0, damage - 20)

            game_state['damage'] += damage

            if num_cops <= 0:
                flash(f"You killed all the cops and escaped! {cops_killed} officers down!", "success")
                save_game_state(game_state)
                return redirect(url_for('city'))
            else:
                # Add kill message to flash
                if cops_killed == 1:
                    flash(f"💀 You killed 1 police officer!", "info")
                else:
                    flash(f"💀 You killed {cops_killed} police officers!", "info")
                message = f"You killed {cops_killed} cop(s) but {num_cops} remain and shot back! You took {damage} damage."
                if game_state['damage'] >= 10:
                    game_state['lives'] -= 1
                    final_damage = game_state['damage']  # Store before resetting
                    game_state['damage'] = 0
                    game_state['health'] = 30
                    enemy_type = f"{num_cops} Police Officers"
                    enemy_count = num_cops
                    if game_state.lives <= 0:
                        save_game_state(game_state)
                        fight_log = [f"You were defeated by {enemy_type} and took {final_damage} damage. This was your final life."]
                        return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, final_damage=final_damage, fight_log=fight_log)
                    else:
                        save_game_state(game_state)
                        fight_log = [f"You were defeated by {enemy_type} and took {final_damage} damage. You lost a life but can continue."]
                        return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, final_damage=final_damage, fight_log=fight_log)

        elif weapon == 'uzi' and game_state['weapons']['bullets'] > 0:
            game_state['weapons']['bullets'] -= min(10, game_state['weapons']['bullets'])  # Uzi uses 10 bullets
            cops_killed = min(num_cops, random.randint(2, 5))
            num_cops -= cops_killed

            damage = random.randint(10, 40) * (num_cops if num_cops > 0 else 1)
            if game_state['weapons']['vest'] > 0:
                game_state['weapons']['vest'] -= 1
                damage = max(0, damage - 20)

            game_state['damage'] += damage

            if num_cops <= 0:
                flash(f"You sprayed the cops with your Uzi! {cops_killed} officers down!", "success")
                save_game_state(game_state)
                return redirect(url_for('city'))
            else:
                message = f"You sprayed {cops_killed} cop(s) but {num_cops} remain! Massive shootout - you took {damage} damage."

        elif weapon == 'grenade' and game_state['weapons']['grenades'] > 0:
            game_state['weapons']['grenades'] -= 1
            cops_killed = min(num_cops, random.randint(3, 6))
            num_cops -= cops_killed

            if num_cops <= 0:
                flash(f"Grenade explosion! {cops_killed} cops eliminated!", "success")
                save_game_state(game_state)
                return redirect(url_for('city'))
            else:
                damage = random.randint(20, 50)
                if game_state['weapons']['vest'] > 0:
                    game_state['weapons']['vest'] -= 1
                    damage = max(0, damage - 20)
                game_state['damage'] += damage
                message = f"Grenade blast killed {cops_killed} cops but you're hurt too! {damage} damage."

        elif weapon == 'missile_launcher' and game_state['weapons']['missiles'] > 0:
            game_state['weapons']['missiles'] -= 1
            cops_killed = num_cops  # Missile kills all remaining cops
            num_cops = 0

            damage = random.randint(30, 60)
            if game_state['weapons']['vest'] > 0:
                game_state['weapons']['vest'] -= 1
                damage = max(0, damage - 20)
            game_state['damage'] += damage

            flash(f"RPG blast! All {cops_killed} cops eliminated!", "success")
            save_game_state(game_state)
            return redirect(url_for('city'))

        elif weapon == 'knife':
            damage_to_player = random.randint(15, 35) * num_cops
            if game_state['weapons']['vest'] > 0:
                game_state['weapons']['vest'] -= 1
                damage_to_player = max(0, damage_to_player - 20)
            game_state['damage'] += damage_to_player
            message = f"You tried to fight with a knife but got overwhelmed! {damage_to_player} damage from {num_cops} cops."

        elif weapon == 'vampire_bat' and game_state['weapons']['vampire_bat'] > 0:
            cops_killed = min(num_cops, random.randint(1, 2))  # Vampire bat kills 1-2 cops
            num_cops -= cops_killed

            damage = random.randint(5, 25) * (num_cops if num_cops > 0 else 1)
            if game_state['weapons']['vest'] > 0:
                game_state['weapons']['vest'] -= 1
                damage = max(0, damage - 20)
            game_state['damage'] += damage

            if num_cops <= 0:
                flash(f"You beat the cops senseless with your vampire bat! {cops_killed} officers down!", "success")
                save_game_state(game_state)
                return redirect(url_for('city'))
            else:
                message = f"You smashed {cops_killed} cop(s) with your vampire bat but {num_cops} remain! You took {damage} damage."

        # Check if player died
        if game_state['damage'] >= 10:
            game_state['lives'] -= 1
            final_damage = game_state['damage']  # Store before resetting
            game_state['damage'] = 0
            game_state['health'] = 30
            enemy_type = f"{num_cops} Police Officers"
            enemy_count = num_cops
            if game_state.lives <= 0:
                save_game_state(game_state)
                fight_log = [f"You were defeated by {enemy_type} and took {final_damage} damage. This was your final life."]
                return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, final_damage=final_damage, fight_log=fight_log)
            else:
                save_game_state(game_state)
                fight_log = [f"You were defeated by {enemy_type} and took {final_damage} damage. You lost a life but can continue."]
                return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, final_damage=final_damage, fight_log=fight_log)

        # Return to MUD fight with updated state
        enemy_health = num_cops * 10
        enemy_type = f"{num_cops} Police Officers"
        combat_active = True
        combat_id = f"police_{random.randint(1000, 9999)}"
        return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=num_cops, combat_active=combat_active, combat_id=combat_id)

    save_game_state(game_state)
    return redirect(url_for('city'))

@app.route('/process_fight_action', methods=['POST'])
def process_fight_action():
    """Handle MUD-style fight actions"""
    game_state = get_game_state()
    combat_id = request.form.get('combat_id')
    action = request.form.get('action')
    weapon = request.form.get('weapon', 'pistol')
    drug = request.args.get('drug')

    # Get combat state from session (simplified - in real implementation you'd store full combat state)
    enemy_health = int(request.form.get('enemy_health', 30))
    enemy_type = request.form.get('enemy_type', 'Enemy')
    enemy_count = int(request.form.get('enemy_count', 1))

    # Initialize or get fight log from session
    fight_log = session.get('fight_log', [])
    if not fight_log:
        fight_log = [f"Combat begins against {enemy_type}!"]
        session['fight_log'] = fight_log
        session.modified = True

    # Track total enemies killed this fight
    if 'total_killed' not in session:
        session['total_killed'] = 0
        session.modified = True

    # Track initial enemy count for victory message
    if 'initial_enemy_count' not in session:
        session['initial_enemy_count'] = enemy_count
        session.modified = True

    # Process action
    if action == 'attack':
        weapon_name = weapon.replace('_', ' ').title()
        total_player_damage = 0
        killed_this_turn = 0

        # Player's attack
        if weapon == 'pistol' and game_state['weapons']['pistols'] > 0 and game_state['weapons']['bullets'] > 0:
            game_state['weapons']['bullets'] -= 1
            damage = random.randint(15, 25)
            total_player_damage += damage
            fight_log.append(battle_descriptions['attack_messages']['pistol'])
        elif weapon == 'ghost_gun' and game_state['weapons']['ghost_guns'] > 0 and game_state['weapons']['bullets'] > 0:
            game_state['weapons']['bullets'] -= 1
            damage = random.randint(15, 25)
            total_player_damage += damage
            fight_log.append(battle_descriptions['attack_messages']['ghost_gun'])
        elif weapon == 'pistol_switch' and game_state['weapons'].get('upgraded_pistols', 0) > 0 and game_state['weapons']['bullets'] >= 2:
            # Full auto pistol fires 3-5 shots per turn
            shots_fired = random.randint(3, 5)
            bullets_needed = shots_fired
            if game_state['weapons']['bullets'] >= bullets_needed:
                game_state['weapons']['bullets'] -= bullets_needed
                total_damage = 0
                for shot in range(shots_fired):
                    shot_damage = random.randint(15, 25)  # Base pistol damage per shot
                    total_damage += shot_damage
                    if shot < shots_fired - 1:  # Don't show individual damage for last shot
                        fight_log.append(f"Shot {shot + 1}: {shot_damage} damage!")
                total_player_damage += total_damage
                fight_log.append(f"You unleash a full-auto burst from your upgraded pistol, firing {shots_fired} shots for {total_damage} total damage!")
            else:
                fight_log.append("You don't have enough bullets for a full-auto burst!")
        elif weapon == 'ghost_gun_switch' and game_state['weapons'].get('upgraded_ghost_guns', 0) > 0 and game_state['weapons']['bullets'] >= 2:
            # Full auto ghost gun fires 3-5 shots per turn
            shots_fired = random.randint(3, 5)
            bullets_needed = shots_fired
            if game_state['weapons']['bullets'] >= bullets_needed:
                game_state['weapons']['bullets'] -= bullets_needed
                total_damage = 0
                for shot in range(shots_fired):
                    shot_damage = random.randint(15, 25)  # Base ghost gun damage per shot
                    total_damage += shot_damage
                    if shot < shots_fired - 1:  # Don't show individual damage for last shot
                        fight_log.append(f"Shot {shot + 1}: {shot_damage} damage!")
                total_player_damage += total_damage
                fight_log.append(f"You unleash a full-auto burst from your upgraded ghost gun, firing {shots_fired} shots for {total_damage} total damage!")
            else:
                fight_log.append("You don't have enough bullets for a full-auto burst!")
        elif weapon == 'uzi' and game_state['weapons']['uzis'] > 0 and game_state['weapons']['bullets'] >= 3:
            game_state['weapons']['bullets'] -= 3
            damage = random.randint(20, 40)
            total_player_damage += damage
            fight_log.append(battle_descriptions['attack_messages']['uzi'])
        elif weapon == 'grenade' and game_state['weapons']['grenades'] > 0:
            game_state['weapons']['grenades'] -= 1
            damage = random.randint(30, 60)
            total_player_damage += damage
            fight_log.append(battle_descriptions['attack_messages']['grenade'])
        elif weapon == 'missile_launcher' and game_state['weapons']['missile_launcher'] > 0 and game_state['weapons']['missiles'] > 0:
            game_state['weapons']['missiles'] -= 1
            damage = random.randint(50, 100)
            total_player_damage += damage
            fight_log.append(battle_descriptions['attack_messages']['missile_launcher'])
        elif weapon == 'barbed_wire_bat' and game_state['weapons']['barbed_wire_bat'] > 0:
            damage = random.randint(25, 45)
            total_player_damage += damage
            fight_log.append(battle_descriptions['attack_messages']['barbed_wire_bat'])
        elif weapon == 'knife':
            damage = random.randint(10, 20)
            total_player_damage += damage
            fight_log.append(battle_descriptions['attack_messages']['knife'])

        # Gang members' attacks (if player has gang members)
        gang_damage = 0
        if game_state['members'] > 1:  # Player + at least 1 gang member
            gang_member_count = min(game_state['members'] - 1, 5)  # Max 5 gang members attack per turn
            weapons_available = []

            # Check what weapons are available for gang members
            if game_state['weapons']['pistols'] > 1 and game_state['weapons']['bullets'] >= gang_member_count:
                weapons_available.append('pistol')
            if game_state['weapons']['uzis'] > 0 and game_state['weapons']['bullets'] >= gang_member_count * 3:
                weapons_available.append('uzi')
            if game_state['weapons']['barbed_wire_bat'] > 0:
                weapons_available.append('barbed_wire_bat')
            if game_state['weapons']['knife'] > 0:
                weapons_available.append('knife')

            if weapons_available:
                # Each gang member gets a chance to attack
                for i in range(gang_member_count):
                    if enemy_health <= 0:
                        break

                    weapon_choice = random.choice(weapons_available)
                    member_damage = 0

                    if weapon_choice == 'pistol' and game_state['weapons']['bullets'] > 0:
                        game_state['weapons']['bullets'] -= 1
                        member_damage = random.randint(10, 20)
                    elif weapon_choice == 'uzi' and game_state['weapons']['bullets'] >= 3:
                        game_state['weapons']['bullets'] -= 3
                        member_damage = random.randint(15, 30)
                    elif weapon_choice == 'barbed_wire_bat':
                        member_damage = random.randint(15, 25)
                    elif weapon_choice == 'knife':
                        member_damage = random.randint(8, 15)

                    if member_damage > 0:
                        gang_damage += member_damage
                        fight_log.append(f"Gang member {i+1} attacks with {weapon_choice.replace('_', ' ')}, dealing {member_damage} damage!")

        # Calculate total damage and killed enemies
        total_damage = total_player_damage + gang_damage
        previous_enemy_health = enemy_health
        enemy_health -= total_damage

        # Calculate how many enemies were killed this turn
        if total_damage > 0:
            # Estimate killed enemies based on damage (rough approximation)
            # Assuming each enemy has ~15-25 HP on average
            avg_enemy_hp = 20
            killed_this_turn = min(enemy_count, max(1, total_damage // avg_enemy_hp))

            # Adjust for overkill - if we did more damage than remaining health
            if previous_enemy_health > 0 and enemy_health <= 0:
                killed_this_turn = enemy_count  # All remaining enemies killed

            # Deduct from Squidies gang total for any enemy kills (police or gangs)
            game_state['squidies'] = max(0, game_state['squidies'] - killed_this_turn)

            # Update total killed counter
            session['total_killed'] = session.get('total_killed', 0) + killed_this_turn
            session.modified = True

            # Add kill messages to fight log
            if killed_this_turn > 0:
                if "Police" in enemy_type:
                    if killed_this_turn == 1:
                        fight_log.append(battle_descriptions['kill_messages']['police_singular'])
                    else:
                        fight_log.append(battle_descriptions['kill_messages']['police_plural'].format(count=killed_this_turn))
                elif "Squidie" in enemy_type:
                    if killed_this_turn == 1:
                        fight_log.append(battle_descriptions['kill_messages']['squidie_singular'])
                    else:
                        fight_log.append(battle_descriptions['kill_messages']['squidie_plural'].format(count=killed_this_turn))
                    # Additional mention for Squidie kills
                    fight_log.append(battle_descriptions['squidie_specific']['gang_loss'].format(count=killed_this_turn))
                elif "Gang" in enemy_type:
                    if killed_this_turn == 1:
                        fight_log.append(battle_descriptions['kill_messages']['gang_singular'])
                    else:
                        fight_log.append(battle_descriptions['kill_messages']['gang_plural'].format(count=killed_this_turn))
                else:
                    if killed_this_turn == 1:
                        fight_log.append(battle_descriptions['kill_messages']['generic_singular'])
                    else:
                        fight_log.append(battle_descriptions['kill_messages']['generic_plural'].format(count=killed_this_turn))

        # Update enemy count
        enemy_count = max(0, enemy_count - killed_this_turn)

        # Enemy attacks back
        if enemy_health > 0 and enemy_count > 0:
            enemy_damage = random.randint(5, 15) * enemy_count
            if game_state['weapons']['vest'] > 0 and random.random() < 0.5:
                game_state['weapons']['vest'] -= 1
                enemy_damage = max(0, enemy_damage - 20)
                fight_log.append(f"The {enemy_type} attack! Your vest absorbs damage, you take {enemy_damage} damage!")
            else:
                game_state['damage'] += enemy_damage
                fight_log.append(f"The {enemy_type} counterattack, dealing {enemy_damage} damage!")

    elif action == 'defend':
        # Reduced enemy damage
        if enemy_health > 0:
            enemy_damage = random.randint(2, 10) * enemy_count
            game_state['damage'] += enemy_damage
            fight_log.append(f"You defend carefully. The {enemy_type} deal {enemy_damage} damage!")

    elif action == 'flee':
        if random.random() < 0.4:  # 40% chance to flee
            fight_log.append("You successfully flee from combat!")
            session['fight_log'] = fight_log
            session.modified = True
            flash("You successfully flee from combat!", "success")
            save_game_state(game_state)
            return redirect(url_for('city'))
        else:
            # Enemy attacks during flee attempt
            enemy_damage = random.randint(10, 20) * enemy_count
            game_state['damage'] += enemy_damage
            fight_log.append(f"You try to flee but the {enemy_type} attack, dealing {enemy_damage} damage!")

    elif action == 'change_weapon':
        # No combat action, just return to fight with same state
        fight_log.append("You take a moment to consider changing weapons.")

    elif action == 'use_drug':
        # Handle drug usage
        drug_name = drug.title() if drug else "Unknown"
        if drug and drug in game_state['drugs'] and game_state['drugs'][drug] > 0:
            game_state['drugs'][drug] -= 1
            if drug == 'crack':
                game_state['damage'] += 5
                fight_log.append(battle_descriptions['combat_status']['use_drug_crack'])
            elif drug == 'percs':
                healed = min(10, game_state['damage'])
                game_state['damage'] = max(0, game_state['damage'] - 10)
                fight_log.append(battle_descriptions['combat_status']['use_drug_percs'].format(healed=healed))
            else:
                fight_log.append(battle_descriptions['combat_status']['drug_generic'].format(drug_name=drug_name))
        else:
            fight_log.append(f"You try to use {drug_name} but have none!")

    # Check win/lose conditions
    if enemy_health <= 0:
        # Handle NPC-specific victory logic
        npc_id = request.form.get('npc_id')
        if npc_id and npc_id in npcs_data:
            npcs_data[npc_id]['is_alive'] = False
            with open('npcs.json', 'w') as f:
                json.dump(npcs_data, f, indent=2)
            game_state.money += 100  # Loot from defeated NPC
            fight_log.append(f"You defeated {npcs_data[npc_id]['name']} and looted $100!")

        # Chance to recruit a defeated enemy as a gang member
        if enemy_type != "Police Officers" and random.random() < 0.3:  # 30% chance
            game_state['members'] += 1
            fight_log.append("One of your defeated enemies has joined your gang!")

        # Calculate victory stats
        initial_count = session.get('initial_enemy_count', enemy_count)
        total_killed = session.get('total_killed', 0) + killed_this_turn
        escaped_count = initial_count - total_killed

        # Create victory message with kill/escape breakdown
        if "Police" in enemy_type:
            enemy_type_singular = "police officer"
            enemy_type_plural = "police officers"
        elif "Gang" in enemy_type or "Squidie" in enemy_type:
            enemy_type_singular = "gang member"
            enemy_type_plural = "gang members"
        else:
            enemy_type_singular = "enemy"
            enemy_type_plural = "enemies"

        if total_killed == 1:
            killed_text = f"1 {enemy_type_singular}"
        else:
            killed_text = f"{total_killed} {enemy_type_plural}"

        if escaped_count == 1:
            escaped_text = f"1 {enemy_type_singular}"
        elif escaped_count > 1:
            escaped_text = f"{escaped_count} {enemy_type_plural}"
        else:
            escaped_text = None

        if escaped_text:
            victory_message = battle_descriptions['victory_messages']['partial_victory'].format(killed=total_killed)
        else:
            victory_message = battle_descriptions['victory_messages']['complete_victory']

        fight_log.append(victory_message)
        save_game_state(game_state)

        # Show victory outcome in mud fight template before redirect
        combat_active = False
        return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=enemy_count, combat_active=combat_active, combat_id=combat_id, fight_log=fight_log, victory=True)
    elif game_state.damage >= 10:
        game_state.lives -= 1
        final_damage = game_state.damage  # Store the final damage before resetting
        game_state.damage = 0
        game_state.health = 30
        if game_state.lives <= 0:
            fight_log.append(battle_descriptions['defeat_messages']['final_death'])
        else:
            fight_log.append(battle_descriptions['defeat_messages']['standard'])
            fight_log.append(battle_descriptions['defeat_messages']['damage_taken'].format(damage=final_damage))
        save_game_state(game_state)

        # Show defeat outcome in mud fight template
        combat_active = False
        return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=enemy_count, combat_active=combat_active, combat_id=combat_id, fight_log=fight_log, defeat=True)

    # Continue combat
    save_game_state(game_state)
    session['fight_log'] = fight_log
    session.modified = True
    combat_active = enemy_health > 0
    return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=enemy_count, combat_active=combat_active, combat_id=combat_id, fight_log=fight_log)

@app.route('/continue_after_fight', methods=['POST'])
def continue_after_fight():
    """Handle continue button after fight ends"""
    game_state = get_game_state()
    outcome = request.form.get('outcome')

    if outcome == 'victory':
        # Victory - return to city
        flash("Victory! You have successfully defeated your enemies!", "success")
        return redirect(url_for('city'))
    elif outcome == 'defeat':
        # Defeat - check if game over or continue
        if game_state.lives <= 0:
            # Game over
            return redirect(url_for('game_over'))
        else:
            # Continue with reduced lives
            flash(f"You were defeated but have {game_state.lives} lives remaining!", "warning")
            return redirect(url_for('city'))

    # Fallback
    return redirect(url_for('city'))

@app.route('/game_over')
def game_over():
    """Game Over screen"""
    game_state = get_game_state()
    return render_template('game_over.html', game_state=game_state)

# ============
# SocketIO Events
# ============

if socketio:
    @socketio.on('join')
    def handle_join(data):
        """Handle player joining a room"""
        room = data.get('room', 'global')
        location_room = data.get('location_room', 'city')
        player_name = data.get('player_name', 'Unknown Player')

        # Get the actual player name from game state if available
        game_state = get_game_state()
        if game_state and game_state['player_name'] and game_state['player_name'] != 'Player':
            player_name = game_state['player_name']

        join_room(room)
        join_room(location_room)

        # Store player info with proper name
        connected_players[request.sid] = {
            'id': request.sid,
            'name': player_name,
            'room': location_room,
            'in_fight': False,
            'joined_at': time.time()
        }

        emit('status', {'msg': f'{player_name} joined the chat'})
        update_player_lists()

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle player disconnecting"""
        if request.sid in connected_players:
            player_name = connected_players[request.sid]['name']
            del connected_players[request.sid]
            emit('status', {'msg': f'{player_name} left the chat'}, broadcast=True)
            update_player_lists()

    @socketio.on('chat_message')
    def handle_chat_message(data):
        """Handle chat messages"""
        room = data.get('room', 'global')
        player_name = data.get('player_name', 'Unknown Player')
        message = data.get('message', '')

        # Get the actual player name from game state if available
        game_state = get_game_state()
        if game_state and game_state['player_name'] and game_state['player_name'] != 'Player':
            player_name = game_state['player_name']

        if message.strip():
            emit('chat_message', {
                'player': player_name,
                'message': message,
                'room': room
            }, room=room)

    @socketio.on('get_player_list')
    def handle_get_player_list(data):
        """Send current player list to requesting client"""
        room = data.get('room', 'city')
        players_in_room = [
            player for player in connected_players.values()
            if player['room'] == room
        ]
        emit('player_list', {'players': players_in_room})

    @socketio.on('pvp_challenge')
    def handle_pvp_challenge(data):
        """Handle PVP challenge requests"""
        target_id = data.get('target_id')
        room = data.get('room', 'city')

        if target_id in connected_players:
            # For now, just send a notification
            emit('pvp_response', {
                'success': True,
                'message': 'PVP challenge sent!'
            })
            # In a real implementation, you'd handle the challenge logic here
        else:
            emit('pvp_response', {
                'success': False,
                'message': 'Player not found or unavailable.'
            })

    def update_player_lists():
        """Update player lists for all connected clients"""
        # Group players by room
        room_players = {}
        for player in connected_players.values():
            room = player['room']
            if room not in room_players:
                room_players[room] = []
            room_players[room].append(player)

        # Send updated lists to all clients in each room
        for room, players in room_players.items():
            socketio.emit('player_list', {'players': players}, room=room)
else:
    def update_player_lists():
        """Dummy function when SocketIO is disabled"""
        pass


if __name__ == '__main__':
    if socketio:
        socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
    else:
        app.run(debug=True)
