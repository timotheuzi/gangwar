import os
import random
import secrets
import sys
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple

# Force threading mode for Flask-SocketIO to avoid eventlet/gevent issues with Python 3.13
os.environ.setdefault('ENGINEIO_FORCE_THREADING', '1')

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
from flask_socketio import SocketIO, emit, join_room, leave_room


# =========================
# Configuration & Constants
# =========================

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    # Check if running in PyInstaller bundle
    IS_BUNDLED = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

    # Allow forcing SocketIO on/off via environment variable
    FORCE_SOCKETIO = os.environ.get('FORCE_SOCKETIO', '').lower() in ('true', '1', 'yes', 'on')

    # Game constants
    MAX_STEPS_PER_DAY = 35
    INITIAL_MONEY = 1000
    INITIAL_LIVES = 5
    DAMAGE_THRESHOLD = 10

    # Price ranges
    DRUG_PRICE_RANGES = {
        'weed': (50, 370),
        'crack': (300, 4500),
        'coke': (8000, 17000),
        'ice': (2000, 7000),
        'percs': (10000, 30000),
        'pixie_dust': (50000, 170000)
    }

    # Weapon prices
    WEAPON_PRICES = {
        'pistol': 1200,
        'bullets': 100,  # 50-pack
        'uzi': 10000,
        'grenade': 1000,
        'missile_launcher': 100000,
        'missile': 1000,
        'vest_light': 3000,
        'vest_medium': 5500,
        'vest_heavy': 7500,
        'vampire_bat': 2500
    }


# ============
# Dataclasses
# ============

@dataclass
class DrugInventory:
    weed: int = 0
    crack: int = 5
    coke: int = 0
    ice: int = 0
    percs: int = 0
    pixie_dust: int = 0

    def has_any_drugs(self) -> bool:
        return any(getattr(self, drug) > 0 for drug in ['weed', 'crack', 'coke', 'ice', 'percs', 'pixie_dust'])

    def get_drug_amount(self, drug_type: str) -> int:
        return getattr(self, drug_type, 0)

    def modify_drug(self, drug_type: str, amount: int) -> bool:
        if hasattr(self, drug_type):
            current = getattr(self, drug_type)
            if current + amount >= 0:
                setattr(self, drug_type, current + amount)
                return True
        return False


@dataclass
class WeaponInventory:
    pistols: int = 1
    uzis: int = 0
    bullets: int = 10
    grenades: int = 0
    missiles: int = 0
    missile_launcher: int = 0
    vest: int = 0
    knife: int = 1
    vampire_bat: int = 0

    def has_weapons(self) -> bool:
        return self.pistols > 0 or self.uzis > 0 or self.knife > 0

    def can_fight(self) -> bool:
        return self.has_weapons() and (self.bullets > 0 or self.knife > 0)

    def can_fight_with_pistol(self) -> bool:
        return self.pistols > 0 and self.bullets > 0

    def can_fight_with_knife(self) -> bool:
        return self.knife > 0


@dataclass
class GameFlags:
    eric_met: bool = False
    steve_met: bool = False
    has_id: bool = False
    free_pistol: bool = False
    free_crack: bool = False

@dataclass
class Prostitute:
    name: str
    price: int
    description: str
    risk_level: str  # "low", "medium", "high"
    healing_amount: int
    death_risk: float  # Percentage chance of death
    death_method: str  # "aids", "gun", "knife"

@dataclass
class PotentialHooker:
    name: str
    description: str
    recruitment_cost_drugs: Dict[str, int]  # Drugs needed to recruit
    recruitment_cost_money: int  # Money needed to recruit
    stats: Dict[str, any]  # price, risk_level, healing_amount, death_risk, death_method


@dataclass
class Room:
    id: str
    title: str
    description: str
    exits: Dict[str, str] = field(default_factory=dict)
    has_encounter: bool = False
    encounter_chance: int = 0  # Percentage chance of encounter
    has_baby_momma: bool = False
    baby_momma_chance: int = 0  # Percentage chance of baby momma encounter


@dataclass
class GameState:
    # Core stats
    money: int = Config.INITIAL_MONEY
    damage: int = 0
    lives: int = Config.INITIAL_LIVES
    day: int = 1
    account: int = 0
    loan: int = 0
    members: int = 1
    steps: int = 0
    max_steps: int = Config.MAX_STEPS_PER_DAY

    # Player info
    player_name: str = ""
    gang_name: str = ""
    gender: str = "male"  # "male" or "female"

    # Inventories
    drugs: DrugInventory = field(default_factory=DrugInventory)
    weapons: WeaponInventory = field(default_factory=WeaponInventory)
    flags: GameFlags = field(default_factory=GameFlags)

    # Employed prostitutes (recruited hookers)
    employed_prostitutes: List[Prostitute] = field(default_factory=list)

    # Enemy stats
    squidies: int = 50
    squidies_pistols: int = 50
    squidies_bullets: int = 250
    squidies_uzis: int = 3
    squidies_missiles: int = 5
    squidies_missile_launcher: int = 1
    squidies_grenades: int = 20

    # Dynamic prices
    drug_prices: Dict[str, int] = field(default_factory=dict)

    # Location
    current_location: str = "city"
    position_x: int = 14
    position_y: int = 40

    # MUD room tracking
    current_mud_room: str = "entrance"

    # Discovery tracking for exploration
    discovery_type: str = ""

    def __post_init__(self):
        if not self.drug_prices:
            self.randomize_prices()

    def randomize_prices(self):
        """Randomize drug prices for the day"""
        for drug, (min_price, max_price) in Config.DRUG_PRICE_RANGES.items():
            self.drug_prices[drug] = random.randint(min_price, max_price)

    def can_afford(self, cost: int) -> bool:
        return self.money >= cost

    def spend_money(self, amount: int) -> bool:
        if self.can_afford(amount):
            self.money -= amount
            return True
        return False

    def take_damage(self, damage_amount: int) -> bool:
        """Apply damage, considering vest protection. Returns True if player dies."""
        actual_damage = damage_amount

        if self.weapons.vest > 0:
            blocked = min(damage_amount, self.weapons.vest)
            self.weapons.vest -= blocked
            actual_damage -= blocked

        self.damage += actual_damage

        if self.damage >= Config.DAMAGE_THRESHOLD:
            self.lives -= 1
            self.damage = 0
            return self.lives <= 0

        return False

    def advance_day(self):
        """Handle end-of-day updates"""
        self.day += 1
        self.steps = 0
        self.account = int(self.account * 1.01)  # Interest on savings
        self.loan = int(self.loan * 1.05)        # Interest on loans

        # Enhanced wealth-based recruitment
        wealth_recruitment = int(self.money / 500000)  # Better recruitment rate
        if wealth_recruitment > 0:
            self.members += wealth_recruitment

        # squidies grow stronger
        self.squidies = int(self.squidies * 1.05)
        self.squidies_pistols = int(self.squidies_pistols * 1.1)
        self.squidies_bullets += 20

        self.randomize_prices()


# ===============
# Game Mechanics
# ===============

class GameLogic:
    """Main game logic handler"""

    @staticmethod
    def get_gory_attack_description(attacker: str, defender: str, weapon: str, damage: int) -> str:
        """Generate a random gory description for attacks based on combatants and weapon"""
        import random

        # Base descriptions by weapon type
        weapon_descriptions = {
            'pistol': [
                f"{attacker} squeezes the trigger and {defender}'s chest explodes in a spray of blood and bone fragments!",
                f"A bullet tears through {defender}'s abdomen, intestines spilling out in a steaming pile!",
                f"{attacker} fires point-blank, blowing {defender}'s jaw clean off in a fountain of gore!",
                f"The pistol roars as {defender}'s kneecap shatters, sending shards of bone flying everywhere!",
                f"{attacker} puts a round through {defender}'s eye socket, brains painting the wall behind!"
            ],
            'uzi': [
                f"{attacker} unleashes a hail of bullets, {defender}'s torso turning into bloody Swiss cheese!",
                f"The Uzi rattles as {defender}'s limbs are shredded, blood and flesh flying in all directions!",
                f"{attacker} sprays bullets wildly, {defender}'s face melting into an unrecognizable pulp!",
                f"Lead tears through {defender}'s body, exposing ribs and organs in a gruesome display!",
                f"The automatic fire catches {defender}'s arm, ripping it clean off in a shower of blood!"
            ],
            'grenade': [
                f"{attacker} hurls the grenade and {defender} is vaporized in a massive explosion of flesh and bone!",
                f"The blast catches {defender} full-on, limbs scattering like bloody confetti across the street!",
                f"{attacker}'s grenade detonates, turning {defender} into a crater of smoking meat and shattered bones!",
                f"The explosion rips {defender} apart, chunks of gore raining down on horrified onlookers!",
                f"{defender} is caught in the blast radius, body shredded into a thousand bloody pieces!"
            ],
            'missile_launcher': [
                f"{attacker} fires the RPG-7 and {defender} is obliterated in a fireball of flaming flesh!",
                f"The missile strikes true, {defender}'s body disintegrating in a cloud of blood mist!",
                f"{attacker}'s rocket turns {defender} into a smoking crater filled with charred remains!",
                f"The RPG round impacts, {defender}'s torso exploding outward in a spray of organs and blood!",
                f"{defender} is hit by the missile, body parts flying in every direction like bloody shrapnel!"
            ],
            'knife': [
                f"{attacker} slashes {defender}'s throat, blood spraying like a broken fire hydrant!",
                f"The blade plunges into {defender}'s gut, intestines uncoiling onto the filthy ground!",
                f"{attacker} stabs wildly, {defender}'s chest cavity opening up like a bloody flower!",
                f"{defender}'s screams as {attacker} carves deep gashes, blood pooling beneath their feet!",
                f"The knife finds {defender}'s femoral artery, blood pumping out in rhythmic spurts!"
            ],
            'vampire_bat': [
                f"{attacker} swings the barbed baseball bat, {defender}'s skull cracking like a walnut in a vice!",
                f"The razor-sharp barbs tear through {defender}'s flesh, blood spraying in crimson arcs!",
                f"{attacker} brings the bat down hard, {defender}'s ribs shattering with a sickening crunch!",
                f"The vampire bat's barbs catch {defender}'s arm, ripping muscle and tendon in a bloody mess!",
                f"{attacker} smashes the bat into {defender}'s knee, bone fragments exploding outward!"
            ]
        }

        # Special descriptions for player vs squidie or squidie vs player
        if "player" in attacker.lower() and "squidie" in defender.lower():
            # Player attacking squidie
            special_descriptions = [
                f"You unload on the filthy squidie, {defender}'s disgusting form exploding in a satisfying mess!",
                f"The squidie bastard takes it in the face, brains and ink mixing in a revolting slurry!",
                f"You paint the wall with squidie guts, the tentacled freak finally getting what's coming!",
                f"{defender}'s slimy body ruptures, foul-smelling ichor mixing with blood everywhere!",
                f"You turn the squidie into squidie paste, the streets running with their vile fluids!"
            ]
            if random.random() < 0.7:  # 70% chance for special description
                return random.choice(special_descriptions)

        elif "squidie" in attacker.lower() and "player" in defender.lower():
            # Squidie attacking player
            special_descriptions = [
                f"The disgusting squidie bastard claws at you, their foul tentacles leaving burning wounds!",
                f"Squidie slime burns your skin as {attacker}'s attack tears into your flesh!",
                f"You feel the squidie's vile ichor seeping into your wounds, poisoning your blood!",
                f"{attacker}'s tentacle whips out, leaving deep gashes that ooze with their foul essence!",
                f"The squidie freak's attack splatters you with their disgusting bodily fluids!"
            ]
            if random.random() < 0.7:  # 70% chance for special description
                return random.choice(special_descriptions)

        elif "player" in attacker.lower() and "player" in defender.lower():
            # Player vs Player combat
            special_descriptions = [
                f"{attacker} shows no mercy, {defender}'s screams echoing as flesh is torn asunder!",
                f"In this brutal street fight, {defender}'s blood paints the concrete in vivid crimson!",
                f"{attacker} goes for the kill, {defender}'s vital organs exposed to the cold night air!",
                f"The rivalry boils over as {defender}'s body is riddled with holes, lifeblood draining away!",
                f"{attacker} ends {defender}'s street cred permanently, body left broken and bleeding!"
            ]
            if random.random() < 0.8:  # 80% chance for special description
                return random.choice(special_descriptions)

        # Return random weapon-specific description
        descriptions = weapon_descriptions.get(weapon, weapon_descriptions['knife'])
        return random.choice(descriptions)

    @staticmethod
    def calculate_trade_cost(drug_type: str, quantity: int, game_state: GameState, is_selling: bool = False) -> int:
        """Calculate cost for drug trades"""
        base_price = game_state.drug_prices.get(drug_type, 0)
        if is_selling:
            # Selling prices are lower than buying prices
            markup = {
                'weed': 30, 'crack': 300, 'coke': 3000,
                'ice': 1500, 'percs': 5000, 'pixie_dust': 25000
            }
            return max(0, base_price - markup.get(drug_type, 0)) * quantity
        return base_price * quantity

    def calculate_win_probability(self, game_state: GameState, weapon_type: str) -> float:
        """Calculate win probability for a specific weapon type"""
        base_power = game_state.members

        if weapon_type == 'gun':
            if not game_state.weapons.can_fight_with_pistol():
                return 0.0
            weapon_power = game_state.weapons.pistols * 3  # Guns are strong
            reliability = 0.85  # 85% reliability
        elif weapon_type == 'uzi':
            if game_state.weapons.uzis <= 0 or game_state.weapons.bullets <= 0:
                return 0.0
            weapon_power = game_state.weapons.uzis * 5  # Uzis are very strong
            reliability = 0.9  # 90% reliability
        elif weapon_type == 'grenade':
            if game_state.weapons.grenades <= 0:
                return 0.0
            weapon_power = game_state.weapons.grenades * 4  # Grenades are area effect
            reliability = 0.95  # 95% reliability
        elif weapon_type == 'missile_launcher':
            if game_state.weapons.missile_launcher <= 0 or game_state.weapons.missiles <= 0:
                return 0.0
            weapon_power = game_state.weapons.missile_launcher * 8  # RPG-7 launchers are devastating
            reliability = 0.98  # 98% reliability
        elif weapon_type == 'knife':
            if not game_state.weapons.can_fight_with_knife():
                return 0.0
            weapon_power = game_state.weapons.knife * 2  # Knives are weaker
            reliability = 0.65  # 65% reliability (more risky)
        elif weapon_type == 'vampire_bat':
            if game_state.weapons.vampire_bat <= 0:
                return 0.0
            weapon_power = game_state.weapons.vampire_bat * 3  # Medium power, between knife and pistol
            reliability = 0.75  # 75% reliability (good but not great)
        else:
            return 0.0

        total_power = base_power + weapon_power
        enemy_power = 4  # Average enemy power

        # Calculate base win chance
        if total_power > enemy_power:
            base_chance = min(0.95, 0.5 + (total_power - enemy_power) * 0.1)
        else:
            base_chance = max(0.05, 0.5 - (enemy_power - total_power) * 0.15)

        return base_chance * reliability

    def get_weapon_options(self, game_state: GameState) -> Dict[str, Dict[str, any]]:
        """Get available weapon options with their probabilities"""
        options = {}

        if game_state.weapons.can_fight_with_pistol():
            win_prob = self.calculate_win_probability(game_state, 'gun')
            options['gun'] = {
                'name': 'Pistol',
                'win_probability': win_prob,
                'description': f"Powerful and reliable. {win_prob:.0%} chance to win.",
                'damage_range': '2-8',
                'special': 'Uses 1 bullet per fight'
            }

        if game_state.weapons.uzis > 0 and game_state.weapons.bullets > 0:
            win_prob = self.calculate_win_probability(game_state, 'uzi')
            options['uzi'] = {
                'name': 'Uzi',
                'win_probability': win_prob,
                'description': f"Very powerful automatic weapon. {win_prob:.0%} chance to win.",
                'damage_range': '3-12',
                'special': 'Uses 2 bullets per fight'
            }

        if game_state.weapons.grenades > 0:
            win_prob = self.calculate_win_probability(game_state, 'grenade')
            options['grenade'] = {
                'name': 'Grenade',
                'win_probability': win_prob,
                'description': f"Area effect explosive. {win_prob:.0%} chance to win.",
                'damage_range': '5-20',
                'special': 'Destroys enemy group'
            }

        if game_state.weapons.missile_launcher > 0 and game_state.weapons.missiles > 0:
            win_prob = self.calculate_win_probability(game_state, 'missile_launcher')
            options['missile_launcher'] = {
                'name': 'Missile Launcher',
                'win_probability': win_prob,
                'description': f"Devastating long-range weapon. {win_prob:.0%} chance to win.",
                'damage_range': '10-50',
                'special': 'High damage, low ammo'
            }

        if game_state.weapons.can_fight_with_knife():
            win_prob = self.calculate_win_probability(game_state, 'knife')
            options['knife'] = {
                'name': 'Knife',
                'win_probability': win_prob,
                'description': f"Melee weapon, risky but silent. {win_prob:.0%} chance to win.",
                'damage_range': '1-5',
                'special': 'No ammo required'
            }

        if game_state.weapons.vampire_bat > 0:
            win_prob = self.calculate_win_probability(game_state, 'vampire_bat')
            options['vampire_bat'] = {
                'name': 'Vampire Bat',
                'win_probability': win_prob,
                'description': f"Barbed baseball bat, brutal melee weapon. {win_prob:.0%} chance to win.",
                'damage_range': '2-6',
                'special': 'No ammo required, high damage potential'
            }

        return options


# ===============
# Flask App
# ===============

app = Flask(__name__)
app.config.from_object(Config)

# Handle SocketIO for PyInstaller bundles
# Enable SocketIO for both development and bundled applications
if Config.IS_BUNDLED:
    # For bundled applications, let SocketIO auto-detect async mode (threading forced by env var)
    socketio = SocketIO(app, engineio_logger=False, cors_allowed_origins="*")
    print("Running in bundled mode - SocketIO enabled")
else:
    # For development, use threading mode
    socketio = SocketIO(app, async_mode='threading', engineio_logger=False, cors_allowed_origins="*")
    print("SocketIO enabled")

# Routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/new_game', methods=['GET', 'POST'])
def new_game():
    if request.method == 'POST':
        # Handle new game creation
        player_name = request.form.get('player_name')
        gang_name = request.form.get('gang_name')
        gender = request.form.get('gender', 'male')
        game_state = GameState(player_name=player_name, gang_name=gang_name, gender=gender)
        session['game_state'] = asdict(game_state)
        return redirect(url_for('city'))
    return render_template('new_game.html')

@app.route('/city')
def city():
    game_state = get_game_state()
    # Update current location for SocketIO room
    game_state.current_location = "city"
    session['game_state'] = asdict(game_state)
    return render_template('city.html', game_state=game_state)

@app.route('/bank')
def bank():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))
    # Update current location for SocketIO room
    game_state.current_location = "bank"
    session['game_state'] = asdict(game_state)
    return render_template('bank.html', game_state=game_state)

@app.route('/bar')
def bar():
    game_state = get_game_state()
    # Update current location for SocketIO room
    game_state.current_location = "bar"
    session['game_state'] = asdict(game_state)
    return render_template('bar.html', game_state=game_state)

def get_current_room(room_id: str) -> Room:
    """Get room data for the given room ID"""
    # Define expanded alleyway rooms for MUD system
    rooms = {
        'entrance': Room(
            id='entrance',
            title='The Dark Alleyway Entrance',
            description='You stand at the entrance of a dark, narrow alleyway. The streetlights from the main road cast long shadows that dance on the cracked pavement. The air smells of garbage and something metallic.',
            exits={'north': 'alley1', 'south': 'city', 'east': 'alley_dead_end'}
        ),
        'alley1': Room(
            id='alley1',
            title='Middle of the Alleyway',
            description='Deeper into the alley, the walls close in around you. Graffiti covers the brick surfaces, and you can hear the distant sounds of traffic. A few rats scurry away as you approach.',
            exits={'north': 'alley2', 'south': 'entrance', 'east': 'side_street', 'west': 'abandoned_lot'}
        ),
        'alley2': Room(
            id='alley2',
            title='End of the Alleyway',
            description='You\'ve reached the far end of the alley. A chain-link fence blocks further progress to the north. To the west, you see a small door that might lead somewhere interesting.',
            exits={'south': 'alley1', 'west': 'hidden_room', 'up': 'rooftop', 'north': 'alley_fork'}
        ),
        'alley_fork': Room(
            id='alley_fork',
            title='Alleyway Fork',
            description="The alley splits into two paths here. To the northeast, you see a dimly lit passage. To the northwest, there's a narrow gap between buildings that looks dangerous.",
            exits={'south': 'alley2', 'northeast': 'drug_den', 'northwest': 'back_alley'}
        ),
        'drug_den': Room(
            id='drug_den',
            title='Abandoned Drug Den',
            description='This looks like it used to be a drug dealing spot. Old mattresses and discarded needles litter the ground. The air smells strongly of chemicals and decay.',
            exits={'southwest': 'alley_fork', 'north': 'crack_house_entrance'},
            has_encounter=True,
            encounter_chance=45
        ),
        'crack_house_entrance': Room(
            id='crack_house_entrance',
            title='Crack House Entrance',
            description='You\'ve found the entrance to an old crack house. The windows are boarded up and the door hangs off its hinges. Strange sounds come from inside.',
            exits={'south': 'drug_den', 'inside': 'crack_house_interior'},
            has_encounter=True,
            encounter_chance=55
        ),
        'crack_house_interior': Room(
            id='crack_house_interior',
            title='Inside the Crack House',
            description='The interior is dark and filthy. The walls are covered in strange symbols and graffiti. You can hear faint moaning sounds from deeper within.',
            exits={'outside': 'crack_house_entrance', 'upstairs': 'crack_house_upstairs'},
            has_encounter=True,
            encounter_chance=50
        ),
        'crack_house_upstairs': Room(
            id='crack_house_upstairs',
            title='Crack House Upstairs',
            description='The upstairs room is even more dilapidated than downstairs. The floor creaks under your feet, and you can see the city through holes in the roof.',
            exits={'downstairs': 'crack_house_interior', 'north': 'rooftop_access'},
            has_encounter=True,
            encounter_chance=45
        ),
        'back_alley': Room(
            id='back_alley',
            title='Back Alley Passage',
            description='This narrow passage between buildings is extremely dark and claustrophobic. The walls seem to close in on you from both sides.',
            exits={'southeast': 'alley_fork', 'north': 'dead_end_alley', 'west': 'service_entrance'},
            has_encounter=True,
            encounter_chance=60
        ),
        'dead_end_alley': Room(
            id='dead_end_alley',
            title='Dead End Alley',
            description='This alley ends abruptly at a brick wall. There\'s nowhere else to go from here. You notice some suspicious markings on the wall and what looks like a small drainage grate hidden in the shadows.',
            exits={'south': 'back_alley', 'down': 'sewer_grate'},
            has_encounter=True,
            encounter_chance=30
        ),
        'sewer_grate': Room(
            id='sewer_grate',
            title='Sewer Grate Entrance',
            description='You\'ve found a rusty sewer grate partially covered by debris. The air coming from below smells overwhelmingly foul. You\'ll have to squeeze through the narrow opening to enter.',
            exits={'up': 'dead_end_alley', 'down': 'sewer_maintenance_tunnel'},
            has_encounter=True,
            encounter_chance=50
        ),
        'sewer_maintenance_tunnel': Room(
            id='sewer_maintenance_tunnel',
            title='Sewer Maintenance Tunnel',
            description='You\'re in a narrow maintenance tunnel running alongside the main sewer line. The walls are slick with moisture and the air is thick with the stench of decay. The tunnel continues north into darkness.',
            exits={'up': 'sewer_grate', 'north': 'sewer_flooded_chamber'},
            has_encounter=True,
            encounter_chance=70
        ),
        'sewer_flooded_chamber': Room(
            id='sewer_flooded_chamber',
            title='Flooded Sewer Chamber',
            description='You\'ve reached a large flooded chamber in the sewer system. The water level looks dangerously high, and you can hear a ominous rumbling sound echoing through the pipes.',
            exits={'south': 'sewer_maintenance_tunnel', 'north': 'sewer_death_trap'},
            has_encounter=True,
            encounter_chance=80
        ),
        'sewer_death_trap': Room(
            id='sewer_death_trap',
            title='Sewer Death Trap',
            description='As you step forward, you trigger a hidden mechanism! The chamber begins to flood rapidly with raw sewage. There\'s no escape as a massive wave of shit comes crashing down!',
            exits={},  # No exits - instant death
            has_encounter=True,
            encounter_chance=100
        ),
        'service_entrance': Room(
            id='service_entrance',
            title='Service Entrance',
            description='You\'ve found a service entrance to what appears to be a restaurant. The door is slightly ajar, and you can smell cooking oil from inside.',
            exits={'east': 'back_alley', 'inside': 'restaurant_kitchen'},
            has_encounter=True,
            encounter_chance=25
        ),
        'restaurant_kitchen': Room(
            id='restaurant_kitchen',
            title='Restaurant Kitchen',
            description='The kitchen is surprisingly clean and well-organized. Pots and pans hang from the ceiling, and the air smells of spices and cooking meat.',
            exits={'outside': 'service_entrance', 'north': 'restaurant_dining'},
            has_encounter=True,
            encounter_chance=20
        ),
        'restaurant_dining': Room(
            id='restaurant_dining',
            title='Restaurant Dining Area',
            description='The dining area is empty at this late hour. Tables are set with white tablecloths and silverware. A cash register sits on the counter.',
            exits={'south': 'restaurant_kitchen', 'east': 'alley_dead_end'},
            has_encounter=True,
            encounter_chance=15
        ),
        'alley_dead_end': Room(
            id='alley_dead_end',
            title='Alley Dead End',
            description='This part of the alley ends at a tall brick wall covered in ivy. There\'s no way through here. You can hear traffic from the nearby street.',
            exits={'west': 'restaurant_dining', 'south': 'entrance'},
            has_encounter=True,
            encounter_chance=20
        ),
        'side_street': Room(
            id='side_street',
            title='Side Street',
            description='This narrow side street runs parallel to the main alley. A few parked cars line the curb, and you can see apartment windows with their lights on above.',
            exits={'west': 'alley1', 'north': 'burned_building'}
        ),
        'hidden_room': Room(
            id='hidden_room',
            title='Hidden Room',
            description='Behind the door is a small, dimly lit room. It looks like it might have been used for storage at some point. There\'s a table in the corner with some suspicious-looking items on it.',
            exits={'east': 'alley2', 'down': 'basement'}
        ),
        'abandoned_lot': Room(
            id='abandoned_lot',
            title='Abandoned Parking Lot',
            description='You find yourself in a weed-choked parking lot filled with rusted-out cars. The asphalt is cracked and broken, with nature reclaiming the space. A chain-link fence surrounds the area, but you spot a gap to the north.',
            exits={'east': 'alley1', 'north': 'construction_site'},
            has_encounter=True,
            encounter_chance=30
        ),
        'construction_site': Room(
            id='construction_site',
            title='Abandoned Construction Site',
            description='This looks like a building project that was abandoned years ago. Scaffolding towers loom overhead, and partially built walls stand like skeletal remains. Construction equipment sits rusting in the mud, and the air smells of damp concrete and decay.',
            exits={'south': 'abandoned_lot', 'west': 'burned_building'},
            has_encounter=True,
            encounter_chance=25
        ),
        'burned_building': Room(
            id='burned_building',
            title='Burned-Out Building',
            description='The charred remains of what was once an apartment building stand before you. The walls are blackened with soot, and the windows are either broken or boarded up. You can smell the acrid scent of burned wood and plastic.',
            exits={'south': 'side_street', 'east': 'construction_site', 'inside': 'building_interior'},
            has_encounter=True,
            encounter_chance=20
        ),
        'building_interior': Room(
            id='building_interior',
            title='Building Interior',
            description='Inside the burned building, the air is thick with dust and the smell of smoke. The floor is covered in debris, and you can see the sky through holes in the ceiling. Something glints in the corner - might be worth investigating.',
            exits={'outside': 'burned_building'},
            has_encounter=True,
            encounter_chance=15
        ),
        'rooftop': Room(
            id='rooftop',
            title='Rooftop Access',
            description='From this rooftop, you have a commanding view of the surrounding streets. The city lights twinkle in the distance, and you can see the alleyway snaking below you like a dark river. A fire escape leads down to the alley.',
            exits={'down': 'alley2', 'jump': 'alley1'},
            has_encounter=True,
            encounter_chance=10
        ),
        'rooftop_access': Room(
            id='rooftop_access',
            title='Rooftop Access',
            description='You\'ve climbed onto another rooftop. From here you can see the entire alleyway network below you. The night air is cool and carries the sounds of the city.',
            exits={'down': 'crack_house_upstairs'},
            has_encounter=True,
            encounter_chance=15
        ),
        'basement': Room(
            id='basement',
            title='Damp Basement',
            description='The basement is cold and damp, with water dripping from the ceiling. Old boxes and forgotten furniture are stacked against the walls. You hear the scurrying of small animals in the darkness, and the air feels heavy and oppressive.',
            exits={'up': 'hidden_room', 'north': 'sewer_entrance'},
            has_encounter=True,
            encounter_chance=35
        ),
        'sewer_entrance': Room(
            id='sewer_entrance',
            title='Sewer Entrance',
            description='A rusty manhole cover leads down into the city\'s sewer system. The smell is overwhelming - a mix of decay, chemicals, and worse. You can hear the distant rush of water echoing from below.',
            exits={'south': 'basement', 'down': 'sewer_tunnel'},
            has_encounter=True,
            encounter_chance=40
        ),
        'sewer_tunnel': Room(
            id='sewer_tunnel',
            title='Sewer Tunnel',
            description='The sewer tunnel is narrow and claustrophobic. Water flows slowly along the curved floor, carrying who-knows-what. The walls are slick with slime, and the air is thick and humid. Rats watch you from the shadows.',
            exits={'up': 'sewer_entrance', 'north': 'underground_chamber'},
            has_encounter=True,
            encounter_chance=45
        ),
        'underground_chamber': Room(
            id='underground_chamber',
            title='Underground Chamber',
            description='You\'ve discovered a hidden underground chamber beneath the city. The walls are lined with old bricks, and there are signs that this place was used for something illicit in the past. A small stream of water flows through the center.',
            exits={'south': 'sewer_tunnel'},
            has_encounter=True,
            encounter_chance=50
        )
    }

    return rooms.get(room_id, rooms['entrance'])  # Default to entrance if room not found

@app.route('/alleyway')
def alleyway():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    current_room = get_current_room(game_state.current_mud_room)

    # Check for random encounters
    encounter_triggered = False
    if current_room.has_encounter and random.random() * 100 < current_room.encounter_chance:
        encounter_triggered = True
        # Trigger encounter
        return redirect(url_for('encounter'))

    # Update current location for SocketIO room
    game_state.current_location = "alleyway"
    session['game_state'] = asdict(game_state)

    return render_template('alleyway.html', game_state=game_state, current_room=current_room)

@app.route('/move_room/<direction>')
def move_room(direction):
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    current_room = get_current_room(game_state.current_mud_room)

    if direction in current_room.exits:
        new_room_id = current_room.exits[direction]
        game_state.current_mud_room = new_room_id

        # Increment steps for each room entered in the dark alleyway
        game_state.steps += 1

        session['game_state'] = asdict(game_state)

        # Check for special room effects
        if new_room_id == 'sewer_death_trap':
            # Instant death from massive wave of shit
            game_state.damage = Config.DAMAGE_THRESHOLD  # Set to max damage
            game_state.lives = 0  # Kill the player instantly
            session['game_state'] = asdict(game_state)
            return redirect(url_for('game_over'))

        # Check for encounters in the new room
        new_room = get_current_room(new_room_id)
        if new_room.has_encounter and random.random() * 100 < new_room.encounter_chance:
            return redirect(url_for('encounter'))

        return redirect(url_for('alleyway'))
    else:
        # Invalid direction - stay in current room
        return redirect(url_for('alleyway'))

@app.route('/crackhouse')
def crackhouse():
    game_state = get_game_state()
    # Update current location for SocketIO room
    game_state.current_location = "crackhouse"
    session['game_state'] = asdict(game_state)
    return render_template('crackhouse.html', game_state=game_state)

@app.route('/gunshack')
def gunshack():
    game_state = get_game_state()
    # Update current location for SocketIO room
    game_state.current_location = "gunshack"
    session['game_state'] = asdict(game_state)
    return render_template('gunshack.html', game_state=game_state)

@app.route('/picknsave')
def picknsave():
    game_state = get_game_state()
    # Update current location for SocketIO room
    game_state.current_location = "picknsave"
    session['game_state'] = asdict(game_state)
    return render_template('picknsave.html', game_state=game_state)

@app.route('/infobooth')
def infobooth():
    game_state = get_game_state()
    return render_template('infobooth.html', game_state=game_state)

@app.route('/credits')
def credits():
    game_state = get_game_state()
    return render_template('credits.html', game_state=game_state)

@app.route('/stats')
def stats():
    game_state = get_game_state()
    return render_template('stats.html', game_state=game_state)

@app.route('/npcs')
def npcs():
    game_state = get_game_state()
    return render_template('npcs.html', game_state=game_state)

@app.route('/encounter')
def encounter():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    import random

    # Random encounter types
    encounter_types = [
        ("squidies", "You run into some Squidies gang members who look like they're up to no good."),
        ("baby_momma", "Your baby momma spots you from across the street and starts heading your way."),
        ("discovery", "You notice an abandoned building that looks like it might contain something valuable."),
        ("drug_deal", "A shady character approaches you with a proposition for a drug deal."),
        ("potential_hooker", f"You encounter {random.choice(POTENTIAL_HOOKERS).name}, a potential hooker who looks like she could use some help.")
    ]

    encounter_type, description = random.choice(encounter_types)

    return render_template('encounter.html', game_state=game_state, encounter_type=encounter_type, encounter_description=description)

@app.route('/npc_interaction/<npc>')
def npc_interaction(npc):
    game_state = get_game_state()

    # Handle new NPCs
    if npc in NPCS:
        npc_data = NPCS[npc]
        # Create a dict with the NPC data for template compatibility
        npc_info = {
            'id': npc_data.id,
            'name': npc_data.name,
            'description': npc_data.description,
            'dialogue': npc_data.dialogue,
            'personality': npc_data.personality,
            'special_ability': npc_data.special_ability,
            'sells_drugs': npc_data.sells_drugs,
            'is_alive': True,  # All NPCs in this system are alive
            'hp': npc_data.health,
            'max_hp': npc_data.health
        }
        return render_template('npc_interaction.html', game_state=game_state, npc=npc_info)

    # Legacy NPC handling
    else:
        # Create basic NPC info for legacy NPCs
        npc_info = {
            'id': npc,
            'name': npc.title(),
            'description': f'A shady character named {npc.title()}.',
            'dialogue': f'{npc.title()} looks at you suspiciously.',
            'personality': 'suspicious',
            'special_ability': 'unknown',
            'sells_drugs': False,
            'is_alive': True,
            'hp': 10,
            'max_hp': 10
        }
        return render_template('npc_interaction.html', game_state=game_state, npc=npc_info)

@app.route('/npc_trade/<npc>', methods=['GET', 'POST'])
def npc_trade(npc):
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    # Get NPC data
    if npc not in NPCS:
        return redirect(url_for('city'))

    npc_data = NPCS[npc]

    if request.method == 'POST':
        trade_type = request.form.get('trade_type')
        item_type = request.form.get('item_type')
        quantity = int(request.form.get('quantity', 0))

        if trade_type == 'buy':
            # Player buying from NPC
            if item_type not in ['weed', 'crack', 'coke', 'ice', 'percs', 'pixie_dust']:
                return render_template('npc_trade.html', game_state=game_state, npc=npc_data,
                                     error="Invalid item type")

            # Check if NPC has the item
            npc_quantity = getattr(npc_data.drugs, item_type, 0)
            if npc_quantity < quantity:
                return render_template('npc_trade.html', game_state=game_state, npc=npc_data,
                                     error=f"NPC only has {npc_quantity} kilos of {item_type}")

            # Calculate cost with NPC's price modifier
            base_price = game_state.drug_prices[item_type]
            cost = int(base_price * npc_data.drug_price_modifier * quantity)

            if not game_state.can_afford(cost):
                return render_template('npc_trade.html', game_state=game_state, npc=npc_data,
                                     error=f"You can't afford ${cost} for {quantity} kilos of {item_type}")

            # Execute trade
            game_state.spend_money(cost)
            game_state.drugs.modify_drug(item_type, quantity)
            npc_data.drugs.modify_drug(item_type, -quantity)

            result = f"You bought {quantity} kilos of {item_type} for ${cost}"
            return render_template('wander_result.html', game_state=game_state, result=result)

        elif trade_type == 'sell':
            # Player selling to NPC
            if item_type not in ['weed', 'crack', 'coke', 'ice', 'percs', 'pixie_dust']:
                return render_template('npc_trade.html', game_state=game_state, npc=npc_data,
                                     error="Invalid item type")

            # Check if player has the item
            player_quantity = getattr(game_state.drugs, item_type, 0)
            if player_quantity < quantity:
                return render_template('npc_trade.html', game_state=game_state, npc=npc_data,
                                     error=f"You only have {player_quantity} kilos of {item_type}")

            # Calculate sell price (lower than buy price)
            base_price = game_state.drug_prices[item_type]
            sell_price = int(base_price * 0.7 * quantity)  # 70% of buy price

            # Execute trade
            game_state.money += sell_price
            game_state.drugs.modify_drug(item_type, -quantity)
            npc_data.drugs.modify_drug(item_type, quantity)

            result = f"You sold {quantity} units of {item_type} for ${sell_price}"
            return render_template('wander_result.html', game_state=game_state, result=result)

    return render_template('npc_trade.html', game_state=game_state, npc=npc_data)

@app.route('/exploration_result')
def exploration_result():
    game_state = get_game_state()
    return render_template('exploration_result.html', game_state=game_state)

@app.route('/wander_result')
def wander_result():
    game_state = get_game_state()
    return render_template('wander_result.html', game_state=game_state)

@app.route('/gang_war')
def gang_war():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    # Check if player has enough members for gang war
    if game_state.members <= 25:
        return render_template('wander_result.html',
                             game_state=game_state,
                             result="You don't have enough gang members to start a war! You need more than 25 members to challenge the Squidies.")

    return render_template('gang_war.html', game_state=game_state)

@app.route('/start_war', methods=['POST'])
def start_war():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    # Calculate battle outcome based on forces
    player_power = (game_state.members * 10 +
                   game_state.weapons.pistols * 5 +
                   game_state.weapons.uzis * 15 +
                   game_state.weapons.grenades * 20 +
                   game_state.weapons.missiles * 50)

    enemy_power = (game_state.squidies * 8 +
                  game_state.squidies_pistols * 4 +
                  game_state.squidies_uzis * 12 +
                  game_state.squidies_grenades * 18 +
                  game_state.squidies_missiles * 45)

    # Add some randomness
    player_power *= (0.8 + random.random() * 0.4)  # 80-120% variation
    enemy_power *= (0.8 + random.random() * 0.4)   # 80-120% variation

    if player_power > enemy_power:
        # Player wins
        return redirect(url_for('victory'))
    else:
        # Player loses - game over
        return redirect(url_for('defeat'))

@app.route('/cop_chase')
def cop_chase():
    game_state = get_game_state()
    return render_template('cop_chase.html', game_state=game_state)

@app.route('/cop_victory')
def cop_victory():
    game_state = get_game_state()
    return render_template('cop_victory.html', game_state=game_state)

@app.route('/final_battle')
def final_battle():
    game_state = get_game_state()
    return render_template('final_battle.html', game_state=game_state)

@app.route('/start_final_battle', methods=['POST'])
def start_final_battle():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    # Similar calculation but for final battle
    player_power = (game_state.members * 12 +
                   game_state.weapons.pistols * 6 +
                   game_state.weapons.uzis * 18 +
                   game_state.weapons.grenades * 25 +
                   game_state.weapons.missiles * 60 +
                   game_state.weapons.missile_launcher * 30)

    enemy_power = (game_state.squidies * 10 +
                  game_state.squidies_pistols * 5 +
                  game_state.squidies_uzis * 15 +
                  game_state.squidies_grenades * 22 +
                  game_state.squidies_missiles * 55 +
                  game_state.squidies_missile_launcher * 25)

    # Add some randomness
    player_power *= (0.85 + random.random() * 0.3)  # 85-115% variation
    enemy_power *= (0.85 + random.random() * 0.3)   # 85-115% variation

    if player_power > enemy_power:
        # Player wins
        return redirect(url_for('victory'))
    else:
        # Player loses - game over
        return redirect(url_for('defeat'))

@app.route('/victory')
def victory():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    # Achievement-based recruitment for major victories
    # Bonus recruitment for defeating the Squidies
    achievement_bonus = random.randint(3, 8)  # 3-8 new members from the victory
    game_state.members += achievement_bonus

    # Save the updated game state
    session['game_state'] = asdict(game_state)

    return render_template('victory.html', game_state=game_state, achievement_bonus=achievement_bonus)

@app.route('/game_win')
def game_win():
    game_state = get_game_state()
    return render_template('game_win.html', game_state=game_state)

@app.route('/game_loss')
def game_loss():
    game_state = get_game_state()
    return render_template('game_loss.html', game_state=game_state)

@app.route('/game_over')
def game_over():
    game_state = get_game_state()
    return render_template('game_over.html', game_state=game_state)

@app.route('/defeat')
def defeat():
    game_state = get_game_state()
    return render_template('defeat.html', game_state=game_state)

@app.route('/day_end')
def day_end():
    game_state = get_game_state()
    return render_template('day_end.html', game_state=game_state)

@app.route('/closet')
def closet():
    game_state = get_game_state()
    return render_template('closet.html', game_state=game_state)

@app.route('/wander')
def wander():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    import random

    # Increment steps
    game_state.steps += 1

    # Fear-based recruitment: If player is powerful, rival gangs may send emissaries
    fear_recruit_chance = 0.0
    if game_state.members >= 15:  # Powerful gang
        fear_recruit_chance = 0.05  # 5% chance
    elif game_state.members >= 25:  # Very powerful
        fear_recruit_chance = 0.1   # 10% chance
    elif game_state.members >= 35:  # Extremely powerful
        fear_recruit_chance = 0.15  # 15% chance

    if random.random() < fear_recruit_chance:
        # Fear-based recruitment offer
        recruited = random.randint(2, 5)
        game_state.members += recruited
        session['game_state'] = asdict(game_state)
        result = f"🏴 A rival gang emissary approaches you trembling! 'Boss, we heard about your power and want to join you instead of fighting!' {recruited} members from a rival gang defected to your side out of fear!"
        return render_template('wander_result.html', game_state=game_state, result=result)

    # Random scenarios
    rand = random.random()

    if rand < 0.1:  # 10% - Find money
        found_money = random.randint(10, 100)
        game_state.money += found_money
        session['game_state'] = asdict(game_state)
        return render_template('wander_result.html', game_state=game_state, result=f"You found ${found_money} on the ground!")

    elif rand < 0.2:  # 10% - Find drugs
        drug_types = ['weed', 'crack', 'coke', 'ice', 'percs', 'pixie_dust']
        drug = random.choice(drug_types)
        amount = random.randint(1, 5)
        game_state.drugs.modify_drug(drug, amount)
        session['game_state'] = asdict(game_state)
        return render_template('wander_result.html', game_state=game_state, result=f"You found {amount} units of {drug}!")

    elif rand < 0.3:  # 10% - Get robbed
        if game_state.money > 0:
            lost_money = min(random.randint(50, 200), game_state.money)
            game_state.money -= lost_money
            session['game_state'] = asdict(game_state)
            return render_template('wander_result.html', game_state=game_state, result=f"You got robbed! Lost ${lost_money}.")

    elif rand < 0.4:  # 10% - Police encounter
        return redirect(url_for('cop_chase'))

    elif rand < 0.5:  # 10% - Gang encounter (only if powerful enough)
        if game_state.members > 25:
            return redirect(url_for('gang_war'))
        else:
            # Redirect to a different encounter if not powerful enough
            return redirect(url_for('encounter'))

    elif rand < 0.65:  # 15% - Meet NPC (increased from 10%)
        # Include both old and new NPCs
        npcs = ['nox', 'raze', 'void', 'whisper', 'scarface', 'big_mama', 'slick_vic', 'mad_dog', 'shadow', 'blade_master', 'cyber_punk', 'witch_doctor', 'demolition_man', 'ghost_rider']
        npc = random.choice(npcs)
        return redirect(url_for('npc_interaction', npc=npc))

    elif rand < 0.75:  # 10% - Find weapon
        weapons = ['pistol', 'bullets', 'grenade']
        weapon = random.choice(weapons)
        if weapon == 'pistol':
            game_state.weapons.pistols += 1
            result = "You found a pistol!"
        elif weapon == 'bullets':
            game_state.weapons.bullets += random.randint(5, 20)
            result = "You found some bullets!"
        elif weapon == 'grenade':
            game_state.weapons.grenades += 1
            result = "You found a grenade!"
        session['game_state'] = asdict(game_state)
        return render_template('wander_result.html', game_state=game_state, result=result)

    elif rand < 0.8:  # 10% - Get injured
        damage = random.randint(1, 3)
        died = game_state.take_damage(damage)
        if died:
            session['game_state'] = asdict(game_state)
            return redirect(url_for('game_over'))
        session['game_state'] = asdict(game_state)
        return render_template('wander_result.html', game_state=game_state, result=f"You got injured! Took {damage} damage.")

    elif rand < 0.9:  # 10% - Random encounter
        return redirect(url_for('encounter'))

    else:  # 10% - Nothing happens
        session['game_state'] = asdict(game_state)
        return render_template('wander_result.html', game_state=game_state, result="You wandered around but nothing interesting happened.")

@app.route('/trade_drugs', methods=['POST'])
def trade_drugs():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    action = request.form.get('action')
    drug_type = request.form.get('drug_type')
    quantity = int(request.form.get('quantity', 0))

    if action == 'buy':
        cost = GameLogic.calculate_trade_cost(drug_type, quantity, game_state, is_selling=False)
        if game_state.can_afford(cost):
            game_state.spend_money(cost)
            game_state.drugs.modify_drug(drug_type, quantity)
        # Else, maybe flash message, but for now ignore
    elif action == 'sell':
        if game_state.drugs.get_drug_amount(drug_type) >= quantity:
            cost = GameLogic.calculate_trade_cost(drug_type, quantity, game_state, is_selling=True)
            game_state.money += cost
            game_state.drugs.modify_drug(drug_type, -quantity)

    session['game_state'] = asdict(game_state)
    return redirect(url_for('crackhouse'))

@app.route('/buy_weapon', methods=['POST'])
def buy_weapon():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    weapon_type = request.form.get('weapon_type')
    quantity = int(request.form.get('quantity', 1))

    price = Config.WEAPON_PRICES.get(weapon_type, 0) * quantity

    if game_state.can_afford(price):
        game_state.spend_money(price)
        # Update inventory based on weapon_type
        if weapon_type == 'gun':
            game_state.weapons.pistols += quantity
        elif weapon_type == 'bullets':
            game_state.weapons.bullets += quantity * 50  # 50-pack
        elif weapon_type == 'uzi':
            game_state.weapons.uzis += quantity
        elif weapon_type == 'grenade':
            game_state.weapons.grenades += quantity
        elif weapon_type == 'missile_launcher':
            game_state.weapons.missile_launcher += quantity
        elif weapon_type == 'missile':
            game_state.weapons.missiles += quantity
        elif weapon_type == 'vest_light':
            game_state.weapons.vest += 5 * quantity
        elif weapon_type == 'vest_medium':
            game_state.weapons.vest += 10 * quantity
        elif weapon_type == 'vest_heavy':
            game_state.weapons.vest += 15 * quantity
        elif weapon_type == 'vampire_bat':
            game_state.weapons.vampire_bat += quantity

    session['game_state'] = asdict(game_state)
    return redirect(url_for('gunshack'))

@app.route('/recruit_hooker/<hooker_name>', methods=['GET', 'POST'])
def recruit_hooker(hooker_name):
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    # Find the potential hooker
    potential_hooker = None
    for hooker in POTENTIAL_HOOKERS:
        if hooker.name == hooker_name:
            potential_hooker = hooker
            break

    if not potential_hooker:
        return redirect(url_for('city'))

    if request.method == 'POST':
        # Check if player has the required drugs and money
        can_afford = True
        missing_items = []

        # Check money
        if game_state.money < potential_hooker.recruitment_cost_money:
            can_afford = False
            missing_items.append(f"${potential_hooker.recruitment_cost_money - game_state.money} more money")

        # Check drugs
        for drug_type, required_amount in potential_hooker.recruitment_cost_drugs.items():
            current_amount = getattr(game_state.drugs, drug_type, 0)
            if current_amount < required_amount:
                can_afford = False
                missing_items.append(f"{required_amount - current_amount} more {drug_type}")

        if not can_afford:
            result = f"You don't have enough to recruit {hooker_name}! You need: {', '.join(missing_items)}"
            return render_template('wander_result.html', game_state=game_state, result=result)

        # Pay the costs
        game_state.spend_money(potential_hooker.recruitment_cost_money)
        for drug_type, required_amount in potential_hooker.recruitment_cost_drugs.items():
            game_state.drugs.modify_drug(drug_type, -required_amount)

        # Create the employed prostitute
        employed_prostitute = Prostitute(
            name=potential_hooker.name,
            price=potential_hooker.stats['price'],
            description=f"{potential_hooker.description} (Employed by you)",
            risk_level=potential_hooker.stats['risk_level'],
            healing_amount=potential_hooker.stats['healing_amount'],
            death_risk=potential_hooker.stats['death_risk'],
            death_method=potential_hooker.stats['death_method']
        )

        # Add to employed prostitutes
        game_state.employed_prostitutes.append(employed_prostitute)

        session['game_state'] = asdict(game_state)
        result = f"🎉 You successfully recruited {hooker_name}! She now works for you and is available at the crack house."
        return render_template('wander_result.html', game_state=game_state, result=result)

    return render_template('recruit_hooker.html', game_state=game_state, hooker=potential_hooker)

@app.route('/visit_prostitutes', methods=['GET', 'POST'])
def visit_prostitutes():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    if request.method == 'POST':
        prostitute_name = request.form.get('prostitute_name')
        if not prostitute_name:
            return redirect(url_for('crackhouse'))

        # Find the selected prostitute (check both default and employed)
        selected_prostitute = None

        # Check default prostitutes
        for prostitute in PROSTITUTES:
            if prostitute.name == prostitute_name:
                selected_prostitute = prostitute
                break

        # Check employed prostitutes
        if not selected_prostitute:
            for prostitute in game_state.employed_prostitutes:
                if prostitute.name == prostitute_name:
                    selected_prostitute = prostitute
                    break

        if not selected_prostitute:
            return redirect(url_for('crackhouse'))

        # Check if player can afford
        if not game_state.can_afford(selected_prostitute.price):
            result = f"You don't have enough money for {selected_prostitute.name}! You need ${selected_prostitute.price}."
            return render_template('wander_result.html', game_state=game_state, result=result)

        # Pay for services
        game_state.spend_money(selected_prostitute.price)

        # Roll for death risk
        import random
        death_roll = random.random() * 100

        if death_roll < selected_prostitute.death_risk:
            # Player dies from the encounter
            if selected_prostitute.death_method == "aids":
                result = f"💀 OH NO! {selected_prostitute.name} gave you AIDS! You die a slow, painful death from the disease. 💀"
            elif selected_prostitute.death_method == "gun":
                result = f"💀 DANGER! {selected_prostitute.name} pulls a gun from under the pillow and shoots you in the head! 💀"
            elif selected_prostitute.death_method == "knife":
                result = f"💀 BETRAYAL! {selected_prostitute.name} slits your throat with a knife while you're in bed! 💀"

            # Clear game session - player dies permanently
            if 'game_state' in session:
                session.pop('game_state', None)

            return render_template('wander_result.html', game_state=None, result=result)
        else:
            # Player survives and gets healing
            old_damage = game_state.damage
            game_state.damage = max(0, game_state.damage - selected_prostitute.healing_amount)
            healing = old_damage - game_state.damage

            result = f"😘 You spend a wild night with {selected_prostitute.name}! She heals you for {healing} damage. Feeling refreshed!"

        session['game_state'] = asdict(game_state)
        return render_template('wander_result.html', game_state=game_state, result=result)

    # GET request - show prostitute selection (combine default and employed)
    all_prostitutes = PROSTITUTES + game_state.employed_prostitutes
    return render_template('prostitutes.html', game_state=game_state, prostitutes=all_prostitutes)

@app.route('/pickup_loot/<npc_id>')
def pickup_loot(npc_id):
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    # Simple loot system - give player some money
    loot_money = random.randint(50, 200)
    game_state.money += loot_money
    session['game_state'] = asdict(game_state)

    result = f"You search the body and find ${loot_money} in cash!"
    return render_template('wander_result.html', game_state=game_state, result=result)

@app.route('/talk_to_npc/<npc_id>')
def talk_to_npc(npc_id):
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    # Handle new NPCs
    if npc_id in NPCS:
        npc = NPCS[npc_id]
        dialogue = npc.dialogue
        npc_data = {
            'id': npc.id,
            'name': npc.name,
            'dialogue': dialogue,
            'description': npc.description,
            'special_ability': npc.special_ability
        }
    else:
        # Legacy NPC dialogue system
        dialogues = {
            'nox': "Nox says: 'Hey, I got some good info for you. The Squidies are planning something big.'",
            'raze': "Raze says: 'Word on the street is the cops are cracking down hard. Watch your back.'",
            'void': "Void says: 'Got some premium stuff if you're interested. Best prices in town.'",
            'whisper': "Whisper whispers: 'I heard the Squidies got a new shipment coming in. Big money involved.'"
        }
        dialogue = dialogues.get(npc_id, f"{npc_id.title()} says: 'Not much to say right now.'")
        npc_data = {'id': npc_id, 'name': npc_id.title(), 'dialogue': dialogue}

    return render_template('npc_interaction.html', game_state=game_state, npc=npc_data)

@app.route('/trade_with_npc/<npc_id>', methods=['GET', 'POST'])
def trade_with_npc(npc_id):
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Simple trade - give player some drugs for money
        if game_state.money >= 100:
            game_state.money -= 100
            game_state.drugs.weed += 2
            session['game_state'] = asdict(game_state)
            result = "You traded $100 for 2 units of weed!"
            return render_template('wander_result.html', game_state=game_state, result=result)
        else:
            result = "You don't have enough money to trade!"
            return render_template('wander_result.html', game_state=game_state, result=result)

    return render_template('npc_trade.html', game_state=game_state, npc={'id': npc_id, 'name': npc_id})

@app.route('/fight_npc/<npc_id>', methods=['POST'])
def fight_npc(npc_id):
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    # Handle new NPCs
    if npc_id in NPCS:
        npc = NPCS[npc_id]

        # Use NPC-specific win probability
        win_chance = random.random()
        if win_chance <= npc.win_probability:
            # Player wins - use NPC's reward range
            min_reward, max_reward = npc.reward_money
            reward = random.randint(min_reward, max_reward)
            game_state.money += reward

            # Use NPC's recruitment chance and amount
            recruit_chance = random.random()
            recruited = 0
            if recruit_chance <= npc.recruit_chance:
                min_recruits, max_recruits = npc.recruit_amount
                recruited = random.randint(min_recruits, max_recruits)
                game_state.members += recruited

            session['game_state'] = asdict(game_state)
            npc_name = npc.name
            if recruited > 0:
                result = f"You defeated {npc_name} and took ${reward} from them! {recruited} bystander(s) witnessed your victory and joined your gang!"
            else:
                result = f"You defeated {npc_name} and took ${reward} from them!"
        else:
            # Player loses - use NPC's damage range
            min_damage, max_damage = npc.damage_range
            damage = random.randint(min_damage, max_damage)
            died = game_state.take_damage(damage)
            if died:
                session['game_state'] = asdict(game_state)
                return redirect(url_for('game_over'))
            session['game_state'] = asdict(game_state)
            result = f"You lost the fight with {npc.name} and took {damage} damage!"
    else:
        # Legacy NPC fight logic
        win_chance = random.random()
        if win_chance > 0.4:  # 60% win chance
            reward = random.randint(100, 300)
            game_state.money += reward

            # Recruitment chance after winning combat
            recruit_chance = random.random()
            recruited = 0
            if recruit_chance > 0.6:  # 40% chance to recruit from NPC fights
                recruited = random.randint(1, 2)
                game_state.members += recruited

            session['game_state'] = asdict(game_state)
            if recruited > 0:
                result = f"You defeated {npc_id} and took ${reward} from them! {recruited} bystander(s) witnessed your victory and joined your gang!"
            else:
                result = f"You defeated {npc_id} and took ${reward} from them!"
        else:
            damage = random.randint(1, 3)
            died = game_state.take_damage(damage)
            if died:
                session['game_state'] = asdict(game_state)
                return redirect(url_for('game_over'))
            session['game_state'] = asdict(game_state)
            result = f"You lost the fight with {npc_id} and took {damage} damage!"

    return render_template('wander_result.html', game_state=game_state, result=result)

@app.route('/look_at_npc/<npc_id>')
def look_at_npc(npc_id):
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    # Handle new NPCs
    if npc_id in NPCS:
        npc = NPCS[npc_id]
        description = npc.description
        npc_data = {
            'id': npc.id,
            'name': npc.name,
            'description': description,
            'special_ability': npc.special_ability
        }
    else:
        # Legacy NPC descriptions
        descriptions = {
            'eric': "Eric looks like a seasoned street veteran. He's got tattoos covering his arms and a scar across his cheek.",
            'steve': "Steve appears to be a shady businessman type. He's well-dressed but has that criminal glint in his eye.",
            'dealer': "This dealer looks nervous but professional. He's got that twitchy energy common in his line of work.",
            'informant': "The informant is shifty-eyed and constantly looking over his shoulder. He seems paranoid but knowledgeable."
        }
        description = descriptions.get(npc_id, f"{npc_id.title()} looks like an ordinary person on the street.")
        npc_data = {'id': npc_id, 'name': npc_id.title(), 'description': description}

    return render_template('npc_interaction.html', game_state=game_state, npc=npc_data)

@app.route('/meet_contact', methods=['POST'])
def meet_contact():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    contact = request.form.get('contact')
    if contact == 'nox':
        game_state.flags.eric_met = True
        result = "You meet Nox! He gives you some useful information about the streets."
    elif contact == 'raze':
        game_state.flags.steve_met = True
        result = "You meet Raze! He offers to show you his special closet."
    else:
        result = "You meet someone, but they're not very helpful."

    session['game_state'] = asdict(game_state)
    return render_template('wander_result.html', game_state=game_state, result=result)

@app.route('/bank_transaction', methods=['POST'])
def bank_transaction():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    action = request.form.get('action')
    amount = int(request.form.get('amount', 0))

    if action == 'deposit':
        if game_state.money >= amount:
            game_state.money -= amount
            game_state.account += amount
            result = f"You deposited ${amount} into your savings account."
        else:
            result = "You don't have enough money to deposit that amount."
    elif action == 'withdraw':
        if game_state.account >= amount:
            game_state.account -= amount
            game_state.money += amount
            result = f"You withdrew ${amount} from your savings account."
        else:
            result = "You don't have enough money in your account to withdraw that amount."
    elif action == 'loan':
        if amount <= 10000:  # Max loan
            game_state.loan += amount
            game_state.money += amount
            result = f"You took out a loan for ${amount}. Interest will be charged daily."
        else:
            result = "Banks won't loan you that much money."
    elif action == 'pay_loan':
        if game_state.money >= amount:
            game_state.money -= amount
            game_state.loan = max(0, game_state.loan - amount)
            result = f"You paid ${amount} towards your loan."
        else:
            result = "You don't have enough money to pay that much towards your loan."
    else:
        result = "Invalid bank transaction."

    session['game_state'] = asdict(game_state)
    return render_template('wander_result.html', game_state=game_state, result=result)

@app.route('/picknsave_action', methods=['POST'])
def picknsave_action():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    action = request.form.get('action')

    if action == 'buy_id':
        if game_state.money >= 2000:
            game_state.money -= 2000
            game_state.flags.has_id = True
            result = "You bought a fake ID! This might help you in certain situations."
        else:
            result = "You don't have enough money for a fake ID."
    elif action == 'buy_info':
        if game_state.money >= 10000:
            game_state.money -= 10000
            result = "You bought information about the Squidies' operations. Very useful intelligence!"
        else:
            result = "You don't have enough money for that information."
    elif action == 'recruit':
        cost_per_member = 10000
        if game_state.money >= cost_per_member:
            game_state.money -= cost_per_member
            game_state.members += 1
            result = f"You recruited a new gang member! You now have {game_state.members} members."
        else:
            result = f"You need ${cost_per_member} to recruit a new member."
    else:
        result = "Invalid action at Pick n' Save."

    session['game_state'] = asdict(game_state)
    return render_template('wander_result.html', game_state=game_state, result=result)

@app.route('/fight_cops', methods=['POST'])
def fight_cops():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    action = request.form.get('action')

    if action == 'run':
        escape_chance = random.random()
        if escape_chance > 0.3:  # 70% chance to escape
            result = "You successfully escaped from the police!"
        else:
            # Got caught
            arrest_penalty = min(game_state.money, 500)
            game_state.money -= arrest_penalty
            damage = random.randint(1, 2)
            died = game_state.take_damage(damage)
            if died:
                session['game_state'] = asdict(game_state)
                return redirect(url_for('game_over'))
            result = f"You got caught! Lost ${arrest_penalty} and took {damage} damage."
    else:
        # Fight with weapon
        weapon = action  # 'shoot' parameter contains weapon type
        if weapon == 'shoot':
            weapon = 'pistol'  # Default

        # Check if player has the weapon
        if weapon == 'pistol' and not game_state.weapons.can_fight_with_pistol():
            result = "You don't have a pistol or bullets to fight with!"
        elif weapon == 'uzi' and (game_state.weapons.uzis <= 0 or game_state.weapons.bullets <= 1):
            result = "You don't have an Uzi or enough bullets to fight with!"
        elif weapon == 'grenade' and game_state.weapons.grenades <= 0:
            result = "You don't have any grenades to fight with!"
        elif weapon == 'missile_launcher' and (game_state.weapons.missile_launcher <= 0 or game_state.weapons.missiles <= 0):
            result = "You don't have a missile launcher or missiles to fight with!"
        elif weapon == 'knife' and not game_state.weapons.can_fight_with_knife():
            result = "You don't have a knife to fight with!"
        else:
            # Successful fight
            result = "You fought off the police and escaped! But this will have consequences..."
            # Consume ammo
            if weapon == 'pistol':
                game_state.weapons.bullets = max(0, game_state.weapons.bullets - 1)
            elif weapon == 'uzi':
                game_state.weapons.bullets = max(0, game_state.weapons.bullets - 2)
            elif weapon == 'grenade':
                game_state.weapons.grenades -= 1
            elif weapon == 'missile_launcher':
                game_state.weapons.missiles -= 1

    session['game_state'] = asdict(game_state)
    return render_template('wander_result.html', game_state=game_state, result=result)

@app.route('/bulk_purchase', methods=['POST'])
def bulk_purchase():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    drug_type = request.form.get('drug_type')
    quantity = int(request.form.get('quantity', 10))

    if quantity < 10:
        result = "Bulk purchase requires at least 10 units!"
        return render_template('wander_result.html', game_state=game_state, result=result)

    cost = GameLogic.calculate_trade_cost(drug_type, quantity, game_state, is_selling=False)
    bulk_discount = 0.8  # 20% discount for bulk
    discounted_cost = int(cost * bulk_discount)

    if game_state.can_afford(discounted_cost):
        game_state.spend_money(discounted_cost)
        game_state.drugs.modify_drug(drug_type, quantity)
        result = f"Bulk purchase! You bought {quantity} units of {drug_type} for ${discounted_cost} (20% discount applied)."
    else:
        result = f"You don't have enough money for this bulk purchase. It would cost ${discounted_cost}."

    session['game_state'] = asdict(game_state)
    return render_template('wander_result.html', game_state=game_state, result=result)

@app.route('/handle_encounter', methods=['POST'])
def handle_encounter():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    encounter_type = request.form.get('encounter_type')
    action = request.form.get('action')

    import random

    if encounter_type == 'squidies':
        if action == 'fight':
            # Start detailed MUD-style combat
            combat_id = f"combat_{random.randint(1000, 9999)}"
            enemy_type = "Squidie Gang Member"
            enemy_health = 8
            enemy_count = 1

            # Initialize combat log
            fight_log = [
                "⚔️ COMBAT BEGINS ⚔️",
                f"You encounter a {enemy_type}!",
                f"The {enemy_type} looks at you menacingly.",
                "What do you do?"
            ]

            # Store combat state in session
            session['active_combat'] = {
                'combat_id': combat_id,
                'enemy_type': enemy_type,
                'enemy_health': enemy_health,
                'enemy_count': enemy_count,
                'fight_log': fight_log,
                'player_turn': True
            }

            session['game_state'] = asdict(game_state)
            return render_template('mud_fight.html',
                                 game_state=game_state,
                                 fight_log=fight_log,
                                 combat_active=True,
                                 combat_id=combat_id,
                                 enemy_health=enemy_health,
                                 enemy_type=enemy_type,
                                 enemy_count=enemy_count)
        elif action == 'run':
            if random.random() > 0.3:
                result = "You successfully ran away!"
            else:
                damage = random.randint(1, 3)
                died = game_state.take_damage(damage)
                if died:
                    session['game_state'] = asdict(game_state)
                    return redirect(url_for('game_over'))
                result = f"You tried to run but got caught! Took {damage} damage."
        elif action == 'sneak':
            if random.random() > 0.4:
                result = "You sneaked past them successfully!"
            else:
                damage = random.randint(1, 2)
                died = game_state.take_damage(damage)
                if died:
                    session['game_state'] = asdict(game_state)
                    return redirect(url_for('game_over'))
                result = f"They spotted you! Took {damage} damage."

    elif encounter_type == 'baby_momma':
        if action == 'fight':
            result = "You can't fight your baby momma! She takes $200 in child support."
            game_state.money = max(0, game_state.money - 200)
        elif action == 'run':
            if random.random() > 0.2:
                result = "You ran away from your baby momma!"
            else:
                result = "She caught up! Pay $150 in child support."
                game_state.money = max(0, game_state.money - 150)
        elif action == 'sneak':
            result = "You hid until she left. Crisis averted!"

    elif encounter_type == 'discovery':
        if action == 'fight':  # Force entry
            if random.random() > 0.6:
                found_money = random.randint(200, 1000)
                game_state.money += found_money
                result = f"You broke in and found ${found_money}!"
            else:
                damage = random.randint(3, 6)
                died = game_state.take_damage(damage)
                if died:
                    session['game_state'] = asdict(game_state)
                    return redirect(url_for('game_over'))
                result = f"You broke in but triggered a trap! Took {damage} damage."
        elif action == 'run':  # Walk away
            result = "You decided not to risk it and walked away."
        elif action == 'sneak':  # Sneak in
            if random.random() > 0.3:
                found_money = random.randint(100, 500)
                game_state.money += found_money
                result = f"You sneaked in and found ${found_money}!"
            else:
                damage = random.randint(1, 3)
                died = game_state.take_damage(damage)
                if died:
                    session['game_state'] = asdict(game_state)
                    return redirect(url_for('game_over'))
                result = f"You got caught sneaking! Took {damage} damage."

    elif encounter_type == 'drug_deal':
        if action == 'fight':  # Intimidate
            if random.random() > 0.4:
                discount = random.randint(10, 30)
                result = f"You intimidated them! Got {discount}% discount on drugs."
                # Could implement discount logic here
            else:
                result = "They called your bluff. Deal fell through."
        elif action == 'run':  # Decline deal
            result = "You declined the deal and walked away."
        elif action == 'sneak':  # Negotiate
            if random.random() > 0.5:
                result = "You negotiated a better deal! Got drugs at 80% price."
                # Could implement negotiation logic
            else:
                result = "Negotiation failed. Deal at normal price."

    elif encounter_type == 'potential_hooker':
        # Select a random hooker for this encounter
        selected_hooker = random.choice(POTENTIAL_HOOKERS)
        hooker_name = selected_hooker.name
        if action == 'fight':  # Try to recruit
            # Store the selected hooker in session for recruitment
            session['current_hooker'] = hooker_name
            # Redirect to recruitment page
            return redirect(url_for('recruit_hooker', hooker_name=hooker_name))
        elif action == 'run':  # Walk away
            result = "You decided not to get involved and walked away."
        elif action == 'sneak':  # Offer help
            result = "She seems wary but opens up a bit. Maybe you could help her?"
        elif action == 'trade':  # Offer money/drugs
            if random.random() > 0.6:
                result = f"You offered {hooker_name} some help and she accepted! She's now working for you."
                # Add to employed prostitutes
                employed_prostitute = Prostitute(
                    name=selected_hooker.name,
                    price=selected_hooker.stats['price'],
                    description=f"{selected_hooker.description} (Employed by you)",
                    risk_level=selected_hooker.stats['risk_level'],
                    healing_amount=selected_hooker.stats['healing_amount'],
                    death_risk=selected_hooker.stats['death_risk'],
                    death_method=selected_hooker.stats['death_method']
                )
                game_state.employed_prostitutes.append(employed_prostitute)
            else:
                result = f"{hooker_name} wasn't interested in your offer and walked away."

    elif encounter_type == 'squidies':
        if action == 'trade':  # Try to bribe them
            bribe_amount = min(game_state.money, random.randint(100, 500))
            if random.random() > 0.7:  # 30% success chance
                game_state.money -= bribe_amount
                result = f"You bribed the Squidies with ${bribe_amount} and they let you pass!"
            else:
                game_state.money -= bribe_amount
                result = f"You tried to bribe them with ${bribe_amount} but they took your money and attacked anyway!"
                damage = random.randint(2, 6)
                died = game_state.take_damage(damage)
                if died:
                    session['game_state'] = asdict(game_state)
                    return redirect(url_for('game_over'))
                result += f" You took {damage} damage."

    elif encounter_type == 'baby_momma':
        if action == 'trade':  # Pay child support
            payment = min(game_state.money, random.randint(100, 300))
            game_state.money -= payment
            result = f"You paid ${payment} in child support. She seems satisfied for now."

    elif encounter_type == 'discovery':
        if action == 'trade':  # Buy information about the discovery
            info_cost = random.randint(50, 150)
            if game_state.can_afford(info_cost):
                game_state.money -= info_cost
                if random.random() > 0.5:
                    found_money = random.randint(300, 800)
                    game_state.money += found_money
                    result = f"You bought information for ${info_cost} and discovered ${found_money} inside!"
                else:
                    result = f"You bought information for ${info_cost} but found nothing of value."
            else:
                result = f"You need at least ${info_cost} to buy information about this discovery."

    elif encounter_type == 'drug_deal':
        if action == 'trade':  # Make the deal
            deal_chance = random.random()
            if deal_chance > 0.8:  # 20% chance of getting ripped off
                if game_state.money >= 200:
                    game_state.money -= 200
                    result = "You got ripped off! Paid $200 for fake drugs."
                else:
                    result = "They tried to rip you off but you didn't have enough money."
            elif deal_chance > 0.4:  # 40% chance of good deal
                drug_types = ['weed', 'crack']
                drug = random.choice(drug_types)
                amount = random.randint(3, 8)
                game_state.drugs.modify_drug(drug, amount)
                result = f"Great deal! You got {amount} units of {drug} for $100."
                game_state.money -= 100
            else:  # 40% chance of average deal
                drug_types = ['weed', 'crack', 'coke']
                drug = random.choice(drug_types)
                amount = random.randint(1, 3)
                game_state.drugs.modify_drug(drug, amount)
                result = f"Fair deal. You got {amount} units of {drug} for $150."
                game_state.money -= 150

    session['game_state'] = asdict(game_state)
    return render_template('wander_result.html', game_state=game_state, result=result)

@app.route('/process_fight_action', methods=['POST'])
def process_fight_action():
    game_state = get_game_state()
    if not game_state:
        return redirect(url_for('index'))

    combat_id = request.form.get('combat_id')
    action = request.form.get('action')
    weapon = request.form.get('weapon', 'knife')

    # Get combat state from session
    active_combat = session.get('active_combat', {})
    if not active_combat or active_combat.get('combat_id') != combat_id:
        return redirect(url_for('alleyway'))

    fight_log = active_combat['fight_log']
    enemy_health = active_combat['enemy_health']
    enemy_type = active_combat['enemy_type']

    import random

    if action == 'attack':
        # Player attacks
        damage = calculate_weapon_damage(weapon, game_state)
        enemy_health -= damage

        # Generate gory attack description
        attacker_name = "You"
        defender_name = enemy_type
        gory_description = GameLogic.get_gory_attack_description(attacker_name, defender_name, weapon, damage)
        fight_log.append(f"⚔️ {gory_description}")

        if enemy_health > 0:
            fight_log.append(f"The {enemy_type} has {enemy_health} health remaining.")
        else:
            fight_log.append(f"The {enemy_type} collapses in a bloody heap!")

        if enemy_health <= 0:
            # Victory!
            fight_log.append(f"💀 You defeated the {enemy_type}!")
            reward = random.randint(100, 500)
            game_state.money += reward
            fight_log.append(f"You loot ${reward} from the body.")

            # Recruitment chance
            recruit_chance = random.random()
            recruited = 0
            if recruit_chance > 0.7:
                recruited = random.randint(1, 3)
                game_state.members += recruited
                fight_log.append(f"{recruited} bystander(s) witness your victory and join your gang!")

            # Clean up combat
            session.pop('active_combat', None)
            session['game_state'] = asdict(game_state)

            return render_template('mud_fight.html',
                                 game_state=game_state,
                                 fight_log=fight_log,
                                 combat_active=False,
                                 enemy_health=0,
                                 enemy_type=enemy_type,
                                 enemy_count=1)

        # Enemy counterattacks
        enemy_damage = random.randint(1, 4)
        died = game_state.take_damage(enemy_damage)

        # Generate gory enemy attack description
        enemy_gory_description = GameLogic.get_gory_attack_description(enemy_type, "You", "pistol", enemy_damage)
        fight_log.append(f"🔥 {enemy_gory_description}")

        if died:
            fight_log.append("💀 You have been defeated! 💀")
            session['game_state'] = asdict(game_state)
            session.pop('active_combat', None)
            return redirect(url_for('game_over'))

        fight_log.append("What do you do next?")

    elif action == 'defend':
        fight_log.append("🛡️ You take a defensive stance!")
        # Reduced enemy damage
        enemy_damage = max(1, random.randint(1, 4) - 2)
        died = game_state.take_damage(enemy_damage)
        fight_log.append(f"🔥 The {enemy_type} attacks but you block most of it! You take {enemy_damage} damage.")

        if died:
            fight_log.append("💀 You have been defeated! 💀")
            session['game_state'] = asdict(game_state)
            session.pop('active_combat', None)
            return redirect(url_for('game_over'))

        fight_log.append("What do you do next?")

    elif action == 'flee':
        if random.random() > 0.4:
            fight_log.append("🏃 You successfully flee from combat!")
            session.pop('active_combat', None)
            session['game_state'] = asdict(game_state)
            return render_template('mud_fight.html',
                                 game_state=game_state,
                                 fight_log=fight_log,
                                 combat_active=False,
                                 enemy_health=enemy_health,
                                 enemy_type=enemy_type,
                                 enemy_count=1)
        else:
            fight_log.append("🏃 You try to flee but the enemy blocks your escape!")
            enemy_damage = random.randint(2, 5)
            died = game_state.take_damage(enemy_damage)
            fight_log.append(f"🔥 The {enemy_type} strikes you for {enemy_damage} damage!")

            if died:
                fight_log.append("💀 You have been defeated! 💀")
                session['game_state'] = asdict(game_state)
                session.pop('active_combat', None)
                return redirect(url_for('game_over'))

            fight_log.append("What do you do next?")

    # Update combat state
    active_combat['fight_log'] = fight_log
    active_combat['enemy_health'] = enemy_health
    session['active_combat'] = active_combat
    session['game_state'] = asdict(game_state)

    return render_template('mud_fight.html',
                         game_state=game_state,
                         fight_log=fight_log,
                         combat_active=True,
                         combat_id=combat_id,
                         enemy_health=enemy_health,
                         enemy_type=enemy_type,
                         enemy_count=1)

def calculate_weapon_damage(weapon, game_state):
    """Calculate damage for a weapon in combat"""
    import random

    damage_ranges = {
        'pistol': (2, 8),
        'uzi': (3, 12),
        'grenade': (5, 20),
        'missile_launcher': (10, 50),
        'knife': (1, 5)
    }

    if weapon not in damage_ranges:
        weapon = 'knife'

    min_dmg, max_dmg = damage_ranges[weapon]

    # Check weapon availability and consume ammo
    if weapon == 'pistol':
        if not game_state.weapons.can_fight_with_pistol():
            return 0
        game_state.weapons.bullets -= 1
    elif weapon == 'uzi':
        if game_state.weapons.uzis <= 0 or game_state.weapons.bullets <= 1:
            return 0
        game_state.weapons.bullets -= 2
    elif weapon == 'grenade':
        if game_state.weapons.grenades <= 0:
            return 0
        game_state.weapons.grenades -= 1
    elif weapon == 'missile_launcher':
        if game_state.weapons.missile_launcher <= 0 or game_state.weapons.missiles <= 0:
            return 0
        game_state.weapons.missiles -= 1
    # Knife doesn't consume ammo

    return random.randint(min_dmg, max_dmg)

# Helper function
def get_game_state():
    if 'game_state' in session:
        data = session['game_state']
        # Properly reconstruct nested dataclasses from session dict
        game_state = GameState(**data)
        # Reconstruct nested dataclasses
        if isinstance(game_state.drugs, dict):
            game_state.drugs = DrugInventory(**game_state.drugs)
        if isinstance(game_state.weapons, dict):
            game_state.weapons = WeaponInventory(**game_state.weapons)
        if isinstance(game_state.flags, dict):
            game_state.flags = GameFlags(**game_state.flags)
        # Reconstruct employed prostitutes list
        if isinstance(game_state.employed_prostitutes, list):
            reconstructed_prostitutes = []
            for prostitute_data in game_state.employed_prostitutes:
                if isinstance(prostitute_data, dict):
                    reconstructed_prostitutes.append(Prostitute(**prostitute_data))
                else:
                    reconstructed_prostitutes.append(prostitute_data)
            game_state.employed_prostitutes = reconstructed_prostitutes
        return game_state
    return None

# Global player tracking
players_in_rooms = {}  # room -> {player_id: player_data}
active_pvp_fights = {}  # room -> current_fight_data

# NPC Data Structure
@dataclass
class NPC:
    id: str
    name: str
    description: str
    dialogue: str
    health: int
    damage_range: Tuple[int, int]
    win_probability: float
    reward_money: Tuple[int, int]
    recruit_chance: float
    recruit_amount: Tuple[int, int]
    special_ability: str = ""
    sells_drugs: bool = False
    drug_price_modifier: float = 1.0  # 1.0 = normal price, 0.8 = 20% discount, 1.5 = 50% markup
    robbery_chance: float = 0.0  # Chance NPC will try to rob player instead of buying
    personality: str = "neutral"  # For template compatibility
    drugs: DrugInventory = None  # For template compatibility

    def __post_init__(self):
        if self.drugs is None:
            # Initialize with random drug amounts for NPCs that sell drugs
            if self.sells_drugs:
                self.drugs = DrugInventory(
                    weed=random.randint(0, 10),
                    crack=random.randint(0, 5),
                    coke=random.randint(0, 3),
                    ice=random.randint(0, 2),
                    percs=random.randint(0, 1),
                    pixie_dust=random.randint(0, 1)
                )
            else:
                self.drugs = DrugInventory()  # Empty inventory

# New NPCs - 5 total, first one is strong, others randomized but weaker
NPCS = {
    # Strong NPC (first one)
    'scarface': NPC(
        id='scarface',
        name='Scarface Tony',
        description='A massive, scarred gangster with gold chains and a reputation that precedes him. His face tells stories of countless brutal fights.',
        dialogue='"You lookin\' at me? You got some nerve walkin\' up to Scarface Tony like that. What do you want, punk?"',
        health=25,
        damage_range=(8, 15),
        win_probability=0.85,
        reward_money=(500, 1000),
        recruit_chance=0.8,
        recruit_amount=(3, 6),
        special_ability="intimidation",
        sells_drugs=True,
        drug_price_modifier=0.7,  # 30% discount - good deal
        robbery_chance=0.0  # Won't try to rob
    ),

    # Weaker NPCs (randomized attributes)
    'big_mama': NPC(
        id='big_mama',
        name='Big Mama Jenkins',
        description='A large, imposing woman with a no-nonsense attitude. She runs the local gambling dens and knows everyone\'s secrets.',
        dialogue='"Well, well, what do we have here? Another street rat thinkin\' they can make it big. You got the guts, kid?"',
        health=12,
        damage_range=(3, 8),
        win_probability=0.6,
        reward_money=(150, 300),
        recruit_chance=0.5,
        recruit_amount=(1, 3),
        special_ability="information",
        sells_drugs=True,
        drug_price_modifier=1.3,  # 30% markup - bad deal
        robbery_chance=0.2  # 20% chance to rob
    ),

    'slick_vic': NPC(
        id='slick_vic',
        name='Slick Vic Malone',
        description='A smooth-talking con artist with a silver tongue and quick fingers. He\'s always got an angle and a backup plan.',
        dialogue='"Hey there, friend! You look like someone who appreciates the finer things in life. Care to make a little... arrangement?"',
        health=10,
        damage_range=(2, 6),
        win_probability=0.55,
        reward_money=(100, 250),
        recruit_chance=0.4,
        recruit_amount=(1, 2),
        special_ability="negotiation",
        sells_drugs=True,
        drug_price_modifier=0.8,  # 20% discount - decent deal
        robbery_chance=0.15  # 15% chance to rob
    ),

    'mad_dog': NPC(
        id='mad_dog',
        name='Mad Dog Riley',
        description='A wild-eyed, unpredictable fighter with a hair-trigger temper. His nickname says it all - he\'s completely unhinged.',
        dialogue='"GRRR! You talkin\' to me?! I\'ll tear your head off and spit down your neck! What do you want?!"',
        health=15,
        damage_range=(4, 10),
        win_probability=0.65,
        reward_money=(200, 400),
        recruit_chance=0.6,
        recruit_amount=(2, 4),
        special_ability="ferocity",
        sells_drugs=True,
        drug_price_modifier=1.5,  # 50% markup - terrible deal
        robbery_chance=0.35  # 35% chance to rob
    ),

    'shadow': NPC(
        id='shadow',
        name='The Shadow',
        description='A mysterious figure who moves like a ghost through the streets. No one knows his real name or background.',
        dialogue='"... (silence) ... You shouldn\'t have seen me. But now that you have, what will you do about it?"',
        health=8,
        damage_range=(1, 5),
        win_probability=0.5,
        reward_money=(80, 200),
        recruit_chance=0.3,
        recruit_amount=(1, 2),
        special_ability="stealth",
        sells_drugs=False,  # Doesn't sell drugs
        drug_price_modifier=1.0,
        robbery_chance=0.25  # 25% chance to rob
    ),

    # Additional 5 new NPCs with random attributes
    'blade_master': NPC(
        id='blade_master',
        name='Blade Master Chen',
        description='A legendary knife fighter from the East, his blade work is poetry in motion. He claims to have studied under ancient masters.',
        dialogue='"My blade sings the song of death. Will you dance with me, or shall I play a solo?"',
        health=18,
        damage_range=(6, 12),
        win_probability=0.75,
        reward_money=(300, 600),
        recruit_chance=0.7,
        recruit_amount=(2, 5),
        special_ability="precision",
        sells_drugs=False,
        drug_price_modifier=1.0,
        robbery_chance=0.1
    ),

    'cyber_punk': NPC(
        id='cyber_punk',
        name='Cyber Punk Zero',
        description='A heavily augmented street samurai with glowing cybernetic implants and a attitude to match. Tech meets toughness.',
        dialogue='"01010111 01101000 01100001 01110100 00100111 01110011 00100000 01111001 01101111 01110101 01110010 00100000 01110000 01110010 01101111 01100010 01101100 01100101 01101101 00111111"',
        health=22,
        damage_range=(7, 14),
        win_probability=0.8,
        reward_money=(400, 800),
        recruit_chance=0.6,
        recruit_amount=(1, 4),
        special_ability="hacking",
        sells_drugs=True,
        drug_price_modifier=0.9,
        robbery_chance=0.05
    ),

    'witch_doctor': NPC(
        id='witch_doctor',
        name='Mama Voodoo',
        description='A mysterious shaman with tribal tattoos and pouches of strange herbs. Her eyes seem to pierce your soul.',
        dialogue='"The spirits whisper your name to me. They say you carry great darkness... but also great potential."',
        health=14,
        damage_range=(3, 9),
        win_probability=0.6,
        reward_money=(200, 350),
        recruit_chance=0.5,
        recruit_amount=(1, 3),
        special_ability="healing",
        sells_drugs=True,
        drug_price_modifier=1.2,
        robbery_chance=0.15
    ),

    'demolition_man': NPC(
        id='demolition_man',
        name='Boomer Kowalski',
        description='A grizzled explosives expert with burn scars and a collection of questionable fireworks. He smells like gunpowder.',
        dialogue='"Everything\'s got a weak point, kid. You just gotta know where to poke it with enough boom!"',
        health=20,
        damage_range=(5, 11),
        win_probability=0.7,
        reward_money=(250, 500),
        recruit_chance=0.4,
        recruit_amount=(1, 3),
        special_ability="explosives",
        sells_drugs=False,
        drug_price_modifier=1.0,
        robbery_chance=0.3
    ),

    'ghost_rider': NPC(
        id='ghost_rider',
        name='Phantom Rider',
        description='A spectral figure on a modified motorcycle, appearing and disappearing like smoke. No one knows where he came from.',
        dialogue='"The road calls to those with nowhere else to go. You hear it too, don\'t you?"',
        health=16,
        damage_range=(4, 10),
        win_probability=0.65,
        reward_money=(180, 400),
        recruit_chance=0.45,
        recruit_amount=(1, 2),
        special_ability="speed",
        sells_drugs=True,
        drug_price_modifier=1.1,
        robbery_chance=0.2
    )
}

# Prostitutes data
PROSTITUTES = [
    Prostitute(
        name="Candy",
        price=50,
        description="A sweet young thing with a smile that could melt your heart. Low risk, decent healing.",
        risk_level="low",
        healing_amount=2,
        death_risk=5.0,  # 5% chance of death
        death_method="aids"
    ),
    Prostitute(
        name="Raven",
        price=100,
        description="Mysterious goth chick with tattoos everywhere. Medium risk, good healing.",
        risk_level="medium",
        healing_amount=4,
        death_risk=15.0,  # 15% chance of death
        death_method="gun"
    ),
    Prostitute(
        name="Diamond",
        price=200,
        description="High-class escort with expensive tastes. High risk, excellent healing.",
        risk_level="high",
        healing_amount=6,
        death_risk=25.0,  # 25% chance of death
        death_method="knife"
    ),
    Prostitute(
        name="Jasmine",
        price=75,
        description="Exotic dancer with moves that could kill. Medium risk, solid healing.",
        risk_level="medium",
        healing_amount=3,
        death_risk=12.0,  # 12% chance of death
        death_method="aids"
    ),
    Prostitute(
        name="Vixen",
        price=150,
        description="Wild redhead with a temper. High risk, great healing.",
        risk_level="high",
        healing_amount=5,
        death_risk=20.0,  # 20% chance of death
        death_method="gun"
    )
]

# Potential Hookers data - can be recruited by giving them drugs/money
POTENTIAL_HOOKERS = [
    PotentialHooker(
        name="Lola",
        description="A desperate young woman down on her luck. She's willing to work for some drugs and a little cash to get back on her feet.",
        recruitment_cost_drugs={'weed': 5, 'crack': 2},
        recruitment_cost_money=100,
        stats={
            'price': 80,
            'risk_level': 'medium',
            'healing_amount': 3,
            'death_risk': 10.0,
            'death_method': 'aids'
        }
    ),
    PotentialHooker(
        name="Trixie",
        description="A street-smart hustler who's fallen on hard times. She needs some coke and money to pay off her debts.",
        recruitment_cost_drugs={'coke': 1},
        recruitment_cost_money=200,
        stats={
            'price': 120,
            'risk_level': 'high',
            'healing_amount': 5,
            'death_risk': 18.0,
            'death_method': 'gun'
        }
    ),
    PotentialHooker(
        name="Ginger",
        description="A fiery redhead with a temper and a drug habit. She'll work for some ice and cash.",
        recruitment_cost_drugs={'ice': 3},
        recruitment_cost_money=150,
        stats={
            'price': 100,
            'risk_level': 'medium',
            'healing_amount': 4,
            'death_risk': 14.0,
            'death_method': 'knife'
        }
    ),
    PotentialHooker(
        name="Bambi",
        description="An innocent-looking girl who's new to the streets. She just needs some weed and a little money.",
        recruitment_cost_drugs={'weed': 8},
        recruitment_cost_money=50,
        stats={
            'price': 60,
            'risk_level': 'low',
            'healing_amount': 2,
            'death_risk': 8.0,
            'death_method': 'aids'
        }
    ),
    PotentialHooker(
        name="Sasha",
        description="A former model who's hit rock bottom. She needs percs and cash to numb the pain.",
        recruitment_cost_drugs={'percs': 2},
        recruitment_cost_money=300,
        stats={
            'price': 180,
            'risk_level': 'high',
            'healing_amount': 6,
            'death_risk': 22.0,
            'death_method': 'gun'
        }
    ),
    PotentialHooker(
        name="Nikki",
        description="A tough chick with a criminal past. She'll work for some crack and money.",
        recruitment_cost_drugs={'crack': 4},
        recruitment_cost_money=250,
        stats={
            'price': 140,
            'risk_level': 'high',
            'healing_amount': 4,
            'death_risk': 16.0,
            'death_method': 'knife'
        }
    )
]

# SocketIO events - only define if socketio is available
if socketio:
    @socketio.on('join')
    def handle_join(data):
        room = data['room']
        player_id = data.get('player_id', request.sid)
        player_name = data.get('player_name', 'Unknown Player')

        join_room(room)

        # Get game state to sync PVP stats with actual game state
        game_state = get_game_state()

        # Track player in room
        if room not in players_in_rooms:
            players_in_rooms[room] = {}
        players_in_rooms[room][player_id] = {
            'name': player_name,
            'sid': request.sid,
            'health': 100,  # Start with full health for PVP
            'max_health': 100,
            'weapons': {
                'pistol': game_state.weapons.pistols if game_state else 1,
                'bullets': game_state.weapons.bullets if game_state else 10,
                'uzi': game_state.weapons.uzis if game_state else 0,
                'grenade': game_state.weapons.grenades if game_state else 0,
                'knife': 1  # Everyone has a knife
            },
            'in_fight': False,
            'flask_session_id': session.get('game_state') is not None  # Track if they have an active game
        }

        # Notify room of player join
        emit('status', {'msg': f'{player_name} joined {room}'}, room=room, skip_sid=request.sid)

        # Send updated player list to all players in the room
        player_list = list(players_in_rooms[room].keys())
        emit('player_list', {'players': player_list}, room=room)

    @socketio.on('leave')
    def handle_leave(data):
        room = data.get('room')
        player_id = data.get('player_id', request.sid)

        if room in players_in_rooms and player_id in players_in_rooms[room]:
            player_name = players_in_rooms[room][player_id]['name']
            del players_in_rooms[room][player_id]

            # Clean up empty rooms
            if not players_in_rooms[room]:
                del players_in_rooms[room]

            emit('status', {'msg': f'{player_name} left {room}'}, room=room)
            emit('player_list', {'players': list(players_in_rooms.get(room, {}).keys())}, room=room)

        leave_room(room)

    @socketio.on('chat_message')
    def handle_chat_message(data):
        room = data['room']
        player_name = data.get('player_name', 'Unknown')
        message = data['message']
        emit('chat_message', {'player': player_name, 'message': message}, room=room)

    @socketio.on('get_player_list')
    def handle_get_player_list(data):
        room = data.get('room', 'city')
        if room in players_in_rooms:
            player_list = []
            for player_id, player_data in players_in_rooms[room].items():
                if player_id != request.sid:  # Don't include self
                    player_list.append({
                        'id': player_id,
                        'name': player_data['name'],
                        'in_fight': player_data.get('in_fight', False)
                    })
            emit('player_list', {'players': player_list})
        else:
            emit('player_list', {'players': []})

    @socketio.on('pvp_challenge')
    def handle_pvp_challenge(data):
        room = data['room']
        challenger_id = data.get('challenger_id', request.sid)
        target_id = data['target_id']

        # Check if PVP is allowed in this room (only alleyway rooms)
        alleyway_rooms = [
            'entrance', 'alley1', 'alley2', 'alley_fork', 'drug_den', 'crack_house_entrance',
            'crack_house_interior', 'crack_house_upstairs', 'back_alley', 'dead_end_alley',
            'service_entrance', 'restaurant_kitchen', 'restaurant_dining', 'alley_dead_end',
            'side_street', 'hidden_room', 'abandoned_lot', 'construction_site', 'burned_building',
            'building_interior', 'rooftop', 'rooftop_access', 'basement', 'sewer_entrance',
            'sewer_tunnel', 'underground_chamber', 'sewer_grate', 'sewer_maintenance_tunnel',
            'sewer_flooded_chamber', 'sewer_death_trap'
        ]

        if room not in alleyway_rooms:
            emit('pvp_response', {'success': False, 'message': 'PVP combat is only allowed in the dark alleyway!'})
            return

        if (room not in players_in_rooms or
            challenger_id not in players_in_rooms[room] or
            target_id not in players_in_rooms[room]):
            emit('pvp_response', {'success': False, 'message': 'Player not found in room'})
            return

        challenger = players_in_rooms[room][challenger_id]
        target = players_in_rooms[room][target_id]

        if challenger['in_fight'] or target['in_fight']:
            emit('pvp_response', {'success': False, 'message': 'One or both players are already in a fight'})
            return

        # Send challenge to target
        emit('pvp_challenge_received', {
            'challenger_id': challenger_id,
            'challenger_name': challenger['name'],
            'message': f'{challenger["name"]} challenges you to a fight!'
        }, room=room, skip_sid=challenger['sid'])

        # Confirm to challenger
        emit('pvp_response', {'success': True, 'message': f'Challenge sent to {target["name"]}'})

    @socketio.on('pvp_accept')
    def handle_pvp_accept(data):
        room = data['room']
        challenger_id = data['challenger_id']
        accepter_id = data.get('accepter_id', request.sid)

        if (room not in players_in_rooms or
            challenger_id not in players_in_rooms[room] or
            accepter_id not in players_in_rooms[room]):
            return

        challenger = players_in_rooms[room][challenger_id]
        accepter = players_in_rooms[room][accepter_id]

        if challenger['in_fight'] or accepter['in_fight']:
            return

        # Mark both players as in fight
        challenger['in_fight'] = True
        accepter['in_fight'] = True

        # Initialize fight
        fight_data = {
            'room': room,
            'player1': {'id': challenger_id, 'name': challenger['name'], 'health': challenger['health']},
            'player2': {'id': accepter_id, 'name': accepter['name'], 'health': accepter['health']},
            'current_turn': challenger_id,  # Challenger goes first
            'turn_count': 1,
            'fight_log': []
        }

        active_pvp_fights[room] = fight_data

        # Announce fight start
        emit('pvp_fight_start', {
            'message': f'⚔️ FIGHT START: {challenger["name"]} vs {accepter["name"]} ⚔️',
            'fight_data': fight_data
        }, room=room)

        # Start first turn
        emit('pvp_turn_start', {
            'current_player': challenger_id,
            'message': f"{challenger['name']}'s turn! Choose your action."
        }, room=room)

    @socketio.on('pvp_action')
    def handle_pvp_action(data):
        room = data['room']
        player_id = data.get('player_id', request.sid)
        action = data['action']  # 'attack', 'defend', 'use_item'
        weapon = data.get('weapon', 'pistol')

        if room not in active_pvp_fights:
            return

        fight = active_pvp_fights[room]

        # Verify it's the player's turn
        if fight['current_turn'] != player_id:
            emit('pvp_response', {'success': False, 'message': 'Not your turn!'})
            return

        current_player = fight['player1'] if player_id == fight['player1']['id'] else fight['player2']
        opponent = fight['player2'] if player_id == fight['player1']['id'] else fight['player1']

        # Process action
        if action == 'attack':
            damage = calculate_pvp_damage(weapon, players_in_rooms[room][player_id])
            opponent['health'] = max(0, opponent['health'] - damage)

            # Generate gory attack description
            attacker_name = current_player['name']
            defender_name = opponent['name']
            gory_description = GameLogic.get_gory_attack_description(attacker_name, defender_name, weapon, damage)
            fight['fight_log'].append(f"⚔️ {gory_description}")

            if opponent['health'] > 0:
                fight['fight_log'].append(f"{opponent['name']} has {opponent['health']} HP remaining.")
            else:
                fight['fight_log'].append(f"{opponent['name']} collapses in a bloody heap!")

            # Check for victory
            if opponent['health'] <= 0:
                winner = current_player
                loser = opponent

                # Mark players as not in fight
                players_in_rooms[room][winner['id']]['in_fight'] = False
                players_in_rooms[room][loser['id']]['in_fight'] = False

                # Handle game over for loser (similar to final gang war)
                loser_player_data = players_in_rooms[room][loser['id']]
                if loser_player_data.get('flask_session_id', False):
                    # Clear the loser's game session to end their game permanently
                    if 'game_state' in session:
                        session.pop('game_state', None)

                    # Emit defeat message to loser - redirect to defeat page like final battle
                    emit('game_over', {
                        'message': f'💀 You have been defeated by {winner["name"]}! Your gang has been wiped out. 💀',
                        'redirect_url': url_for('defeat')
                    }, room=loser['sid'])

                victory_message = f"💀 VICTORY: {winner['name']} defeats {loser['name']}! {loser['name']} is eliminated! 💀"
                fight['fight_log'].append(victory_message)

                emit('pvp_fight_end', {
                    'winner': winner['name'],
                    'loser': loser['name'],
                    'message': victory_message,
                    'fight_log': fight['fight_log']
                }, room=room)

                # Clean up fight
                del active_pvp_fights[room]
                return

        elif action == 'defend':
            message = f"🛡️ {current_player['name']} takes a defensive stance!"
            fight['fight_log'].append(message)

        # Switch turns
        fight['current_turn'] = opponent['id']
        fight['turn_count'] += 1

        # Broadcast turn result and next turn
        emit('pvp_turn_result', {
            'message': message,
            'fight_log': fight['fight_log'],
            'next_player': opponent['id'],
            'next_message': f"{opponent['name']}'s turn! Choose your action."
        }, room=room)

def calculate_pvp_damage(weapon, player_data):
    """Calculate damage for PVP combat"""
    import random

    base_damage = {
        'pistol': (8, 15),
        'uzi': (12, 20),
        'knife': (3, 8),
        'grenade': (20, 35)
    }

    if weapon not in base_damage:
        weapon = 'pistol'  # Default

    min_dmg, max_dmg = base_damage[weapon]

    # Check if player has the weapon and ammo
    weapons = player_data.get('weapons', {})

    # Validate weapon availability
    if weapon == 'pistol' and (weapons.get('pistol', 0) <= 0 or weapons.get('bullets', 0) <= 0):
        weapon = 'knife'  # Fallback to knife
        min_dmg, max_dmg = base_damage['knife']
    elif weapon == 'uzi' and (weapons.get('uzi', 0) <= 0 or weapons.get('bullets', 0) <= 1):
        weapon = 'pistol'  # Fallback to pistol
        min_dmg, max_dmg = base_damage['pistol']

    damage = random.randint(min_dmg, max_dmg)

    # Consume ammo
    if weapon == 'pistol':
        weapons['bullets'] = max(0, weapons.get('bullets', 0) - 1)
    elif weapon == 'uzi':
        weapons['bullets'] = max(0, weapons.get('bullets', 0) - 2)
    elif weapon == 'grenade':
        weapons['grenade'] = max(0, weapons.get('grenade', 0) - 1)

    return damage


if __name__ == '__main__':
    if socketio:
        socketio.run(app, host='0.0.0.0', port=5005, debug=True)
    else:
        # Run without SocketIO for bundled applications
        app.run(host='0.0.0.0', port=5005, debug=True)
