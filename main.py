#!/usr/bin/env python3
"""
Gangwar Game - Android Mobile App (Master Production Build)
Features: Smart Bot AI, Market Dynamics, Procedural content, and Console Commands.
"""

import os
import sys
import time
import random
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from dataclasses import asdict

# Add src to path for logic imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import core game logic
import app as game_logic
from app import (
    get_game_state, save_game_state, GameState, 
    simulate_bots, load_current_drug_prices,
    rooms_config, load_bots, modify_market_supply, add_chat_message,
    get_who_list, get_top_list, weapon_prices_config, npcs_data,
    process_combat_action, generate_random_room, reset_game_state
)

Window.size = (400, 700)

class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_state = get_game_state()
        self.layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))
        self.add_widget(self.layout)

    def update_game_state(self):
        self.game_state = get_game_state()
        if hasattr(self, 'build_ui'):
            self.build_ui()

    def create_header(self):
        header = BoxLayout(size_hint_y=0.18, padding=dp(5), spacing=dp(5))
        info = BoxLayout(orientation='vertical', size_hint_x=0.45)
        info.add_widget(Label(text=f"[b]{self.game_state.player_name}[/b]", markup=True, font_size=dp(16)))
        info.add_widget(Label(text=f"{self.game_state.gang_name}", font_size=dp(12), color=(0.7,0.7,0.7,1)))
        info.add_widget(Label(text=f"Day: {self.game_state.day} | Step: {self.game_state.steps}/{self.game_state.max_steps}", font_size=dp(11)))
        header.add_widget(info)

        stats = GridLayout(cols=2, size_hint_x=0.55)
        stats.add_widget(Label(text=f"Cash: [color=#00FF00]${self.game_state.money:,}[/color]", markup=True, font_size=dp(11)))
        stats.add_widget(Label(text=f"HP: {self.game_state.health}", font_size=dp(11)))
        stats.add_widget(Label(text=f"Crew: {self.game_state.members}", font_size=dp(11)))
        stats.add_widget(Label(text=f"Lives: {self.game_state.lives}", font_size=dp(11)))
        header.add_widget(stats)
        return header

    def show_message(self, title, msg):
        p = Popup(title=title, content=Label(text=msg, halign='center', valign='middle'), size_hint=(0.8, 0.3))
        p.open()

class CityScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'city'
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(self.create_header())

        # Live Chat
        self.layout.add_widget(Label(text="[b]STREET CHATTER[/b]", markup=True, size_hint_y=0.04, font_size=dp(10), color=(1, 0.8, 0, 1)))
        chat_scroll = ScrollView(size_hint_y=0.2, background_color=(0.1, 0.1, 0.1, 1))
        chat_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        chat_layout.bind(minimum_height=chat_layout.setter('height'))
        for msg in game_logic.CHAT_MESSAGES[-15:]:
            color = "#FFD700" if msg['player'] != "SYSTEM" else "#FF5252"
            lbl = Label(text=f"[color={color}][b]{msg['player']}:[/b][/color] {msg['message']}", 
                        markup=True, font_size=dp(11), size_hint_y=None, height=dp(20), halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            chat_layout.add_widget(lbl)
        chat_scroll.add_widget(chat_layout)
        self.layout.add_widget(chat_scroll)

        # Console
        console = BoxLayout(size_hint_y=0.08, spacing=dp(5))
        self.cmd = TextInput(hint_text="Type command (/who, /top) or chat...", multiline=False, font_size=dp(12))
        send = Button(text="SEND", size_hint_x=0.2, background_color=get_color_from_hex("#4CAF50"))
        send.bind(on_press=self.on_send)
        console.add_widget(self.cmd)
        console.add_widget(send)
        self.layout.add_widget(console)

        # Nav
        nav = GridLayout(cols=2, size_hint_y=0.4, spacing=dp(5))
        locs = [("Crackhouse", "crackhouse", "#5D4037"), ("Gun Shack", "gunshack", "#37474F"),
                ("Bank", "bank", "#FBC02D"), ("Local Bar", "bar", "#C62828"),
                ("Pick n Save", "picknsave", "#2E7D32"), ("Alleyway", "alleyway", "#424242"),
                ("Wander", "wander", "#D32F2F"), ("Stats", "stats", "#673AB7")]
        for name, sid, color in locs:
            btn = Button(text=name, background_color=get_color_from_hex(color), font_size=dp(13), bold=True)
            btn.bind(on_press=lambda x, s=sid: self.navigate(s))
            nav.add_widget(btn)
        self.layout.add_widget(nav)

        # Market Info
        prices_data = load_current_drug_prices()
        self.layout.add_widget(Label(text=f"[i]{prices_data.get('fluctuation_alert', 'Market is steady.')}[/i]", 
                                     markup=True, color=(1, 0.5, 0, 1), font_size=dp(11), size_hint_y=0.06))

    def on_send(self, instance):
        text = self.cmd.text.strip()
        if not text: return
        self.cmd.text = ""
        if text.startswith('/'):
            cmd = text[1:].lower().split()[0]
            if cmd == 'who': self.navigate('who')
            elif cmd == 'top': self.navigate('top')
            elif cmd == 'restart': self.restart_game()
            else: add_chat_message("SYSTEM", f"Command /{cmd} not recognized.")
        else:
            add_chat_message(self.game_state.player_name, text)
        self.update_game_state()

    def restart_game(self):
        reset_game_state()
        self.manager.current = 'new_game'

    def navigate(self, sid):
        self.manager.current = sid
        self.manager.get_screen(sid).update_game_state()

class WhoScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'who'
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(self.create_header())
        self.layout.add_widget(Label(text="[b]WHO'S ON THE BLOCK[/b]", markup=True, font_size=dp(18), size_hint_y=0.08))
        scroll = ScrollView(size_hint_y=0.7)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(5), padding=dp(10))
        grid.bind(minimum_height=grid.setter('height'))
        for e in get_who_list():
            color = "#00FF00" if e['type'] == "Player" else "#00BCD4"
            grid.add_widget(Label(text=f"[color={color}][b]{e['name']}[/b][/color] ({e['type']}) is at [b]{e['loc'].title()}[/b]", 
                                  markup=True, size_hint_y=None, height=dp(30), halign='left'))
        scroll.add_widget(grid); self.layout.add_widget(scroll)
        self.layout.add_widget(Button(text="Back", size_hint_y=0.1, on_press=lambda x: setattr(self.manager, 'current', 'city')))

class TopScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'top'
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(self.create_header())
        self.layout.add_widget(Label(text="[b]KING PIMPS (TOP 10)[/b]", markup=True, font_size=dp(18), size_hint_y=0.08))
        scroll = ScrollView(size_hint_y=0.7)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(5), padding=dp(10))
        grid.bind(minimum_height=grid.setter('height'))
        for i, p in enumerate(get_top_list()):
            grid.add_widget(Label(text=f"{i+1}. [b]{p['name']}[/b] - [color=#00FF00]{p['score']}[/color] pts", 
                                  markup=True, size_hint_y=None, height=dp(30), halign='left'))
        scroll.add_widget(grid); self.layout.add_widget(scroll)
        self.layout.add_widget(Button(text="Back", size_hint_y=0.1, on_press=lambda x: setattr(self.manager, 'current', 'city')))

class CrackhouseScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'crackhouse'
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(self.create_header())
        self.layout.add_widget(Label(text="[b]DRUG WHOLESALE[/b]", markup=True, font_size=dp(18), size_hint_y=0.08))
        scroll = ScrollView(size_hint_y=0.72)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(5), padding=dp(5))
        grid.bind(minimum_height=grid.setter('height'))

        drugs = sorted(self.game_state.drugs.keys(), key=lambda d: self.game_state.drug_prices.get(d, 0), reverse=True)
        for drug in drugs:
            price = self.game_state.drug_prices.get(drug, 1000)
            qty = getattr(self.game_state.drugs, drug, 0)
            box = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))
            box.add_widget(Label(text=f"[b]{drug.upper()}[/b]\n${price:,} ({qty}kg)", markup=True, size_hint_x=0.4))
            
            b_box = BoxLayout(size_hint_x=0.6, spacing=dp(2))
            buy = Button(text="BUY", background_color=get_color_from_hex("#2E7D32"))
            buy.bind(on_press=lambda x, d=drug: self.trade(d, 'buy'))
            sell = Button(text="SELL", background_color=get_color_from_hex("#C62828"))
            sell.bind(on_press=lambda x, d=drug: self.trade(d, 'sell'))
            b_box.add_widget(buy); b_box.add_widget(sell)
            box.add_widget(b_box); grid.add_widget(box)

        scroll.add_widget(grid); self.layout.add_widget(scroll)
        self.layout.add_widget(Button(text="Back", size_hint_y=0.1, on_press=lambda x: setattr(self.manager, 'current', 'city')))

    def trade(self, drug, action):
        price = self.game_state.drug_prices.get(drug, 1000)
        curr_qty = getattr(self.game_state.drugs, drug, 0)
        if action == 'buy' and self.game_state.money >= price:
            self.game_state.money -= price
            setattr(self.game_state.drugs, drug, curr_qty + 1)
            modify_market_supply(drug, -1)
            simulate_bots(self.game_state.current_location, self.game_state.player_name)
        elif action == 'sell' and curr_qty > 0:
            self.game_state.money += price
            setattr(self.game_state.drugs, drug, curr_qty - 1)
            modify_market_supply(drug, 1)
            simulate_bots(self.game_state.current_location, self.game_state.player_name)
        save_game_state(self.game_state); self.update_game_state()

class GunShackScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'gunshack'
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(self.create_header())
        self.layout.add_widget(Label(text="[b]UNDERGROUND ARSENAL[/b]", markup=True, font_size=dp(18), size_hint_y=0.08))
        scroll = ScrollView(size_hint_y=0.72)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(5), padding=dp(5))
        grid.bind(minimum_height=grid.setter('height'))

        weapons = weapon_prices_config.get('weapons', {})
        for wid, info in weapons.items():
            box = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(10))
            box.add_widget(Label(text=f"{wid.replace('_',' ').title()}\n${info['price']:,}", size_hint_x=0.6, font_size=dp(12)))
            buy = Button(text="BUY", size_hint_x=0.4, background_color=get_color_from_hex("#B71C1C"))
            buy.bind(on_press=lambda x, w=wid: self.buy_w(w))
            box.add_widget(buy); grid.add_widget(box)

        scroll.add_widget(grid); self.layout.add_widget(scroll)
        self.layout.add_widget(Button(text="Back", size_hint_y=0.1, on_press=lambda x: setattr(self.manager, 'current', 'city')))

    def buy_w(self, wid):
        price = weapon_prices_config['weapons'][wid]['price']
        if self.game_state.money >= price:
            self.game_state.money -= price
            if wid.endswith('bullets'): setattr(self.game_state.weapons, wid, getattr(self.game_state.weapons, wid) + 50)
            elif hasattr(self.game_state.weapons, wid): setattr(self.game_state.weapons, wid, getattr(self.game_state.weapons, wid) + 1)
            save_game_state(self.game_state); self.update_game_state()
            self.show_message("Locked & Loaded", f"Bought {wid}!")
        else: self.show_message("Broke", "You need more cash.")

class AlleywayScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'alleyway'
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(self.create_header())
        rid = App.get_running_app().rid
        room = rooms_config['rooms'].get(rid, rooms_config['rooms']['entrance'])
        self.layout.add_widget(Label(text=f"[b]{room['title'].upper()}[/b]", markup=True, size_hint_y=0.1))
        desc = Label(text=room['description'], font_size=dp(13), size_hint_y=0.25, halign='center', valign='middle')
        desc.bind(size=desc.setter('text_size'))
        self.layout.add_widget(desc)

        move = GridLayout(cols=3, size_hint_y=0.3, spacing=dp(5))
        exits = room.get('exits', {})
        dirs = [('north', '^'), ('west', '<'), ('east', '>'), ('south', 'v'), ('up', 'U'), ('down', 'D')]
        for d, l in dirs:
            if d in exits:
                b = Button(text=l, background_color=get_color_from_hex("#4682B4"))
                b.bind(on_press=lambda x, dir=d: self.do_move(dir))
                move.add_widget(b)
            else: move.add_widget(Label())
        self.layout.add_widget(move)
        
        acts = BoxLayout(size_hint_y=0.15, spacing=dp(5))
        s = Button(text="SEARCH AREA", background_color=get_color_from_hex("#DAA520"))
        s.bind(on_press=self.do_search)
        acts.add_widget(s)
        self.layout.add_widget(acts)

    def do_move(self, d):
        rid = App.get_running_app().rid
        nxt = rooms_config['rooms'][rid]['exits'][d]
        if nxt == 'city': self.manager.current = 'city'
        else:
            App.get_running_app().rid = nxt
            self.game_state.steps += 1
            simulate_bots(self.game_state.current_location, self.game_state.player_name)
            if self.game_state.steps >= self.game_state.max_steps: self.end_day()
            save_game_state(self.game_state); self.update_game_state()

    def do_search(self, instance):
        self.game_state.steps += 1; simulate_bots(self.game_state.current_location, self.game_state.player_name); rid = App.get_running_app().rid
        boss = next((n for n in npcs_data.values() if n['location'] == rid and n['is_alive']), None)
        if boss:
            self.manager.get_screen('combat').setup_fight(boss['name'], 1, boss['hp'], True)
            self.manager.current = 'combat'
        else:
            roll = random.random()
            if roll < 0.15: 
                new_rid = generate_random_room(rid)
                self.show_message("Discovery", "You found a hidden passage to a new sector!")
            elif roll < 0.3: 
                amt = random.randint(500, 2000); self.game_state.money += amt
                self.show_message("Loot", f"Found a briefcase with ${amt:,}!")
            elif roll < 0.45:
                drug = random.choice(self.game_state.drugs.keys())
                setattr(self.game_state.drugs, drug, getattr(self.game_state.drugs, drug) + 5)
                self.show_message("Loot", f"Found 5kg of {drug}!")
            else: self.show_message("Empty", "Nothing but rats and rust.")
        if self.game_state.steps >= self.game_state.max_steps: self.end_day()
        save_game_state(self.game_state); self.update_game_state()

    def end_day(self):
        self.game_state.day += 1; self.game_state.steps = 0
        game_logic.update_daily_prices()

class CombatScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'combat'
        self.e_type = "Enemy"; self.e_count = 1; self.e_hp = 100; self.is_boss = False
        self.log = []

    def setup_fight(self, e_type, e_count, e_hp, is_boss=False):
        self.e_type = e_type; self.e_count = e_count; self.e_hp = e_hp; self.is_boss = is_boss
        self.log = ["Violence erupts! Combat initiated."]
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(self.create_header())
        
        self.layout.add_widget(Label(text=f"[b]{self.e_type.upper()}[/b] (x{self.e_count})", markup=True, font_size=dp(18), color=(1,0,0,1)))
        self.layout.add_widget(Label(text=f"Health: {self.e_hp}", font_size=dp(16)))

        scroll = ScrollView(size_hint_y=0.4)
        clog = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        clog.bind(minimum_height=clog.setter('height'))
        for line in self.log[-12:]:
            clog.add_widget(Label(text=line, font_size=dp(11), size_hint_y=None, height=dp(20)))
        scroll.add_widget(clog); self.layout.add_widget(scroll)

        w_grid = GridLayout(cols=3, size_hint_y=0.2, spacing=dp(5))
        opts = [('fists', 'Fists')]
        if self.game_state.weapons.pistols > 0: opts.append(('pistol', 'Pistol'))
        if self.game_state.weapons.ar15 > 0: opts.append(('ar15', 'AR-15'))
        if self.game_state.weapons.golden_gun > 0: opts.append(('golden_gun', 'GOLDEN'))
        if self.game_state.weapons.katana > 0: opts.append(('katana', 'Katana'))
        if self.game_state.weapons.uzi > 0: opts.append(('uzi', 'Uzi'))
        if self.game_state.weapons.sawed_off_shotgun > 0: opts.append(('sawed_off_shotgun', 'Sawed-off'))
        
        for wid, label in opts:
            btn = Button(text=label, background_color=get_color_from_hex("#37474F"))
            btn.bind(on_press=lambda x, w=wid: self.combat_step(w))
            w_grid.add_widget(btn)
        self.layout.add_widget(w_grid)
        self.layout.add_widget(Button(text="FLEE", size_hint_y=0.1, background_color=get_color_from_hex("#616161"), on_press=lambda x: self.combat_step('flee')))

    def combat_step(self, choice):
        defeated, self.e_hp, new_log, dead = process_combat_action(self.game_state, 'flee' if choice=='flee' else 'attack', choice, self.e_hp, self.e_type, self.e_count, self.is_boss)
        self.log.extend(new_log)
        self.update_game_state()
        if dead: self.manager.current = 'city'; self.show_message("Wasted", "You were taken out.")
        elif defeated: 
            self.manager.current = 'city'; self.show_message("Victory", f"Defeated {self.e_type}!")
            game_logic.BOT_CHALLENGE = None
        else: self.build_ui()

class WanderScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'wander'

    def on_enter(self):
        self.game_state.steps += 1
        simulate_bots(self.game_state.current_location, self.game_state.player_name)
        save_game_state(self.game_state)
        
        if game_logic.BOT_CHALLENGE:
            bc = game_logic.BOT_CHALLENGE
            self.manager.get_screen('combat').setup_fight(bc, 1, 150, False)
            self.manager.current = 'combat'
            return

        self.layout.clear_widgets()
        self.layout.add_widget(self.create_header())
        events = ["Avoided a drive-by.", "Found a stash of brass knuckles.", "Bots are trading heavy today.", "The block is hot."]
        self.layout.add_widget(Label(text=f"[b]STREET REPORT[/b]\n\n{random.choice(events)}", markup=True, halign='center'))
        btn = Button(text="CONTINUE", size_hint_y=0.2, on_press=lambda x: setattr(self.manager, 'current', 'city'))
        self.layout.add_widget(btn)

class NewGameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'new_game'
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        layout.add_widget(Label(text="[b]GANGWAR[/b]", markup=True, font_size=dp(30), color=(1,0.8,0,1)))
        self.p_name = TextInput(hint_text="Pimp Name", multiline=False, font_size=dp(18))
        self.g_name = TextInput(hint_text="Syndicate Name", multiline=False, font_size=dp(18))
        layout.add_widget(self.p_name); layout.add_widget(self.g_name)
        btn = Button(text="START EMPIRE", background_color=get_color_from_hex("#4CAF50"), font_size=dp(20), bold=True)
        btn.bind(on_press=self.start)
        layout.add_widget(btn); self.add_widget(layout)

    def start(self, instance):
        if self.p_name.text and self.g_name.text:
            gs = GameState(player_name=self.p_name.text, gang_name=self.g_name.text)
            save_game_state(gs); self.manager.current = 'city'; self.manager.get_screen('city').update_game_state()

class StatsScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'stats'
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()
        self.layout.add_widget(self.create_header())
        scroll = ScrollView(size_hint_y=0.8)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(2), padding=dp(10))
        grid.bind(minimum_height=grid.setter('height'))
        grid.add_widget(Label(text="[b]ARSENAL[/b]", markup=True, size_hint_y=None, height=dp(30), color=(1,0,0,1)))
        for k, v in asdict(self.game_state.weapons).items():
            if v and not isinstance(v, bool): grid.add_widget(Label(text=f"{k.replace('_',' ').title()}: {v}", size_hint_y=None, height=dp(20)))
        grid.add_widget(Label(text="[b]STASH[/b]", markup=True, size_hint_y=None, height=dp(30), color=(0,1,0,1)))
        for drug in self.game_state.drugs.keys():
            q = getattr(self.game_state.drugs, drug, 0)
            if q: grid.add_widget(Label(text=f"{drug.title()}: {q}kg", size_hint_y=None, height=dp(20)))
        scroll.add_widget(grid); self.layout.add_widget(scroll)
        self.layout.add_widget(Button(text="Back", size_hint_y=0.1, on_press=lambda x: setattr(self.manager, 'current', 'city')))

class GangwarApp(App):
    def build(self):
        self.rid = 'entrance'
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(NewGameScreen())
        sm.add_widget(CityScreen()); sm.add_widget(WhoScreen()); sm.add_widget(TopScreen())
        sm.add_widget(StatsScreen()); sm.add_widget(GunShackScreen()); sm.add_widget(BankScreen())
        sm.add_widget(AlleywayScreen()); sm.add_widget(WanderScreen()); sm.add_widget(CombatScreen())
        sm.add_widget(CrackhouseScreen())
        for s in ['bar', 'picknsave', 'infobooth']:
            sc = GameScreen(name=s); sc.layout.add_widget(Label(text=f"{s.upper()} Area (WIP)"))
            sc.layout.add_widget(Button(text="Return", size_hint_y=0.1, on_press=lambda x: setattr(sm, 'current', 'city')))
            sm.add_widget(sc)
        if get_game_state().player_name: sm.current = 'city'
        return sm

if __name__ == '__main__':
    if not os.path.exists(game_logic.PRICES_FILE): update_daily_prices()
    GangwarApp().run()
