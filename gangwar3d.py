#!/usr/bin/env python3

"""
Gang War 3D - A 3D graphical remake of the text-based gang warfare game
Built with Panda3D, inspired by Stardew Valley gameplay in a dystopian setting
"""

from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import *
from direct.task import Task
from direct.actor.Actor import Actor
from panda3d.core import *
import sys
import random
import json
from dataclasses import dataclass, field
from typing import Dict, List

# Import game state classes from original app
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

@dataclass
class GameState:
    player_name: str = ""
    gang_name: str = ""
    money: int = 1000
    account: int = 0
    loan: int = 0
    members: int = 1
    squidies: int = 25
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

class GangWar3D(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        # Set window title
        props = WindowProperties()
        props.setTitle("Gang War 3D")
        self.win.requestProperties(props)

        # Initialize game state
        self.game_state = GameState()
        self.game_state.player_name = "Player"
        self.game_state.gang_name = "Your Gang"
        self.game_state.weapons.pistols = 1
        self.game_state.weapons.bullets = 10

        # Load NPCs
        self.load_npcs()

        # Set up camera
        self.camera.setPos(0, -20, 5)
        self.camera.lookAt(0, 0, 0)

        # Disable default mouse camera control
        self.disableMouse()

        # Set up lighting
        self.setup_lighting()

        # Create UI
        self.setup_ui()

        # Create current level
        self.current_level = None
        self.load_level("city")

        # Player character
        self.player = None
        self.create_player()

        # Input handling
        self.setup_input()

        # Game loop
        self.taskMgr.add(self.update, "update")

    def setup_lighting(self):
        """Set up basic lighting"""
        # Ambient light
        ambient_light = AmbientLight("ambient_light")
        ambient_light.setColor(Vec4(0.3, 0.3, 0.3, 1))
        ambient_light_np = self.render.attachNewNode(ambient_light)
        self.render.setLight(ambient_light_np)

        # Directional light (sun)
        directional_light = DirectionalLight("directional_light")
        directional_light.setColor(Vec4(0.8, 0.8, 0.8, 1))
        directional_light.setDirection(Vec3(-1, -1, -1))
        directional_light_np = self.render.attachNewNode(directional_light)
        self.render.setLight(directional_light_np)

    def setup_ui(self):
        """Set up user interface"""
        # Main HUD frame
        self.hud = DirectFrame(frameColor=(0, 0, 0, 0.5),
                              frameSize=(-1.3, 1.3, -0.9, 0.9),
                              pos=(0, 0, 0))

        # Player stats
        self.stats_text = OnscreenText(text=self.get_stats_text(),
                                      pos=(-1.2, 0.8),
                                      scale=0.05,
                                      align=TextNode.ALeft,
                                      fg=(1, 1, 1, 1),
                                      parent=self.hud)

        # Location text
        self.location_text = OnscreenText(text=f"Location: {self.game_state.current_location.title()}",
                                         pos=(0, 0.8),
                                         scale=0.06,
                                         fg=(1, 1, 0, 1),
                                         parent=self.hud)

        # Action buttons frame
        self.action_frame = DirectFrame(frameColor=(0.2, 0.2, 0.2, 0.8),
                                       frameSize=(-0.8, 0.8, -0.3, 0.3),
                                       pos=(0, 0, -0.7),
                                       parent=self.hud)

        # Initialize action buttons (will be populated based on location)
        self.action_buttons = []

        # Drug trading UI (hidden initially)
        self.drug_ui = DirectFrame(frameColor=(0.1, 0.1, 0.1, 0.9),
                                  frameSize=(-0.9, 0.9, -0.8, 0.8),
                                  pos=(0, 0, 0))
        self.drug_ui.hide()

        self.drug_title = OnscreenText(text="Drug Market",
                                      pos=(0, 0.7),
                                      scale=0.08,
                                      fg=(1, 1, 0, 1),
                                      parent=self.drug_ui)

        # Drug list
        self.drug_list_text = OnscreenText(text=self.get_drug_list_text(),
                                          pos=(-0.8, 0.5),
                                          scale=0.04,
                                          align=TextNode.ALeft,
                                          fg=(1, 1, 1, 1),
                                          parent=self.drug_ui)

        # Trading buttons
        self.buy_btn = DirectButton(text="Buy",
                                   scale=0.05,
                                   pos=(-0.3, 0, 0.2),
                                   parent=self.drug_ui,
                                   command=self.show_buy_menu)

        self.sell_btn = DirectButton(text="Sell",
                                    scale=0.05,
                                    pos=(0.3, 0, 0.2),
                                    parent=self.drug_ui,
                                    command=self.show_sell_menu)

        self.close_drug_btn = DirectButton(text="Close",
                                          scale=0.05,
                                          pos=(0, 0, -0.6),
                                          parent=self.drug_ui,
                                          command=self.close_drug_ui)

        # Hide UI initially, show on key press
        self.hud.hide()

    def get_stats_text(self):
        """Get formatted stats text"""
        return f"""Player: {self.game_state.player_name}
Gang: {self.game_state.gang_name}
Money: ${self.game_state.money:,}
Day: {self.game_state.day}
Health: {self.game_state.health}/100
Lives: {self.game_state.lives}
Members: {self.game_state.members}
Steps: {self.game_state.steps}/{self.game_state.max_steps}"""

    def setup_input(self):
        """Set up input handling"""
        self.accept("escape", self.quit_game)
        self.accept("tab", self.toggle_ui)
        self.accept("w", self.move_player, ["forward"])
        self.accept("s", self.move_player, ["backward"])
        self.accept("a", self.move_player, ["left"])
        self.accept("d", self.move_player, ["right"])
        self.accept("w-repeat", self.move_player, ["forward"])
        self.accept("s-repeat", self.move_player, ["backward"])
        self.accept("a-repeat", self.move_player, ["left"])
        self.accept("d-repeat", self.move_player, ["right"])
        self.accept("e", self.interact)
        self.accept("i", self.show_inventory)

    def toggle_ui(self):
        """Toggle HUD visibility"""
        if self.hud.isHidden():
            self.hud.show()
            self.update_ui()
        else:
            self.hud.hide()

    def update_ui(self):
        """Update UI elements"""
        self.stats_text.setText(self.get_stats_text())
        self.location_text.setText(f"Location: {self.game_state.current_location.title()}")

    def create_player(self):
        """Create player character"""
        # Simple cube for now - replace with 3D model later
        self.player = self.loader.loadModel("models/box")
        self.player.setScale(0.5, 0.5, 1)
        self.player.setColor(0, 0.5, 1, 1)  # Blue player
        self.player.setPos(0, 0, 0.5)
        self.player.reparentTo(self.render)

    def move_player(self, direction):
        """Move player in given direction"""
        speed = 0.5
        pos = self.player.getPos()

        if direction == "forward":
            self.player.setY(pos.getY() + speed)
        elif direction == "backward":
            self.player.setY(pos.getY() - speed)
        elif direction == "left":
            self.player.setX(pos.getX() - speed)
        elif direction == "right":
            self.player.setX(pos.getX() + speed)

        # Update steps
        self.game_state.steps += 1
        if self.game_state.steps >= self.game_state.max_steps:
            self.game_state.day += 1
            self.game_state.steps = 0
            # Update drug prices daily
            self.update_drug_prices()

        self.update_ui()

    def update_drug_prices(self):
        """Update drug prices daily"""
        for drug in self.game_state.drug_prices:
            # Random fluctuation
            change = random.randint(-100, 100)
            self.game_state.drug_prices[drug] = max(50, self.game_state.drug_prices[drug] + change)

    def interact(self):
        """Handle interaction with objects/NPCs"""
        if self.game_state.current_location == "crackhouse":
            # Show drug trading UI
            self.drug_ui.show()
            self.drug_list_text.setText(self.get_drug_list_text())
        else:
            print("Interacting...")

    def show_inventory(self):
        """Show inventory screen"""
        print("Showing inventory...")

    def get_drug_list_text(self):
        """Get formatted drug list text"""
        text = "Available Drugs:\n\n"
        for drug, price in self.game_state.drug_prices.items():
            owned = getattr(self.game_state.drugs, drug)
            text += f"{drug.title()}: ${price:,} (You have: {owned})\n"
        return text

    def show_buy_menu(self):
        """Show drug buying menu"""
        self.drug_ui.hide()
        # For now, just show a message
        print("Buy menu - not implemented yet")

    def show_sell_menu(self):
        """Show drug selling menu"""
        self.drug_ui.hide()
        # For now, just show a message
        print("Sell menu - not implemented yet")

    def close_drug_ui(self):
        """Close drug trading UI"""
        self.drug_ui.hide()

    def load_level(self, location):
        """Load a level based on location"""
        # Clear current level
        if self.current_level:
            self.current_level.removeNode()

        self.game_state.current_location = location

        if location == "city":
            self.load_city_level()
        elif location == "crackhouse":
            self.load_crackhouse_level()
        elif location == "gunshack":
            self.load_gunshack_level()
        elif location == "bank":
            self.load_bank_level()
        elif location == "bar":
            self.load_bar_level()
        elif location == "alleyway":
            self.load_alleyway_level()
        elif location == "picknsave":
            self.load_picknsave_level()

        self.update_ui()

    def load_city_level(self):
        """Load the city level"""
        self.current_level = self.render.attachNewNode("city")

        # Create ground
        ground = self.loader.loadModel("models/box")
        ground.setScale(20, 20, 0.1)
        ground.setColor(0.3, 0.3, 0.3, 1)
        ground.setPos(0, 0, 0)
        ground.reparentTo(self.current_level)

        # Create buildings
        buildings = [
            {"name": "Crackhouse", "pos": (-5, 5, 1), "color": (0.8, 0.2, 0.2)},
            {"name": "Gun Shack", "pos": (5, 5, 1), "color": (0.2, 0.8, 0.2)},
            {"name": "Bar", "pos": (-5, -5, 1), "color": (0.8, 0.8, 0.2)},
            {"name": "Bank", "pos": (5, -5, 1), "color": (0.2, 0.2, 0.8)},
            {"name": "Pick n Save", "pos": (0, 0, 1), "color": (0.5, 0.5, 0.5)},
        ]

        for building in buildings:
            b = self.loader.loadModel("models/box")
            b.setScale(2, 2, 2)
            b.setColor(*building["color"])
            b.setPos(*building["pos"])
            b.reparentTo(self.current_level)

            # Add label
            label = OnscreenText(text=building["name"],
                               pos=(building["pos"][0], building["pos"][1] + 0.5),
                               scale=0.05,
                               fg=(1, 1, 1, 1))
            label.reparentTo(self.current_level)

    def load_crackhouse_level(self):
        """Load crackhouse level"""
        self.current_level = self.render.attachNewNode("crackhouse")

        # Create ground
        ground = self.loader.loadModel("models/box")
        ground.setScale(15, 15, 0.1)
        ground.setColor(0.4, 0.2, 0.2, 1)
        ground.setPos(0, 0, 0)
        ground.reparentTo(self.current_level)

        # Add some details
        counter = self.loader.loadModel("models/box")
        counter.setScale(5, 1, 1)
        counter.setColor(0.6, 0.4, 0.2, 1)
        counter.setPos(0, 3, 0.5)
        counter.reparentTo(self.current_level)

        # Back to city button (temporary)
        back_btn = self.loader.loadModel("models/box")
        back_btn.setScale(1, 1, 1)
        back_btn.setColor(1, 1, 0, 1)
        back_btn.setPos(-6, -6, 0.5)
        back_btn.reparentTo(self.current_level)

    def load_gunshack_level(self):
        """Load gunshack level"""
        self.current_level = self.render.attachNewNode("gunshack")

        # Similar to crackhouse but different colors
        ground = self.loader.loadModel("models/box")
        ground.setScale(15, 15, 0.1)
        ground.setColor(0.2, 0.4, 0.2, 1)
        ground.setPos(0, 0, 0)
        ground.reparentTo(self.current_level)

        # Back to city button
        back_btn = self.loader.loadModel("models/box")
        back_btn.setScale(1, 1, 1)
        back_btn.setColor(1, 1, 0, 1)
        back_btn.setPos(-6, -6, 0.5)
        back_btn.reparentTo(self.current_level)

    def load_bank_level(self):
        """Load bank level"""
        self.current_level = self.render.attachNewNode("bank")

        ground = self.loader.loadModel("models/box")
        ground.setScale(15, 15, 0.1)
        ground.setColor(0.2, 0.2, 0.4, 1)
        ground.setPos(0, 0, 0)
        ground.reparentTo(self.current_level)

        # Back to city button
        back_btn = self.loader.loadModel("models/box")
        back_btn.setScale(1, 1, 1)
        back_btn.setColor(1, 1, 0, 1)
        back_btn.setPos(-6, -6, 0.5)
        back_btn.reparentTo(self.current_level)

    def load_bar_level(self):
        """Load bar level"""
        self.current_level = self.render.attachNewNode("bar")

        ground = self.loader.loadModel("models/box")
        ground.setScale(15, 15, 0.1)
        ground.setColor(0.4, 0.4, 0.2, 1)
        ground.setPos(0, 0, 0)
        ground.reparentTo(self.current_level)

        # Back to city button
        back_btn = self.loader.loadModel("models/box")
        back_btn.setScale(1, 1, 1)
        back_btn.setColor(1, 1, 0, 1)
        back_btn.setPos(-6, -6, 0.5)
        back_btn.reparentTo(self.current_level)

    def load_alleyway_level(self):
        """Load alleyway level"""
        self.current_level = self.render.attachNewNode("alleyway")

        ground = self.loader.loadModel("models/box")
        ground.setScale(15, 15, 0.1)
        ground.setColor(0.1, 0.1, 0.1, 1)
        ground.setPos(0, 0, 0)
        ground.reparentTo(self.current_level)

        # Back to city button
        back_btn = self.loader.loadModel("models/box")
        back_btn.setScale(1, 1, 1)
        back_btn.setColor(1, 1, 0, 1)
        back_btn.setPos(-6, -6, 0.5)
        back_btn.reparentTo(self.current_level)

    def load_picknsave_level(self):
        """Load pick n save level"""
        self.current_level = self.render.attachNewNode("picknsave")

        ground = self.loader.loadModel("models/box")
        ground.setScale(15, 15, 0.1)
        ground.setColor(0.3, 0.3, 0.3, 1)
        ground.setPos(0, 0, 0)
        ground.reparentTo(self.current_level)

        # Back to city button
        back_btn = self.loader.loadModel("models/box")
        back_btn.setScale(1, 1, 1)
        back_btn.setColor(1, 1, 0, 1)
        back_btn.setPos(-6, -6, 0.5)
        back_btn.reparentTo(self.current_level)

    def load_npcs(self):
        """Load NPC data"""
        try:
            with open('npcs.json', 'r') as f:
                self.npcs_data = json.load(f)
        except FileNotFoundError:
            self.npcs_data = {}

    def update(self, task):
        """Main update loop"""
        dt = globalClock.getDt()

        # Check for level transitions based on player position
        if self.game_state.current_location == "city":
            player_pos = self.player.getPos()
            # Check if player is near buildings
            if -6 < player_pos.getX() < -4 and 4 < player_pos.getY() < 6:
                self.load_level("crackhouse")
                self.player.setPos(0, 0, 0.5)
            elif 4 < player_pos.getX() < 6 and 4 < player_pos.getY() < 6:
                self.load_level("gunshack")
                self.player.setPos(0, 0, 0.5)
            elif -6 < player_pos.getX() < -4 and -6 < player_pos.getY() < -4:
                self.load_level("bar")
                self.player.setPos(0, 0, 0.5)
            elif 4 < player_pos.getX() < 6 and -6 < player_pos.getY() < -4:
                self.load_level("bank")
                self.player.setPos(0, 0, 0.5)
            elif -1 < player_pos.getX() < 1 and -1 < player_pos.getY() < 1:
                self.load_level("picknsave")
                self.player.setPos(0, 0, 0.5)

        # Check for back to city (yellow cube)
        elif self.game_state.current_location != "city":
            player_pos = self.player.getPos()
            if -7 < player_pos.getX() < -5 and -7 < player_pos.getY() < -5:
                self.load_level("city")
                self.player.setPos(0, 0, 0.5)

        return Task.cont

    def quit_game(self):
        """Quit the game"""
        sys.exit()

if __name__ == "__main__":
    game = GangWar3D()
    game.run()
