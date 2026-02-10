#!/usr/bin/env python3
"""
Gangwar Game - Android Mobile App
A beautiful mobile UI for the Gangwar text-based RPG
"""

import os
import sys
import threading
import time
import json
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import game logic
from app import get_game_state, save_game_state, GameState

# Set window size for mobile-like experience
Window.size = (400, 700)

class GameScreen(Screen):
    """Base screen class for game screens"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_state = get_game_state()
        self.layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))
        self.add_widget(self.layout)

    def update_game_state(self):
        """Update the game state display"""
        self.game_state = get_game_state()

    def create_header(self):
        """Create a header with game stats"""
        header = BoxLayout(size_hint_y=0.15, padding=dp(5), spacing=dp(5))

        # Player info
        player_box = BoxLayout(orientation='vertical', size_hint_x=0.4)
        player_box.add_widget(Label(text=f"[b]{self.game_state.player_name}[/b]", markup=True, font_size=dp(16)))
        player_box.add_widget(Label(text=f"Gang: {self.game_state.gang_name}", font_size=dp(12)))
        player_box.add_widget(Label(text=f"Day: {self.game_state.day}", font_size=dp(12)))
        header.add_widget(player_box)

        # Stats
        stats_box = BoxLayout(orientation='vertical', size_hint_x=0.6)
        stats_layout = GridLayout(cols=2, size_hint_y=1)
        stats_layout.add_widget(Label(text=f"Money: ${self.game_state.money:,}", font_size=dp(12)))
        stats_layout.add_widget(Label(text=f"Health: {self.game_state.health}", font_size=dp(12)))
        stats_layout.add_widget(Label(text=f"Members: {self.game_state.members}", font_size=dp(12)))
        stats_layout.add_widget(Label(text=f"Lives: {self.game_state.lives}", font_size=dp(12)))
        stats_box.add_widget(stats_layout)
        header.add_widget(stats_box)

        return header

class CityScreen(GameScreen):
    """City hub screen"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'city'
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()

        # Header
        self.layout.add_widget(self.create_header())

        # Location title
        title = Label(text="[b]CITY HUB[/b]", markup=True, font_size=dp(20), size_hint_y=0.1)
        self.layout.add_widget(title)

        # Navigation buttons
        nav_grid = GridLayout(cols=2, size_hint_y=0.6, spacing=dp(10), padding=dp(10))

        locations = [
            ("Crackhouse", "crackhouse", "#8B4513"),
            ("Gun Shack", "gunshack", "#2F4F4F"),
            ("Bank", "bank", "#FFD700"),
            ("Bar", "bar", "#8B0000"),
            ("Pick n Save", "picknsave", "#32CD32"),
            ("Alleyway", "alleyway", "#696969"),
            ("Infobooth", "infobooth", "#4169E1"),
            ("Wander", "wander", "#DC143C"),
        ]

        for name, screen_name, color in locations:
            btn = Button(
                text=name,
                background_color=get_color_from_hex(color),
                font_size=dp(16),
                size_hint_y=0.2
            )
            btn.bind(on_press=lambda x, s=screen_name: self.go_to_location(s))
            nav_grid.add_widget(btn)

        self.layout.add_widget(nav_grid)

        # Action buttons
        action_box = BoxLayout(size_hint_y=0.15, spacing=dp(5))
        stats_btn = Button(text="Stats", background_color=get_color_from_hex("#9370DB"))
        stats_btn.bind(on_press=lambda x: self.go_to_location("stats"))
        action_box.add_widget(stats_btn)

        high_scores_btn = Button(text="High Scores", background_color=get_color_from_hex("#FF6347"))
        high_scores_btn.bind(on_press=lambda x: self.go_to_location("high_scores"))
        action_box.add_widget(high_scores_btn)

        self.layout.add_widget(action_box)

    def go_to_location(self, location):
        self.manager.current = location
        self.manager.get_screen(location).update_game_state()

class CrackhouseScreen(GameScreen):
    """Crackhouse screen for drug trading"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'crackhouse'
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()

        # Header
        self.layout.add_widget(self.create_header())

        title = Label(text="[b]BIG JOHNNY'S CRACK HOUSE[/b]", markup=True, font_size=dp(18), size_hint_y=0.1)
        self.layout.add_widget(title)

        # Drug prices display
        scroll = ScrollView(size_hint_y=0.4)
        drug_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(5), padding=dp(5))
        drug_grid.bind(minimum_height=drug_grid.setter('height'))

        for drug in ['weed', 'crack', 'coke', 'ice', 'percs', 'pixie_dust']:
            price = self.game_state.drug_prices.get(drug, 0)
            current_qty = getattr(self.game_state.drugs, drug, 0)
            drug_box = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(5))

            info_box = BoxLayout(orientation='vertical', size_hint_x=0.4)
            info_box.add_widget(Label(text=f"[b]{drug.upper()}[/b]", markup=True, font_size=dp(14)))
            info_box.add_widget(Label(text=f"${price:,} | You have: {current_qty}", font_size=dp(12)))

            button_box = BoxLayout(size_hint_x=0.6, spacing=dp(2))
            buy_btn = Button(text="Buy", size_hint_x=0.33, background_color=get_color_from_hex("#32CD32"))
            buy_btn.bind(on_press=lambda x, d=drug: self.show_trade_popup(d, 'buy'))
            button_box.add_widget(buy_btn)

            sell_btn = Button(text="Sell", size_hint_x=0.33, background_color=get_color_from_hex("#FF6347"))
            sell_btn.bind(on_press=lambda x, d=drug: self.show_trade_popup(d, 'sell'))
            button_box.add_widget(sell_btn)

            back_btn = Button(text="Back", size_hint_x=0.34, background_color=get_color_from_hex("#808080"))
            back_btn.bind(on_press=lambda x: self.manager.current = 'city')
            button_box.add_widget(back_btn)

            drug_box.add_widget(info_box)
            drug_box.add_widget(button_box)
            drug_grid.add_widget(drug_box)

        scroll.add_widget(drug_grid)
        self.layout.add_widget(scroll)

    def show_trade_popup(self, drug, action):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))

        content.add_widget(Label(text=f"{action.title()} {drug.upper()}", font_size=dp(16)))

        qty_input = TextInput(text='1', multiline=False, input_filter='int', font_size=dp(16))
        content.add_widget(qty_input)

        buttons = BoxLayout(spacing=dp(5))
        cancel_btn = Button(text="Cancel")
        confirm_btn = Button(text=f"{action.title()}", background_color=get_color_from_hex("#32CD32" if action == 'buy' else "#FF6347"))

        def do_trade(instance):
            try:
                qty = int(qty_input.text)
                self.trade_drug(drug, action, qty)
                popup.dismiss()
            except ValueError:
                pass

        confirm_btn.bind(on_press=do_trade)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())

        buttons.add_widget(cancel_btn)
        buttons.add_widget(confirm_btn)
        content.add_widget(buttons)

        popup = Popup(title=f"{action.title()} {drug.upper()}", content=content, size_hint=(0.8, 0.5))
        popup.open()

    def trade_drug(self, drug, action, quantity):
        price = self.game_state.drug_prices.get(drug, 0)
        current_qty = getattr(self.game_state.drugs, drug, 0)

        if action == 'buy':
            cost = price * quantity
            if self.game_state.money >= cost:
                self.game_state.money -= cost
                setattr(self.game_state.drugs, drug, current_qty + quantity)
                self.show_message(f"Bought {quantity} {drug} for ${cost:,}")
            else:
                self.show_message("Not enough money!")
        elif action == 'sell':
            if current_qty >= quantity:
                revenue = price * quantity
                self.game_state.money += revenue
                setattr(self.game_state.drugs, drug, current_qty - quantity)
                self.show_message(f"Sold {quantity} {drug} for ${revenue:,}")
            else:
                self.show_message("Not enough drugs!")

        save_game_state(self.game_state)
        self.build_ui()

    def show_message(self, message):
        popup = Popup(title="Message", content=Label(text=message), size_hint=(0.8, 0.3))
        popup.open()

class StatsScreen(GameScreen):
    """Stats screen"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'stats'
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()

        # Header
        self.layout.add_widget(self.create_header())

        title = Label(text="[b]PLAYER STATS[/b]", markup=True, font_size=dp(18), size_hint_y=0.1)
        self.layout.add_widget(title)

        # Stats display
        scroll = ScrollView(size_hint_y=0.7)
        stats_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(5), padding=dp(10))
        stats_grid.bind(minimum_height=stats_grid.setter('height'))

        # Basic stats
        stats_items = [
            f"Player: {self.game_state.player_name}",
            f"Gang: {self.game_state.gang_name}",
            f"Money: ${self.game_state.money:,}",
            f"Bank Account: ${self.game_state.account:,}",
            f"Loan: ${self.game_state.loan:,}",
            f"Health: {self.game_state.health}/{self.game_state.max_health}",
            f"Members: {self.game_state.members}",
            f"Squidies Left: {self.game_state.squidies}",
            f"Day: {self.game_state.day}",
            f"Steps Today: {self.game_state.steps}/{self.game_state.max_steps}",
            f"Lives: {self.game_state.lives}",
            f"Current Score: {self.game_state.current_score:,}",
        ]

        for stat in stats_items:
            stat_label = Label(text=stat, size_hint_y=None, height=dp(30), halign='left', valign='middle')
            stat_label.bind(size=stat_label.setter('text_size'))
            stats_grid.add_widget(stat_label)

        # Weapons
        stats_grid.add_widget(Label(text="[b]WEAPONS:[/b]", markup=True, size_hint_y=None, height=dp(30)))
        weapon_stats = [
            f"Pistols: {self.game_state.weapons.pistols}",
            f"Bullets: {self.game_state.weapons.bullets}",
            f"Grenades: {self.game_state.weapons.grenades}",
            f"Vampire Bat: {self.game_state.weapons.vampire_bat}",
            f"AR-15: {self.game_state.weapons.ar15}",
            f"Ghost Guns: {self.game_state.weapons.ghost_guns}",
            f"Vest: {self.game_state.weapons.vest} hits",
        ]

        for weapon in weapon_stats:
            weapon_label = Label(text=weapon, size_hint_y=None, height=dp(25), font_size=dp(12), halign='left')
            weapon_label.bind(size=weapon_label.setter('text_size'))
            stats_grid.add_widget(weapon_label)

        # Drugs
        stats_grid.add_widget(Label(text="[b]DRUGS:[/b]", markup=True, size_hint_y=None, height=dp(30)))
        drug_stats = [
            f"Weed: {self.game_state.drugs.weed}kg",
            f"Crack: {self.game_state.drugs.crack}kg",
            f"Coke: {self.game_state.drugs.coke}kg",
            f"Ice: {self.game_state.drugs.ice}kg",
            f"Percs: {self.game_state.drugs.percs}kg",
            f"Pixie Dust: {self.game_state.drugs.pixie_dust}kg",
        ]

        for drug in drug_stats:
            drug_label = Label(text=drug, size_hint_y=None, height=dp(25), font_size=dp(12), halign='left')
            drug_label.bind(size=drug_label.setter('text_size'))
            stats_grid.add_widget(drug_label)

        scroll.add_widget(stats_grid)
        self.layout.add_widget(scroll)

        # Back button
        back_btn = Button(text="Back to City", size_hint_y=0.1, background_color=get_color_from_hex("#808080"))
        back_btn.bind(on_press=lambda x: self.manager.current = 'city')
        self.layout.add_widget(back_btn)

class NewGameScreen(Screen):
    """New game setup screen"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'new_game'
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))

        title = Label(text="[b]START NEW GAME[/b]", markup=True, font_size=dp(24), size_hint_y=0.2)
        layout.add_widget(title)

        # Player name input
        name_box = BoxLayout(size_hint_y=0.15, spacing=dp(5))
        name_box.add_widget(Label(text="Player Name:", size_hint_x=0.4))
        self.player_input = TextInput(multiline=False, font_size=dp(16))
        name_box.add_widget(self.player_input)
        layout.add_widget(name_box)

        # Gang name input
        gang_box = BoxLayout(size_hint_y=0.15, spacing=dp(5))
        gang_box.add_widget(Label(text="Gang Name:", size_hint_x=0.4))
        self.gang_input = TextInput(multiline=False, font_size=dp(16))
        gang_box.add_widget(self.gang_input)
        layout.add_widget(gang_box)

        # Start game button
        start_btn = Button(text="Start Game", size_hint_y=0.2, font_size=dp(18), background_color=get_color_from_hex("#32CD32"))
        start_btn.bind(on_press=self.start_game)
        layout.add_widget(start_btn)

        self.add_widget(layout)

    def start_game(self, instance):
        player_name = self.player_input.text.strip()
        gang_name = self.gang_input.text.strip()

        if not player_name or not gang_name:
            popup = Popup(title="Error", content=Label(text="Please enter both player name and gang name"), size_hint=(0.8, 0.3))
            popup.open()
            return

        # Initialize new game
        game_state = GameState()
        game_state.player_name = player_name
        game_state.gang_name = gang_name
        game_state.weapons.pistols = 1
        game_state.weapons.bullets = 10
        game_state.weapons.knife = 1

        save_game_state(game_state)
        self.manager.get_screen('city').update_game_state()
        self.manager.current = 'city'

class GangwarApp(App):
    """Main Kivy app for Gangwar"""

    def build(self):
        # Set app properties
        self.title = 'Gangwar Game'
        self.icon = None  # Could add an icon later

        # Create screen manager
        sm = ScreenManager()

        # Add screens
        sm.add_widget(NewGameScreen())
        sm.add_widget(CityScreen())
        sm.add_widget(CrackhouseScreen())
        sm.add_widget(StatsScreen())

        # Placeholder screens for other locations
        for screen_name in ['gunshack', 'bank', 'bar', 'picknsave', 'alleyway', 'infobooth', 'wander', 'high_scores']:
            screen = GameScreen(name=screen_name)
            screen.layout.add_widget(Label(text=f"[b]{screen_name.upper()} SCREEN[/b]", markup=True, font_size=dp(20)))
            back_btn = Button(text="Back to City", size_hint_y=0.1, background_color=get_color_from_hex("#808080"))
            back_btn.bind(on_press=lambda x: sm.current = 'city')
            screen.layout.add_widget(back_btn)
            sm.add_widget(screen)

        # Check if game already exists
        try:
            game_state = get_game_state()
            if game_state.player_name:
                sm.current = 'city'
            else:
                sm.current = 'new_game'
        except:
            sm.current = 'new_game'

        return sm

if __name__ == '__main__':
    GangwarApp().run()
