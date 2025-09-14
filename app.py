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

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
from flask_socketio import SocketIO, emit, join_room, leave_room


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
socketio = SocketIO(app, async_mode='asyncio')

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

# ============
# SocketIO Events
# ============

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


if __name__ == '__main__':
    socketio.run(app, debug=True)
