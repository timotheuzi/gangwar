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
    with open('npcs.json', 'r') as f:
        npcs = json.load(f)
except FileNotFoundError:
    npcs = {}

# ============
# High Scores
# ============

HIGH_SCORES_FILE = 'high_scores.json'

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
    except Exception as e:
        print(f"Error loading high scores: {e}")
    return []

def save_high_scores(scores: List[HighScore]):
    """Save high scores to file"""
    try:
        data = [asdict(score) for score in scores]
        with open(HIGH_SCORES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
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

@dataclass
class Flags:
    has_id: bool = False
    has_info: bool = False

@dataclass
class Drugs:
    weed: int = 0
    crack: int = 0
    coke: int = 0
    ice: int = 0
    percs: int = 0
    pixie_dust: int = 0

@dataclass
class Weapons:
    pistols: int = 0
    bullets: int = 0
    uzis: int = 0
    grenades: int = 0
    vampire_bat: int = 0
    missile_launcher: int = 0
    missiles: int = 0
    vest: int = 0
    knife: int = 0

    def can_fight_with_pistol(self):
        return self.pistols > 0 and self.bullets > 0

@dataclass
class GameState:
    player_name: str = ""
    gang_name: str = ""
    money: int = 1000
    account: int = 0
    loan: int = 0
    members: int = 5
    squidies: int = 25
    squidies_pistols: int = 10
    squidies_uzis: int = 5
    squidies_bullets: int = 100
    squidies_grenades: int = 20
    squidies_missile_launcher: int = 2
    squidies_missiles: int = 10
    day: int = 1
    health: int = 100
    steps: int = 0
    max_steps: int = 100
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
    return GameState(**game_dict)

def save_game_state(game_state):
    """Save game state to session"""
    session['game_state'] = asdict(game_state)
    session.modified = True

# def check_and_update_high_scores(game_state: GameState, gang_wars_won: int = 0, fights_won: int = 0):
#     """Check if current game qualifies for high score and update if necessary"""
#     if not game_state.player_name or not game_state.gang_name:
#         return

#     # Calculate current achievements
#     money_earned = game_state.money + game_state.account  # Include savings
#     days_survived = game_state.day

#     # Calculate score
#     score = calculate_score(money_earned, days_survived, gang_wars_won, fights_won)

#     # Load existing high scores
#     high_scores = load_high_scores()

#     # Create new high score entry
#     new_score = HighScore(
#         player_name=game_state.player_name,
#         gang_name=game_state.gang_name,
#         score=score,
#         money_earned=money_earned,
#         days_survived=days_survived,
#         gang_wars_won=gang_wars_won,
#         fights_won=fights_won,
#         date_achieved=time.strftime("%Y-%m-%d %H:%M:%S")
#     )

#     # Add to list and sort by score (highest first)
#     high_scores.append(new_score)
#     high_scores.sort(key=lambda x: x.score, reverse=True)

#     # Keep only top 10 scores
#     high_scores = high_scores[:10]

#     # Save updated high scores
#     save_high_scores(high_scores)


# ============
# Flask App
# ============

app = Flask(__name__)
app.secret_key = 'gangwar_secret_key_2024'

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
    game_state.current_location = "city"
    save_game_state(game_state)
    return render_template('city.html', game_state=game_state)

@app.route('/crackhouse')
def crackhouse():
    """Big Johnny's Crack House"""
    game_state = get_game_state()
    game_state.current_location = "crackhouse"
    save_game_state(game_state)
    return render_template('crackhouse.html', game_state=game_state)

@app.route('/gunshack')
def gunshack():
    """Little Johnny's Gun Shack"""
    game_state = get_game_state()
    return render_template('gunshack.html', game_state=game_state)

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
                'north': 'hidden_entrance'
            }
        },
        'dumpster': {
            'title': 'Behind the Dumpster',
            'description': 'You hide behind a large dumpster. The smell is awful, but you\'re well concealed. You find some discarded items.',
            'exits': {
                'east': 'entrance'
            }
        },
        'hidden_entrance': {
            'title': 'Hidden Entrance',
            'description': 'You find a hidden entrance to an underground network. This could lead to interesting places...',
            'exits': {
                'south': 'side_street',
                'down': 'underground'
            }
        },
        'underground': {
            'title': 'Underground Passage',
            'description': 'You descend into a dimly lit underground passage. Water drips from the ceiling, and you hear echoes of distant footsteps.',
            'exits': {
                'up': 'hidden_entrance',
                'north': 'secret_room'
            }
        },
        'secret_room': {
            'title': 'Secret Room',
            'description': 'You enter a secret room filled with old crates and mysterious artifacts. There might be valuable items here.',
            'exits': {
                'south': 'underground'
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
    return render_template('final_battle.html', game_state=game_state)

@app.route('/wander')
def wander():
    """Wander the Streets"""
    game_state = get_game_state()

    # Check for police chase (10% chance)
    if random.random() < 0.1:
        if game_state.flags.has_id:
            result = "You see a police patrol but your fake ID saves you from getting stopped!"
            flash("Your fake ID protected you from police harassment!", "success")
        else:
            # Police chase sequence
            save_game_state(game_state)
            return render_template('cop_chase.html', game_state=game_state)

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
        result = f"You encounter {enemy_members} rival gang members looking for trouble!"

        # Calculate combat odds
        player_power = game_state.members + (game_state.weapons.pistols * 2) + (game_state.weapons.uzis * 3)
        enemy_power = enemy_members

        if player_power > enemy_power:
            # Victory
            killed = min(enemy_members, random.randint(1, enemy_members))
            game_state.squidies = max(0, game_state.squidies - killed)
            money_gained = killed * 50
            game_state.money += money_gained
            result += f" You and your gang win the fight! You kill {killed} of them and take ${money_gained}."
            flash(f"Gang fight victory! Killed {killed} enemies!", "success")
        elif player_power >= enemy_power * 0.8:
            # Stalemate with casualties
            player_casualties = random.randint(0, min(2, game_state.members - 1))
            enemy_casualties = random.randint(1, enemy_members)
            game_state.members = max(1, game_state.members - player_casualties)
            game_state.squidies = max(0, game_state.squidies - enemy_casualties)
            if player_casualties > 0:
                result += f" The fight is brutal! You lose {player_casualties} gang member(s) but kill {enemy_casualties} of them."
            else:
                result += f" You manage to fight them off without losing anyone, killing {enemy_casualties} enemies!"
        else:
            # Defeat
            player_casualties = random.randint(1, min(3, game_state.members))
            game_state.members = max(1, game_state.members - player_casualties)
            money_lost = random.randint(100, 500)
            game_state.money = max(0, game_state.money - money_lost)
            game_state.health = max(0, game_state.health - 20)
            result += f" You get beaten badly! You lose {player_casualties} gang member(s) and ${money_lost}."
            flash(f"Gang fight defeat! Lost {player_casualties} members!", "danger")

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
            game_state.money += 50
        elif "discarded drugs worth $200" in result:
            game_state.money += 200
        elif "find a quiet spot" in result:
            game_state.health = min(100, game_state.health + 10)
        elif "hidden stash of weapons" in result:
            game_state.weapons.bullets += 5
        elif "without incident" not in result and "trouble" not in result and "police" not in result:
            # Minor health damage for risky wanders
            if random.random() < 0.3:
                game_state.health = max(0, game_state.health - 5)

    # Increment steps
    game_state.steps += 1

    # Check if day ends
    if game_state.steps >= game_state.max_steps:
        game_state.day += 1
        game_state.steps = 0
        # Reset some daily things if needed

    # Check for NPC encounter (15% chance, down from 30% since we have more events now)
    if random.random() < 0.15 and npcs:
        wander_npcs = [npc for npc in npcs.values() if npc['location'] == 'wander']
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
            game_state.health = min(100, game_state.health + 50)  # Heal up to 100
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
        else:
            flash(f"You don't have enough {drug_type} to sell!", "danger")

    save_game_state(game_state)
    return redirect(url_for('crackhouse'))

@app.route('/visit_prostitutes')
def visit_prostitutes():
    """Visit Prostitutes"""
    game_state = get_game_state()
    return render_template('prostitutes.html', game_state=game_state)

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
                'north': 'hidden_entrance'
            }
        },
        'dumpster': {
            'title': 'Behind the Dumpster',
            'description': 'You hide behind a large dumpster. The smell is awful, but you\'re well concealed. You find some discarded items.',
            'exits': {
                'east': 'entrance'
            }
        },
        'hidden_entrance': {
            'title': 'Hidden Entrance',
            'description': 'You find a hidden entrance to an underground network. This could lead to interesting places...',
            'exits': {
                'south': 'side_street',
                'down': 'underground'
            }
        },
        'underground': {
            'title': 'Underground Passage',
            'description': 'You descend into a dimly lit underground passage. Water drips from the ceiling, and you hear echoes of distant footsteps.',
            'exits': {
                'up': 'hidden_entrance',
                'north': 'secret_room'
            }
        },
        'secret_room': {
            'title': 'Secret Room',
            'description': 'You enter a secret room filled with old crates and mysterious artifacts. There might be valuable items here.',
            'exits': {
                'south': 'underground'
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
    if random.random() < 0.2 and npcs:
        alley_npcs = [npc for npc in npcs.values() if npc['location'] == 'alleyway']
        if alley_npcs:
            npc = random.choice(alley_npcs)
            return render_template('npc_interaction.html', npc=npc, action='encounter', message=f"You encounter {npc['name']}. {npc['description']}", game_state=game_state)

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
        # Note: gender is collected but not currently used in game logic

        # Initialize starting weapons
        game_state.weapons.pistols = 1
        game_state.weapons.bullets = 10

        save_game_state(game_state)
        return redirect(url_for('city'))

    return render_template('new_game.html')

@app.route('/npc_interaction/<npc_id>')
def npc_interaction(npc_id):
    if npc_id not in npcs:
        return redirect(url_for('city'))
    npc = npcs[npc_id]
    game_state = get_game_state()
    return render_template('npc_interaction.html', npc=npc, action='encounter', message=f"You encounter {npc['name']}. {npc['description']}", game_state=game_state)

@app.route('/talk_to_npc/<npc_id>')
def talk_to_npc(npc_id):
    if npc_id not in npcs:
        return redirect(url_for('city'))
    npc = npcs[npc_id]
    game_state = get_game_state()
    message = f"{npc['name']} says: Hello, {game_state.player_name}. What can I do for you?"
    return render_template('npc_interaction.html', npc=npc, action='talk', message=message, game_state=game_state)

@app.route('/trade_with_npc/<npc_id>')
def trade_with_npc(npc_id):
    if npc_id not in npcs:
        return redirect(url_for('city'))
    npc = npcs[npc_id]
    game_state = get_game_state()
    message = f"{npc['name']} offers to trade with you."
    return render_template('npc_interaction.html', npc=npc, action='trade', message=message, game_state=game_state)

@app.route('/fight_npc/<npc_id>', methods=['POST'])
def fight_npc(npc_id):
    if npc_id not in npcs:
        return redirect(url_for('city'))
    npc = npcs[npc_id]
    game_state = get_game_state()
    weapon = request.form.get('weapon', 'pistol')
    if weapon == 'pistol' and game_state.weapons.bullets > 0:
        game_state.weapons.bullets -= 1
        npc['hp'] -= 20
        if npc['hp'] <= 0:
            npc['is_alive'] = False
            message = f"You defeated {npc['name']} with your pistol!"
        else:
            message = f"You shot {npc['name']}, but they are still alive. HP: {npc['hp']}"
    else:
        message = "You don't have the weapon or ammo to fight."
    with open('npcs.json', 'w') as f:
        json.dump(npcs, f, indent=2)
    save_game_state(game_state)
    return render_template('npc_interaction.html', npc=npc, action='fight', message=message, game_state=game_state)

@app.route('/pickup_loot/<npc_id>')
def pickup_loot(npc_id):
    if npc_id not in npcs:
        return redirect(url_for('city'))
    npc = npcs[npc_id]
    game_state = get_game_state()
    if not npc['is_alive']:
        game_state.money += 100
        message = f"You search {npc['name']}'s body and find $100!"
    else:
        message = "You can't loot a living person."
    save_game_state(game_state)
    return render_template('npc_interaction.html', npc=npc, action='loot', message=message, game_state=game_state)

@app.route('/cop_chase')
def cop_chase():
    """Police chase encounter"""
    game_state = get_game_state()
    num_cops = random.randint(2, 6)
    message = f"Oh no! {num_cops} police officers spot you and give chase!"
    return render_template('cop_chase.html', game_state=game_state, num_cops=num_cops, message=message)

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
            if game_state.damage >= 10:
                game_state.lives -= 1
                game_state.damage = 0
                game_state.health = 100
                if game_state.lives <= 0:
                    flash("You died and ran out of lives! Game Over!", "danger")
                    return redirect(url_for('game_over'))
                else:
                    flash(f"You died but have {game_state.lives} lives remaining!", "warning")
                    save_game_state(game_state)
                    return redirect(url_for('city'))

            return render_template('cop_chase.html', game_state=game_state, num_cops=num_cops, message=message)

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
                if game_state.damage >= 10:
                    game_state.lives -= 1
                    game_state.damage = 0
                    game_state.health = 100
                    if game_state.lives <= 0:
                        flash("You died in the shootout! Game Over!", "danger")
                        return redirect(url_for('game_over'))
                    else:
                        flash(f"You died in the shootout but have {game_state.lives} lives remaining!", "warning")
                        save_game_state(game_state)
                        return redirect(url_for('city'))

        elif weapon == 'uzi' and game_state.weapons.bullets > 0:
            game_state.weapons.bullets -= min(10, game_state.weapons.bullets)  # Uzi uses 10 bullets
            cops_killed = min(num_cops, random.randint(2, 5))
            num_cops -= cops_killed

            damage = random.randint(10, 40) * (num_cops if num_cops > 0 else 1)
            if game_state.weapons.vest > 0:
                game_state.weapons.vest -= 1
                damage = max(0, damage - 20)

            game_state.damage += damage

            if num_cops <= 0:
                flash(f"You sprayed the cops with your Uzi! {cops_killed} officers down!", "success")
                save_game_state(game_state)
                return redirect(url_for('city'))
            else:
                message = f"You sprayed {cops_killed} cop(s) but {num_cops} remain! Massive shootout - you took {damage} damage."

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

        elif weapon == 'vampire_bat':
            damage_to_player = random.randint(20, 45) * num_cops
            if game_state.weapons.vest > 0:
                game_state.weapons.vest -= 1
                damage_to_player = max(0, damage_to_player - 20)
            game_state.damage += damage_to_player
            message = f"The vampire bat didn't help much! {damage_to_player} damage from {num_cops} cops shooting back."

        # Check if player died
        if game_state.damage >= 10:
            game_state.lives -= 1
            game_state.damage = 0
            game_state.health = 100
            if game_state.lives <= 0:
                flash("You died in the police shootout! Game Over!", "danger")
                return redirect(url_for('game_over'))
            else:
                flash(f"You died but have {game_state.lives} lives remaining!", "warning")
                save_game_state(game_state)
                return redirect(url_for('city'))

        return render_template('cop_chase.html', game_state=game_state, num_cops=num_cops, message=message)

    save_game_state(game_state)
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

        join_room(room)
        join_room(location_room)

        # Store player info
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
        socketio.run(app, debug=True)
    else:
        app.run(debug=True)
