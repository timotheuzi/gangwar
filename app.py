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

@dataclass
class GameState:
    player_name: str = ""
    gang_name: str = ""
    money: int = 1000
    account: int = 0
    members: int = 5
    squidies: int = 25
    day: int = 1
    health: int = 100
    steps: int = 0
    max_steps: int = 100
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
    return render_template('city.html', game_state=game_state)

@app.route('/crackhouse')
def crackhouse():
    """Big Johnny's Crack House"""
    game_state = get_game_state()
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

    # Simple room structure for alleyway
    current_room = {
        'title': 'Dark Alley Entrance',
        'description': 'You stand at the entrance of a dark alleyway. The streetlights cast long shadows, and you can hear distant sounds echoing off the walls.',
        'exits': {
            'north': 'alleyway_north',
            'south': 'city',
            'east': 'alleyway_east',
            'west': 'alleyway_west'
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
    return render_template('final_battle.html', game_state=game_state)

@app.route('/wander')
def wander():
    """Wander the Streets"""
    game_state = get_game_state()
    return render_template('wander_result.html', game_state=game_state)

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
    # For now, just redirect back to alleyway
    # In a full implementation, this would handle room navigation
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
