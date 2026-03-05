#!/usr/bin/env python3
"""
Test script for the evolving NPC system.
This script demonstrates the new NPC evolution, conversation, and relationship features.
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from npc_integration import NPCIntegrationSystem

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_npc_status(npc_id: str, integration: NPCIntegrationSystem):
    """Print detailed status of an NPC."""
    npc = integration.get_npc_with_evolution(npc_id)
    if not npc:
        print(f"NPC {npc_id} not found.")
        return
    
    evolution = npc.get("evolution", {})
    
    print(f"\nNPC: {npc['name']} ({npc_id})")
    print(f"  Location: {npc['location']}")
    print(f"  Description: {npc['description']}")
    print(f"  Evolution Stage: {evolution.get('evolution_stage', 'None')}")
    print(f"  Power Level: {evolution.get('power_level', 0)}")
    print(f"  Traits: {', '.join(evolution.get('traits', [])) or 'None'}")
    print(f"  Relationships: {evolution.get('relationships', {})}")
    print(f"  Status Effects: {evolution.get('status_effects', [])}")
    print(f"  HP: {npc.get('hp', 0)}/{npc.get('max_hp', 0)}")
    print(f"  Damage: {npc.get('damage', 0)}")

def test_evolution_system():
    """Test the complete evolving NPC system."""
    print_section("EVOLVING NPC SYSTEM DEMO")
    
    # Initialize the integration system
    integration = NPCIntegrationSystem()
    
    print("Initializing NPC Integration System...")
    print(f"Loaded {len(integration.npcs)} NPCs")
    print(f"Loaded {len(integration.dialogues)} NPC dialogues")
    
    # Show initial state
    print_section("INITIAL NPC STATUS")
    for npc_id in ["nox", "raze", "void"]:
        print_npc_status(npc_id, integration)
    
    # Test evolution
    print_section("EVOLVING NPCs")
    print("Evolving all NPCs based on current conditions...")
    
    evolution_results = integration.evolve_all_npcs(current_day=5)
    
    for npc_id, result in evolution_results.items():
        if result["evolved"]:
            print(f"✓ {npc_id} evolved!")
            print(f"  Power: {result['old_power']} → {result['new_power']}")
            if result["new_traits"]:
                print(f"  New traits: {', '.join(result['new_traits'])}")
        else:
            print(f"• {npc_id} did not evolve this cycle")
    
    # Show evolved state
    print_section("AFTER EVOLUTION")
    for npc_id in ["nox", "raze", "void"]:
        print_npc_status(npc_id, integration)
    
    # Test relationship system
    print_section("RELATIONSHIP SYSTEM")
    
    # Test different relationship actions
    actions = [
        ("nox", "help_npc", 20, "Helping Glitch"),
        ("raze", "defeat_npc", 30, "Defeating Ravager in combat"),
        ("void", "trade_fairly", 15, "Trading fairly with Phantom"),
        ("nox", "gift_npc", 25, "Giving Glitch a gift")
    ]
    
    for npc_id, action, impact, description in actions:
        print(f"\n{description}:")
        result = integration.update_player_relationship(npc_id, action, impact)
        print(f"  Relationship status: {result['relationship_status']}")
        print(f"  Current relationship: {result['current_relationship']}/100")
        print(f"  Color: {integration.relationship_system.get_relationship_color(npc_id)}")
    
    # Test conversation system
    print_section("EVOLVING CONVERSATIONS")
    
    player_data = {
        "money": 5000,
        "day": 5,
        "health": 80,
        "gang_members": ["member1", "member2", "member3"],
        "name": "Player"
    }
    
    # Test different topics with different NPCs
    conversation_tests = [
        ("nox", "squidies", "Asking Glitch about the Squidies"),
        ("raze", "fight", "Asking Ravager about fights"),
        ("void", "tech", "Asking Phantom about tech"),
        ("nox", "money", "Asking Glitch about making money")
    ]
    
    for npc_id, topic, description in conversation_tests:
        print(f"\n{description}:")
        response = integration.get_npc_response(npc_id, topic, player_data)
        print(f"  Response: {response['text']}")
        print(f"  Cost: ${response.get('cost', 0)}")
        print(f"  Effect: {response.get('effect', 'None')}")
        
        # Show memory summary
        memory = integration.get_npc_memory_summary(npc_id, topic)
        print(f"  Conversation history: {memory['total_conversations']} interactions")
        if memory['recent_responses']:
            print(f"  Recent responses: {memory['recent_responses'][-1][:50]}...")
    
    # Test dynamic greetings
    print_section("DYNAMIC GREETINGS")
    
    for npc_id in ["nox", "raze", "void"]:
        greeting = integration.generate_npc_greeting(npc_id, player_data)
        print(f"{integration.npcs[npc_id]['name']}: {greeting}")
    
    # Test evolved dialogue
    print_section("EVOLVED DIALOGUE")
    
    for npc_id in ["nox", "raze"]:
        evolved_dialogue = integration.get_evolved_npc_dialogue(npc_id)
        if evolved_dialogue:
            print(f"\n{integration.npcs[npc_id]['name']} - Evolved Dialogue:")
            for topic_name, topic_data in evolved_dialogue.get("topics", {}).items():
                print(f"  Topic: {topic_name}")
                for i, response in enumerate(topic_data.get("responses", [])[:2]):  # Show first 2 responses
                    print(f"    {i+1}. {response['text'][:60]}...")
    
    # Test evolution report
    print_section("EVOLUTION REPORT")
    report = integration.get_evolution_report()
    
    print(f"Total NPCs: {report['total_npcs']}")
    print(f"Evolved NPCs: {report['evolved_npcs']}")
    print(f"\nPower Level Distribution:")
    for level, count in report['power_level_distribution'].items():
        print(f"  {level}: {count}")
    
    print(f"\nTop Traits:")
    sorted_traits = sorted(report['trait_distribution'].items(), key=lambda x: x[1], reverse=True)
    for trait, count in sorted_traits[:5]:
        print(f"  {trait}: {count}")
    
    # Test cleanup
    print_section("CLEANUP AND MAINTENANCE")
    integration.cleanup_old_data()
    print("Cleaned up old conversation memory and NPC data.")
    
    # Save final state
    integration.save_npcs()
    print("Saved updated NPC data to model/npcs.json")
    
    print_section("DEMO COMPLETE")
    print("The evolving NPC system is now active!")
    print("\nKey Features Demonstrated:")
    print("• NPC evolution based on time, relationships, and combat outcomes")
    print("• Dynamic conversations that remember past interactions")
    print("• Relationship system affecting prices, information quality, and aggression")
    print("• Trait system modifying NPC behavior and dialogue")
    print("• Memory system tracking player interactions over time")
    print("• Power level progression affecting NPC stats and capabilities")

if __name__ == "__main__":
    try:
        test_evolution_system()
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()