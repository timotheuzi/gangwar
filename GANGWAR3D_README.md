# Gang War 3D

A complete 3D graphical remake of the classic text-based gang warfare and drug dealing simulation game, built with Panda3D and inspired by Stardew Valley gameplay mechanics in a dystopian urban setting.

## 🎮 Game Overview

Gang War 3D transforms the original Flask/SocketIO web-based game into a fully 3D experience. Navigate through a gritty cyberpunk city, build your criminal empire, deal drugs, wage gang wars, and become the ultimate pimp king - all in stunning 3D graphics.

### Key Features

- **3D City Exploration**: Navigate through a fully 3D urban environment with distinct locations
- **Drug Empire**: Buy and sell various drugs with dynamic pricing in a 3D marketplace
- **Gang Warfare**: Recruit members and engage in epic battles (combat system in development)
- **Real-time Multiplayer**: Framework for real-time features (SocketIO integration planned)
- **Dynamic World**: Random encounters, police chases, and unpredictable street events
- **Economic Simulation**: Banking, loans, and interest calculations with 3D interfaces
- **Multiple Locations**: Explore the city, crackhouse, gun shack, bank, bar, and dark alleyways as individual 3D levels
- **Day/Night Cycle**: Each day brings new prices, stronger enemies, and growing challenges
- **Stardew Valley Inspired**: Relaxed exploration gameplay with RPG elements in a dystopian setting

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- Panda3D 1.10+

### Installation

```bash
pip install panda3d
```

### Running the Game

```bash
python gangwar3d.py
```

## 🎯 How to Play

### Getting Started

1. **Launch the Game**: Run `python gangwar3d.py`
2. **Navigate**: Use WASD keys to move your character (blue cube) around the 3D world
3. **Explore**: Walk into colored building cubes to enter different locations
4. **Interact**: Press 'E' to interact with objects and NPCs
5. **View Stats**: Press 'TAB' to toggle the HUD showing your stats

### Core Mechanics

#### Movement & Exploration
- **WASD**: Move forward/backward/left/right
- **TAB**: Toggle heads-up display
- **ESC**: Quit game
- **E**: Interact with objects
- **I**: Inventory (planned)

#### Drug Dealing
- Visit the **Crackhouse** (red building) to access the drug market
- Press 'E' near the counter to open the trading interface
- View current prices and your inventory
- Buy/sell drugs to build your fortune

#### Locations (Levels)
Each location from the original game is now a separate 3D level:

- **City**: Central hub with access to all buildings
- **Crackhouse**: Drug trading marketplace
- **Gun Shack**: Weapon and ammo purchases (green building)
- **Bank**: Financial management (blue building)
- **Bar**: Meet contacts and gather intelligence (yellow building)
- **Pick n' Save**: Fake IDs, recruitment, information (gray building)
- **Alleyway**: Hidden opportunities and dangers (dark level)

#### Economic Management
- **Bank**: Deposit money for interest (planned)
- **Savings Account**: Safe storage with compound interest
- **Loans**: High-risk borrowing to fuel expansion

#### Gang Building
- **Recruit Members**: Spend money at Pick n' Save to grow your gang
- **Gang Power**: More members increase your combat effectiveness
- **Territory Control**: Larger gangs attract more followers automatically

### Winning the Game

1. **Build Your Gang**: Recruit at least 10 members
2. **Arm Your Crew**: Purchase powerful weapons and ammo (planned)
3. **Gather Intelligence**: Use contacts and information to learn about rivals
4. **Final Battle**: Challenge rival gangs to massive warfare (planned)
5. **Victory**: Defeat all rivals and become the undisputed king!

## 🛠️ Technical Details

### Architecture

- **Engine**: Panda3D 3D game engine
- **Language**: Python 3.7+
- **Graphics**: OpenGL via Panda3D
- **UI**: DirectGUI for 2D interfaces
- **State Management**: Python dataclasses for game state persistence

### File Structure

```
gangwar3d.py          # Main game application
npcs.json            # NPC data (inherited from original)
GANGWAR3D_README.md  # This documentation
```

### Game State Management

The game uses Python dataclasses to manage complex game state:
- Player stats (money, health, lives)
- Inventory (drugs, weapons, ammo)
- Gang information (members, name)
- World state (day, prices, enemy strength)
- Flags and achievements

### 3D Level Design

Each location is procedurally generated with:
- Ground planes with thematic coloring
- Simple geometric buildings/objects
- Interactive elements (counters, buttons)
- Navigation between levels via position-based triggers

### Planned Features

- **Combat System**: Real-time 3D battles with weapons
- **NPC Models**: 3D character models instead of simple cubes
- **Advanced UI**: Full inventory management, character customization
- **Audio**: Sound effects and background music
- **Multiplayer**: Real-time PVP and chat features
- **Save/Load**: Persistent game state across sessions

## 🎨 Art Style

- **Cyberpunk/Dystopian**: Dark urban environment with neon accents
- **Stardew Valley Inspired**: Relaxed exploration with RPG progression
- **Minimalist 3D**: Clean geometric shapes with vibrant colors
- **Atmospheric Lighting**: Dynamic lighting for day/night cycle

## 🤝 Development Status

### Current Features ✅
- Basic 3D movement and camera system
- Multiple level loading and transitions
- Drug trading UI in crackhouse
- HUD with player stats
- Day/night cycle with price fluctuations
- Core game state management

### In Development 🚧
- Combat system
- Weapon purchasing
- NPC interactions
- Banking system
- Inventory management

### Planned Features 📋
- 3D models and animations
- Audio system
- Multiplayer features
- Save/load functionality
- Advanced UI systems

## 🐛 Known Issues

- Simple cube-based graphics (placeholder for 3D models)
- Limited UI interactions
- No combat system yet
- No save/load functionality

## 🚨 Content Warning

This game contains mature themes including:
- Drug dealing and substance abuse
- Violence and gang warfare
- Criminal activities
- Sexual content (planned features)
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
# Install dependencies
pip install panda3d

# Run in development mode
python gangwar3d.py
```

## 📄 License

This project is licensed under the terms specified in the LICENSE file.

## 🙏 Acknowledgments

- **Original Gang War Game**: Flask/SocketIO version by timotheuzi@hotmail.com
- **Panda3D**: Excellent free 3D game engine
- **Stardew Valley**: Inspiration for exploration and progression mechanics
- **Cyberpunk Genre**: For the dystopian urban setting

---

**Remember**: In the streets of the 3D city, only the strong survive. Build your empire wisely, and may the best pimp win! 💰🔫🏙️🎮
