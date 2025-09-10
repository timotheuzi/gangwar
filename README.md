# The Gang Wars Are Upon Us

Set in a dypstopian present, this is a gritty, text-based drug dealing and gang warfare simulation game built with Flask and SocketIO. Build your criminal empire, deal drugs, fight rival gangs, and survive the streets in this intense urban warfare experience.

## 🎮 Game Overview

You start as a small-time entrepreneur with $1000, 5 units of crack, and a pistol. Your goal is to build a massive gang empire, defeat the rival Squidies gang, and become the ultimate pimp king of the city.

### Key Features

- **Drug Empire**: Buy and sell various drugs (weed, crack, coke, ice, percs, pixie dust) with dynamic pricing
- **Gang Warfare**: Recruit members, purchase weapons, and engage in epic gang battles
- **Real-time Multiplayer**: Challenge other players to PVP fights using SocketIO
- **Dynamic World**: Random encounters, police chases, and unpredictable street events
- **Economic Simulation**: Banking, loans, and interest calculations
- **Multiple Locations**: Explore the city, crackhouse, gun shack, bank, bar, and dark alleyways
- **Day/Night Cycle**: Each day brings new prices, stronger enemies, and growing challenges

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- pip (Python package manager)

## 🎯 How to Play

### Getting Started

1. **Create a New Game**: Enter your player name, gang name, and choose your gender
2. **Explore the City**: Visit different locations to buy/sell drugs, purchase weapons, and meet contacts
3. **Build Your Empire**: Use profits from drug dealing to recruit gang members and buy better weapons
4. **Survive Encounters**: Random events include police chases, robberies, and rival gang encounters
5. **Challenge Rivals**: Once your gang is strong enough (10+ members), start the final gang war

### Core Mechanics

#### Drug Dealing
- Visit the **Crackhouse** to buy and sell drugs
- Prices fluctuate daily - buy low, sell high
- Different drugs have different profit margins and risks

#### Combat System
- **Weapons Available**: Pistol, Uzi, Grenade, Missile Launcher, Knife
- **Ammo Management**: Track bullets, grenades, and missiles
- **Win Probabilities**: Each weapon has different success rates based on your gang size

#### Economic Management
- **Bank**: Deposit money for 1% daily interest, take loans at 5% interest
- **Savings Account**: Safe storage with compound interest
- **Loans**: High-risk borrowing to fuel your expansion

#### Gang Building
- **Recruit Members**: Spend money at Pick n' Save and achieve greatness to grow your gang
- **Gang Power**: More members increase your combat effectiveness
- **Territory Control**: Larger gangs attract more followers automatically

### Locations

- **City**: Central hub with access to all locations
- **Crackhouse**: Buy/sell drugs and visit prostitutes (dangerous!)
- **Gun Shack**: Purchase weapons, ammo, and protective vests
- **Bank**: Manage your finances and take loans
- **Bar**: Meet contacts and gather intelligence
- **Pick n' Save**: Buy fake IDs, recruit members, purchase information
- **Alleyway**: Explore dark alleys for hidden opportunities

### Random Events

When wandering around the city, you might encounter:
- **Money Finds**: Discover cash on the ground
- **Drug Stashes**: Find random drug supplies
- **Robberies**: Get mugged by street criminals
- **Police Chases**: Evade law enforcement
- **Gang Fights**: Battle rival gang members
- **NPC Encounters**: Meet informants, dealers, and contacts
- **Weapon Drops**: Find abandoned firearms
- **Injuries**: Take damage from street violence

### Winning the Game

1. **Build Your Gang**: Recruit at least 10 members
2. **Arm Your Crew**: Purchase powerful weapons and ammo
3. **Gather Intelligence**: Use contacts and information to learn about the Squidies
4. **Final Battle**: Challenge the Squidies to a massive gang war
5. **Victory**: Defeat the Squidies and become the undisputed king of the streets!

## 🛠️ Technical Details

### Architecture

- **Backend**: Flask web framework with SocketIO for real-time features
- **Frontend**: HTML5, CSS3, vanilla JavaScript
- **Real-time Communication**: WebSocket connections for multiplayer features
- **Session Management**: Flask sessions for game state persistence
- **Template Engine**: Jinja2 for dynamic HTML generation

### File Structure

```
pimpin/
├── app.py                 # Main Flask application
├── run_app.py            # Wrapper script to run with correct PYTHONPATH
├── standalone_app.py      # Single-file version for easy deployment
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── npcs.json             # NPC data (if used)
├── templates/            # HTML templates
│   ├── index.html
│   ├── city.html
│   ├── crackhouse.html
│   └── ...
├── static/               # CSS and static assets
│   └── style.css
└── src/                  # Source code (if applicable)
    └── main.py
```

### Dependencies

- **Flask 2.3.3**: Web framework
- **flask-socketio 5.3.6**: Real-time communication
- **python-socketio 5.8.0**: SocketIO client library

### Game State Management

The game uses Python dataclasses to manage complex game state:
- Player stats (money, health, lives)
- Inventory (drugs, weapons, ammo)
- Gang information (members, name)
- World state (day, prices, enemy strength)
- Flags and achievements

### Multiplayer Features

- **Real-time Chat**: Communicate with other players in the same location
- **PVP Combat**: Challenge other players to turn-based fights
- **Room System**: Location-based player grouping
- **Live Updates**: Real-time game state synchronization

## 🎨 Customization

### Adding New Drugs

Edit the `DRUG_PRICE_RANGES` in `Config` class:

```python
DRUG_PRICE_RANGES = {
    'weed': (50, 270),
    'crack': (300, 4500),
    'new_drug': (min_price, max_price)
}
```

### Modifying Weapon Stats

Update the `WEAPON_PRICES` and weapon logic in the `GameLogic` class.

### Creating New Locations

1. Add route in Flask app
2. Create HTML template
3. Add location to city grid
4. Implement location-specific mechanics

## 🚨 Content Warning

This game contains mature themes including:
- Drug dealing and substance abuse
- Violence and gang warfare
- Criminal activities
- Sexual content (prostitute encounters)
- Strong language and gritty urban themes

**This game is intended for entertainment purposes only and does not condone or promote real-world criminal activities.**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run in debug mode
FLASK_DEBUG=true ./run_app.py
```

Or alternatively:
```bash
FLASK_DEBUG=true python3 run_app.py
```

## 📄 License

This project is licensed under the terms specified in the LICENSE file.

## 🙏 Acknowledgments

- Inspired by classic text-based adventure games
- Built with modern web technologies
- Community contributions welcome

## 🐛 Known Issues & Future Plans

### Current Limitations
- Mobile responsiveness could be improved
- Some browser compatibility issues with older versions
- Limited save/load functionality

### Planned Features
- More detailed NPC interactions
- Expanded weapon variety
- Additional locations and side quests
- Enhanced multiplayer features
- Mobile app version

---

**Remember**: In the streets, only the strong survive. Build your empire wisely, and may the best pimp win! 💰🔫🏙️

- Created and Maintained by timotheuzi@hotmail.com
- Public Address to Receive 
- LTC ltc1qcx3xsrpxqm7q7gpkxhxhtaeqgdqpmq0jdrw7vh
- SOL 4sAaizpXmFS4yedakv7mLN1Z2myGh2CWnes3YJBhF1Hb
- XLM GCVYEJ7GC7LZZ2EBZL5DXWCLTZPTXX7YEUXLS36YGE6BA37R5BHRI2XG
- BTC bc1qfv69rux98r7u3sr786j2qpsenmkskvkf58ynkk
- ETH 0xD1A6b95958dE597c2D9478A3b4212adF0789BF81