# Gang War: Blood in the Streets #

## Game Overview

Gang War is a brutal text-based role-playing game set in a dystopian urban wasteland where you build and command a criminal empire through drug trafficking, violent gang warfare, and ruthless street survival. As a rising gang leader, you'll navigate treacherous streets filled with rival gangs, corrupt police, and deadly encounters.

Start with nothing but a pistol and $1000, then expand your criminal operations by dealing drugs, recruiting violent thugs, and eliminating competition through bloody combat. The city streets run red with blood as you fight for dominance.

## How to Play

### Getting Started
1. Launch the game and create a new character
2. Choose your player name and gang name
3. Begin in the city with $1000, a pistol, 10 bullets, and basic equipment

### Core Gameplay Loop
- **Explore Locations**: Move between different areas of the city
- **Deal Drugs**: Buy low, sell high, and expand your criminal network
- **Recruit Members**: Grow your gang through successful operations and intimidation
- **Combat**: Fight rival gangs, police, and other threats in turn-based battles
- **Manage Resources**: Balance money, weapons, health, and gang morale
- **Wander Streets**: Encounter random events, police chases, and opportunities

### Locations
- **City Hub**: Central navigation point with daily drug price alerts
- **Crackhouse**: Buy/sell drugs and engage in risky encounters
- **Gun Shack**: Purchase weapons, ammunition, and upgrades
- **Bank**: Deposit money for interest or manage savings
- **Bar**: Gather information and meet shady contacts
- **Alleyway**: Explore dark alleys with multiple interconnected rooms for hidden opportunities and dangers
- **Pick n' Save**: Buy supplies, fake IDs, information, and recruit new members
- **Prostitutes**: Get services, reduce stress, and recruit new gang members

### Combat System
Fight using various weapons in turn-based MUD-style combat with detailed battle descriptions:
- **Pistols and Bullets**: Basic firearms with automatic upgrade options
- **AR-15**: Assault rifle for high damage
- **Ghost Guns**: Untraceable weapons with jamming risk
- **Grenades**: Area damage explosives
- **Missile Launchers**: Massive destructive power
- **Vampire Bats**: Melee weapon with multi-strike capability
- **Knives**: Fast multi-stab attacks
- **Special Weapons**: Sword, axe, golden gun, poison blowgun (dropped by NPCs)
- **Special Ammunition**: Exploding bullets and hollow point bullets for enhanced damage
- **Body Armor**: Various vests for damage reduction
- **Gang Members**: Your recruited members fight alongside you
- **Drug Usage**: Use drugs during combat for various effects

Enemies include police, rival gang members, NPCs, and the deadly Squidies gang. Combat features collateral damage where gang members can die, and detailed grim descriptions of violence.

### Winning the Game
Build your gang to 10+ members, gather intelligence, and launch a final assault on the Squidies' headquarters. Survive long enough to become the ultimate gang lord of the city.

### Losing the Game
Die in combat, get arrested, or run out of lives. The streets are unforgiving.

## Technical Requirements
- Python 3.8+
- Flask web framework
- Flask-SocketIO for real-time chat features
- Modern web browser with JavaScript enabled

## Installation & Running

### Local Development
1. Install dependencies: `pip install -r requirements.txt`
2. Run the game using one of these options:
   - **Standard Flask**: `python src/app.py --port 6009`
   - **PythonAnywhere deployment**: `python pythonanywhere_entry.py`
3. Open your browser to `http://localhost:6009`

### PythonAnywhere Deployment
1. Upload files to PythonAnywhere
2. Set up virtual environment and install requirements
3. Configure WSGI file to point to `pythonanywhere_entry.py`
4. The app will run on the PythonAnywhere domain

### Chat System
The real-time chat system requires:
- Flask-SocketIO installed (`pip install flask-socketio`)
- Browser must allow WebSocket connections
- SocketIO client library is loaded from CDN (cdnjs.cloudflare.com)

If chat doesn't connect, check:
1. Browser console for connection errors (F12)
2. Server console for "SocketIO initialized" message
3. Ensure port 6009 is accessible

## Features
- **Dynamic Economy**: Fluctuating drug prices with daily market alerts and busts/flooded markets
- **Real-time Multiplayer Chat**: Global chat system with player lists and location-based rooms
- **PVP Framework**: Player vs player challenge system
- **High Score Tracking**: Persistent leaderboard with money earned, days survived, and achievements
- **Extensive Combat System**: Multiple weapons, special ammo, body armor, and tactical combat
- **NPC Interactions**: Talk to, trade with, and fight non-player characters with unique loot drops
- **Alleyway Exploration**: Multi-room dungeon-like exploration with hidden treasures and traps
- **Gang Management**: Recruit and manage gang members who participate in combat
- **Banking System**: Deposit money for interest and manage savings accounts
- **Fake ID System**: Protection from police encounters and enhanced street operations
- **Information Gathering**: Intelligence system for police awareness and strategic advantages
- **Drug Usage in Combat**: Various drugs provide different combat effects
- **Day/Night Cycle**: Time progression with step limits and daily price fluctuations
- **Random Encounters**: Police chases, baby momma incidents, gang fights, and Squidie hit squads
- **Collateral Damage**: Realistic combat where gang members can die in battle

## Content Warning
This game contains extreme violence, gore, drug use, criminal activity, and mature themes. All depictions are fictional and for entertainment purposes only.

---

*Built with Flask and Flask-SocketIO. All rights reserved.*
