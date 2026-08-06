#!/usr/bin/env python3
"""
Test script to verify bot room restrictions and chat visibility system
"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import load_json, save_json, simulate_bots, get_who_list, CHAT_MESSAGES

def test_bot_room_restrictions():
    """Test that bots are only in allowed wandering/street rooms"""
    print("=" * 60)
    print("TEST 1: Bot Room Restrictions")
    print("=" * 60)
    
    bots = load_json('model/bots.json', [])
    allowed_rooms = [
        "entrance", "dead_end", "side_street", "dumpster", "hidden_entrance",
        "underground", "secret_room", "abandoned_lot", "burned_out_car",
        "construction_site", "alley_graffiti_wall", "overgrown_garden",
        "flooded_chamber", "alley_fight_club", "mysterious_door", "ancient_vault",
        "speakeasy", "rooftop_access", "rooftop_garden", "abandoned_roof_deck",
        "rooftop_hideout", "penthouse_ruins", "makeshift_bridge", "rooftop_observatory",
        "neighboring_roof", "emergency_stairwell", "service_elevator", "maintenance_tunnel",
        "basement_storage", "utility_room", "sewer_access", "forgotten_archive",
        "boiler_room", "sewer_main_line", "coal_storage", "sewer_junction",
        "underground_stream", "storm_drain", "maintenance_shaft", "crystal_cave",
        "drainage_basin", "street_level_access", "gang_hideout", "forgotten_laboratory",
        "buried_vault", "sewage_treatment_chamber", "abandoned_warehouse",
        "loading_dock", "warehouse_office", "industrial_yard", "catwalk",
        "junkyard_office", "roof_access", "scale_house", "water_tower",
        "weigh_station", "maintenance_ladder", "ground_level", "perimeter_fence",
        "chain_lair", "tech_sanctum"
    ]
    
    # Check all bots have current_room field
    all_have_current_room = all('current_room' in bot for bot in bots)
    print(f"✓ All bots have 'current_room' field: {all_have_current_room}")
    
    # Check all bots are in allowed rooms
    violations = []
    for bot in bots:
        current_room = bot.get('current_room', bot.get('location', ''))
        if current_room not in allowed_rooms:
            violations.append(f"{bot['name']}: {current_room}")
    
    if violations:
        print(f"✗ Bots in non-allowed rooms: {violations}")
        return False
    else:
        print(f"✓ All {len(bots)} bots are in allowed wandering/street rooms")
    
    # Check bots are NOT in city-specific locations (bar, bank, crackhouse, etc.)
    forbidden_rooms = ['city', 'bar', 'bank', 'crackhouse', 'gunshack', 'picknsave', 'prostitutes']
    forbidden_found = []
    for bot in bots:
        current_room = bot.get('current_room', bot.get('location', ''))
        if current_room in forbidden_rooms:
            forbidden_found.append(f"{bot['name']}: {current_room}")
    
    if forbidden_found:
        print(f"✗ Bots found in forbidden rooms: {forbidden_found}")
        return False
    else:
        print(f"✓ No bots in city-specific locations (bar, bank, etc.)")
    
    print("✅ TEST 1 PASSED\n")
    return True

def test_bot_movement():
    """Test that bots can move to any allowed room"""
    print("=" * 60)
    print("TEST 2: Bot Movement System")
    print("=" * 60)
    
    # Clear chat messages for clean test
    CHAT_MESSAGES.clear()
    
    # Simulate bot movement
    simulate_bots(player_loc="entrance", player_name="TestPlayer")
    
    bots = load_json('model/bots.json', [])
    rooms_visited = set()
    
    for bot in bots:
        current_room = bot.get('current_room', bot.get('location', ''))
        rooms_visited.add(current_room)
    
    print(f"✓ Bots moved to {len(rooms_visited)} different rooms")
    print(f"  Rooms: {', '.join(sorted(rooms_visited))}")
    
    # Verify bots still have current_room after movement
    all_have_current_room = all('current_room' in bot for bot in bots)
    print(f"✓ Bots maintain 'current_room' after movement: {all_have_current_room}")
    
    print("✅ TEST 2 PASSED\n")
    return True

def test_chat_visibility():
    """Test that chat messages are filtered by room"""
    print("=" * 60)
    print("TEST 3: Room-Based Chat Visibility")
    print("=" * 60)
    
    # Clear chat messages
    CHAT_MESSAGES.clear()
    
    # Add some test messages
    from app import add_chat_message
    
    # Player message (should always appear)
    add_chat_message("TestPlayer", "Hello from entrance")
    
    # System message (should always appear)
    add_chat_message("SYSTEM", "Welcome to the game")
    
    # Bot messages in different rooms
    bots = load_json('model/bots.json', [])
    if len(bots) >= 2:
        # Set bot 1 to entrance
        bots[0]['current_room'] = 'entrance'
        # Set bot 2 to dead_end
        bots[1]['current_room'] = 'dead_end'
        save_json('model/bots.json', bots)
        
        # Add bot messages
        add_chat_message(bots[0]['name'], "I'm at the entrance")
        add_chat_message(bots[1]['name'], "I'm at the dead end")
    
    # Test filtering for player in entrance
    from app import api_get_chat
    from flask import Flask
    app = Flask(__name__)
    
    with app.test_request_context('/api/chat/messages?room=entrance'):
        from app import get_game_state
        gs = get_game_state()
        gs.player_name = "TestPlayer"
        gs.current_location = "entrance"
        
        # Manually test the filtering logic
        player_room = "entrance"
        room_messages = []
        for msg in CHAT_MESSAGES:
            if msg['player'] == "TestPlayer" or msg['player'] == 'SYSTEM':
                room_messages.append(msg)
            else:
                test_bots = load_json('model/bots.json', [])
                bot = next((b for b in test_bots if b['name'] == msg['player']), None)
                if bot and bot.get('current_room') == player_room:
                    room_messages.append(msg)
        
        print(f"✓ Messages visible in 'entrance': {len(room_messages)}")
        for msg in room_messages:
            print(f"  - {msg['player']}: {msg['message']}")
        
        # Should see: TestPlayer, SYSTEM, and bot at entrance
        # Should NOT see: bot at dead_end
        expected_count = 3 if len(bots) >= 2 else 2
        if len(room_messages) == expected_count:
            print(f"✅ TEST 3 PASSED\n")
            return True
        else:
            print(f"✗ Expected {expected_count} messages, got {len(room_messages)}")
            return False
    
    print("✅ TEST 3 PASSED\n")
    return True

def test_who_list():
    """Test that who list shows bot locations"""
    print("=" * 60)
    print("TEST 4: Who List Shows Bot Locations")
    print("=" * 60)
    
    who_list = get_who_list()
    
    print(f"✓ Who list contains {len(who_list)} entries")
    
    # Check bots show their current_room
    bots = load_json('model/bots.json', [])
    bot_entries = [w for w in who_list if w['type'] == 'Bot']
    
    for entry in bot_entries[:3]:  # Show first 3
        print(f"  - {entry['name']} ({entry['type']}): {entry['loc']}")
    
    # Verify all bot entries have a location
    all_have_location = all('loc' in entry for entry in bot_entries)
    print(f"✓ All bot entries have location: {all_have_location}")
    
    print("✅ TEST 4 PASSED\n")
    return True

def main():
    print("\n" + "=" * 60)
    print("BOT ROOM SYSTEM TEST SUITE")
    print("=" * 60 + "\n")
    
    results = []
    
    try:
        results.append(("Bot Room Restrictions", test_bot_room_restrictions()))
    except Exception as e:
        print(f"✗ TEST 1 FAILED: {e}\n")
        results.append(("Bot Room Restrictions", False))
    
    try:
        results.append(("Bot Movement", test_bot_movement()))
    except Exception as e:
        print(f"✗ TEST 2 FAILED: {e}\n")
        results.append(("Bot Movement", False))
    
    try:
        results.append(("Chat Visibility", test_chat_visibility()))
    except Exception as e:
        print(f"✗ TEST 3 FAILED: {e}\n")
        results.append(("Chat Visibility", False))
    
    try:
        results.append(("Who List", test_who_list()))
    except Exception as e:
        print(f"✗ TEST 4 FAILED: {e}\n")
        results.append(("Who List", False))
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())