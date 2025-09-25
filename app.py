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
        npcs_data = json.load(f)
except FileNotFoundError:
    npcs_data = {}

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
    crack: int = 5
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
    ghost_guns: int = 0

    def can_fight_with_pistol(self):
        return self.pistols > 0 and self.bullets > 0

@dataclass
class GameState:
    player_name: str = ""
    gang_name: str = ""
    money: int = 1000
    account: int = 0
    loan: int = 0
    members: int = 1
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
    max_steps: int = 24
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

def update_current_score(game_state):
    """Update the current score based on achievements"""
    money_earned = game_state.money + game_state.account
    days_survived = game_state.day
    # For current score, we don't track gang wars/fights won in real-time,
    # so we'll base it on money and days survived for now
    game_state.current_score = calculate_score(money_earned, days_survived, 0, 0)

def save_game_state(game_state):
    """Save game state to session"""
    # Update current score before saving
    update_current_score(game_state)
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

    # Check for police chase (10% chance)
    if random.random() < 0.1:
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

            # Chance to recruit new member from big drug sales
            if revenue >= 5000:  # Big sale threshold
                if random.random() < 0.25:  # 25% chance for big sales
                    game_state.members += 1
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
        # Note: gender is collected but not currently used in game logic

        # Initialize starting weapons
        game_state.weapons.pistols = 1
        game_state.weapons.bullets = 10

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
        if escape_chance < 0.6:  # 60% chance to escape
            flash("You manage to escape the police chase!", "success")
            # Chance to recruit a impressed bystander
            if random.random() < 0.2:  # 20% chance
                game_state.members += 1
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
            if game_state.damage >= 10:
                game_state.lives -= 1
                final_damage = game_state.damage  # Store before resetting
                game_state.damage = 0
                game_state.health = 100
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
                if game_state.damage >= 10:
                    game_state.lives -= 1
                    final_damage = game_state.damage  # Store before resetting
                    game_state.damage = 0
                    game_state.health = 100
                    enemy_type = f"{num_cops} Police Officers"
                    enemy_count = num_cops
                    fight_log = [message]
                    if game_state.lives <= 0:
                        save_game_state(game_state)
                        return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, fight_log=fight_log, final_damage=final_damage)
                    else:
                        save_game_state(game_state)
                        return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, fight_log=fight_log, final_damage=final_damage)

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
        if game_state.damage >= 10:
            game_state.lives -= 1
            final_damage = game_state.damage  # Store before resetting
            game_state.damage = 0
            game_state.health = 100
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
    drug = request.args.get('drug')

    # Get combat state from session (simplified - in real implementation you'd store full combat state)
    enemy_health = int(request.form.get('enemy_health', 30))
    enemy_type = request.form.get('enemy_type', 'Enemy')
    enemy_count = int(request.form.get('enemy_count', 1))
    fight_log = request.form.getlist('fight_log') or ["Combat begins!"]

    # Process action
    if action == 'attack':
        if weapon == 'pistol' and game_state.weapons.pistols > 0 and game_state.weapons.bullets > 0:
            game_state.weapons.bullets -= 1
            damage = random.randint(15, 25)
            enemy_health -= damage
            fight_log.append(f"You fire your pistol and deal {damage} damage!")
        elif weapon == 'ghost_gun' and game_state.weapons.ghost_guns > 0 and game_state.weapons.bullets > 0:
            game_state.weapons.bullets -= 1
            damage = random.randint(15, 25)
            enemy_health -= damage
            fight_log.append(f"You fire your ghost gun and deal {damage} damage!")
        elif weapon == 'uzi' and game_state.weapons.uzis > 0 and game_state.weapons.bullets >= 3:
            game_state.weapons.bullets -= 3
            damage = random.randint(20, 40)
            enemy_health -= damage
            fight_log.append(f"You spray with your Uzi and deal {damage} damage!")
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
            damage = random.randint(25, 45)
            enemy_health -= damage
            fight_log.append(f"You swing your vampire bat and deal {damage} damage!")
        elif weapon == 'knife':
            damage = random.randint(10, 20)
            enemy_health -= damage
            fight_log.append(f"You stab with your knife and deal {damage} damage!")
        else:
            fight_log.append("You don't have that weapon or ammo!")

        # Enemy attacks back
        if enemy_health > 0:
            enemy_damage = random.randint(5, 15) * enemy_count
            if game_state.weapons.vest > 0 and random.random() < 0.5:
                game_state.weapons.vest -= 1
                enemy_damage = max(0, enemy_damage - 20)
                fight_log.append(f"Enemy attacks! Your vest absorbs some damage, you take {enemy_damage} damage!")
            else:
                fight_log.append(f"Enemy attacks! You take {enemy_damage} damage!")
            game_state.damage += enemy_damage

    elif action == 'defend':
        fight_log.append("You take a defensive stance, reducing incoming damage!")
        # Reduced enemy damage
        if enemy_health > 0:
            enemy_damage = random.randint(2, 10) * enemy_count
            fight_log.append(f"Enemy attacks! You take {enemy_damage} damage (reduced by defense)!")
            game_state.damage += enemy_damage

    elif action == 'flee':
        if random.random() < 0.4:  # 40% chance to flee
            flash("You successfully flee from combat!", "success")
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
        flash("Victory! You defeated your enemies!", "success")

        # Handle NPC-specific victory logic
        npc_id = request.form.get('npc_id')
        if npc_id and npc_id in npcs_data:
            npcs_data[npc_id]['is_alive'] = False
            with open('npcs.json', 'w') as f:
                json.dump(npcs_data, f, indent=2)
            game_state.money += 100  # Loot from defeated NPC
            flash(f"You defeated {npcs_data[npc_id]['name']} and looted $100!", "success")

        # Chance to recruit a defeated enemy as a gang member
        if enemy_type != "Police Officers" and random.random() < 0.3:  # 30% chance
            game_state.members += 1
            flash("One of your defeated enemies has joined your gang!", "success")

        save_game_state(game_state)
        return redirect(url_for('city'))
    elif game_state.damage >= 10:
        game_state.lives -= 1
        final_damage = game_state.damage  # Store the final damage before resetting
        game_state.damage = 0
        game_state.health = 100
        if game_state.lives <= 0:
            save_game_state(game_state)
            return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, fight_log=fight_log, final_damage=final_damage)
        else:
            save_game_state(game_state)
            return render_template('fight_defeat.html', game_state=game_state, enemy_type=enemy_type, enemy_count=enemy_count, fight_log=fight_log, final_damage=final_damage)

    # Continue combat
    save_game_state(game_state)
    combat_active = enemy_health > 0
    return render_template('mud_fight.html', game_state=game_state, enemy_health=enemy_health, enemy_type=enemy_type, enemy_count=enemy_count, combat_active=combat_active, fight_log=fight_log, combat_id=combat_id)

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
