import json
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__)))

from evolution_system import EvolutionSystem
from evolving_conversations import EvolvingConversationSystem

class NPCIntegrationSystem:
    """Main integration system that combines evolution, conversations, and relationships."""
    
    def __init__(self, npcs_path: str = "model/npcs.json", 
                 dialogues_path: str = "model/npc_dialogues.json",
                 evolution_config_path: str = "model/npc_evolution_config.json"):
        """Initialize the NPC integration system."""
        self.evolution_system = EvolutionSystem(evolution_config_path)
        self.conversation_system = EvolvingConversationSystem(dialogues_path)
        
        # Load NPC data
        with open(npcs_path, 'r') as f:
            self.npcs = json.load(f)
        
        with open(dialogues_path, 'r') as f:
            self.dialogues = json.load(f)
        
        self.relationship_system = RelationshipSystem(self.evolution_system, self.dialogues)
    
    def get_npc_with_evolution(self, npc_id: str) -> Dict[str, Any]:
        """Get an NPC with evolution data applied."""
        if npc_id not in self.npcs:
            return None
        
        npc = self.npcs[npc_id].copy()
        
        # Apply evolution effects if NPC has evolution data
        if "evolution" in npc:
            evolution_data = npc["evolution"]
            
            # Apply power level multipliers to stats
            hp_mult, dmg_mult = self.evolution_system.get_power_level_multiplier(evolution_data["power_level"])
            npc["hp"] = int(npc.get("hp", 100) * hp_mult)
            npc["max_hp"] = int(npc.get("max_hp", 100) * hp_mult)
            npc["damage"] = int(npc.get("damage", 10) * dmg_mult)
            
            # Apply trait effects
            npc = self.evolution_system.apply_trait_effects(npc, {})
        
        return npc
    
    def evolve_all_npcs(self, current_day: int) -> Dict[str, Any]:
        """Evolve all NPCs based on current conditions."""
        evolution_results = {}
        
        for npc_id, npc in self.npcs.items():
            # Create a copy to work with
            npc_copy = npc.copy()
            
            # Evolve the NPC
            evolved_npc = self.evolution_system.evolve_npc(npc_copy, current_day)
            
            # Update the original NPC if it changed
            if evolved_npc != npc:
                self.npcs[npc_id] = evolved_npc
                evolution_results[npc_id] = {
                    "evolved": True,
                    "old_power": npc.get("evolution", {}).get("power_level", 100),
                    "new_power": evolved_npc.get("evolution", {}).get("power_level", 100),
                    "new_traits": evolved_npc.get("evolution", {}).get("traits", []),
                    "new_stage": evolved_npc.get("evolution", {}).get("evolution_stage", "Unknown")
                }
            else:
                evolution_results[npc_id] = {"evolved": False}
        
        # Save updated NPC data
        self.save_npcs()
        
        return evolution_results
    
    def get_npc_response(self, npc_id: str, topic: str, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get an evolving response from an NPC."""
        # Get the evolved NPC data
        npc = self.get_npc_with_evolution(npc_id)
        if not npc:
            return {"text": "This NPC doesn't exist.", "cost": 0, "effect": None}
        
        # Get response from conversation system
        response = self.conversation_system.get_npc_response(npc_id, topic, player_data)
        
        # Apply relationship changes if response has cost or effect
        if response.get("cost", 0) > 0:
            # Player paid - positive relationship change
            self.relationship_system.update_relationship(npc_id, "trade_fairly", 10)
        elif response.get("effect") == "has_info":
            # NPC provided information - positive relationship change
            self.relationship_system.update_relationship(npc_id, "help_npc", 5)
        
        return response
    
    def update_player_relationship(self, npc_id: str, action: str, impact: int) -> Dict[str, Any]:
        """Update the relationship between player and NPC."""
        return self.relationship_system.update_relationship(npc_id, action, impact)
    
    def get_npc_relationship_status(self, npc_id: str) -> str:
        """Get the relationship status with an NPC."""
        return self.relationship_system.get_relationship_status(npc_id)
    
    def get_npc_memory_summary(self, npc_id: str, topic: str) -> Dict[str, Any]:
        """Get conversation memory summary for an NPC."""
        return self.conversation_system.get_memory_summary(npc_id, topic)
    
    def generate_npc_greeting(self, npc_id: str, player_data: Dict[str, Any]) -> str:
        """Generate a dynamic greeting for an NPC."""
        return self.conversation_system.generate_dynamic_greeting(npc_id, player_data)
    
    def get_evolved_npc_dialogue(self, npc_id: str) -> Dict[str, Any]:
        """Get dialogue data with evolution effects applied."""
        if npc_id not in self.dialogues:
            return {}
        
        dialogue_data = self.dialogues[npc_id].copy()
        npc_data = self.get_npc_with_evolution(npc_id)
        
        if not npc_data or "evolution" not in npc_data:
            return dialogue_data
        
        evolution_data = npc_data["evolution"]
        traits = evolution_data.get("traits", [])
        
        # Modify dialogue based on traits
        if "Wise" in traits:
            # Add wisdom to responses
            for topic in dialogue_data.get("topics", {}).values():
                for response in topic.get("responses", []):
                    if response.get("effect") == "has_info":
                        response["text"] += " [Wisdom bonus applied]"
        
        if "Generous" in traits:
            # Reduce costs for generous NPCs
            for topic in dialogue_data.get("topics", {}).values():
                for response in topic.get("responses", []):
                    if response.get("cost", 0) > 0:
                        response["cost"] = int(response["cost"] * 0.8)
        
        if "Greedy" in traits:
            # Increase costs for greedy NPCs
            for topic in dialogue_data.get("topics", {}).values():
                for response in topic.get("responses", []):
                    if response.get("cost", 0) > 0:
                        response["cost"] = int(response["cost"] * 1.2)
        
        return dialogue_data
    
    def cleanup_old_data(self):
        """Clean up old conversation memory and NPC data."""
        self.conversation_system.cleanup_old_conversations()
        
        # Clean up NPC memories
        for npc_id, npc in self.npcs.items():
            if "evolution" in npc:
                self.evolution_system.cleanup_old_memories(npc)
    
    def save_npcs(self):
        """Save updated NPC data to file."""
        with open("model/npcs.json", 'w') as f:
            json.dump(self.npcs, f, indent=2)
    
    def get_evolution_report(self) -> Dict[str, Any]:
        """Generate a report on NPC evolution status."""
        report = {
            "total_npcs": len(self.npcs),
            "evolved_npcs": 0,
            "power_level_distribution": {"Weak": 0, "Average": 0, "Strong": 0, "Elite": 0, "Legendary": 0},
            "trait_distribution": {},
            "relationship_summary": {"friendly": 0, "neutral": 0, "hostile": 0}
        }
        
        for npc in self.npcs.values():
            if "evolution" in npc:
                report["evolved_npcs"] += 1
                stage = npc["evolution"].get("evolution_stage", "Unknown")
                if stage in report["power_level_distribution"]:
                    report["power_level_distribution"][stage] += 1
                
                # Count traits
                for trait in npc["evolution"].get("traits", []):
                    report["trait_distribution"][trait] = report["trait_distribution"].get(trait, 0) + 1
        
        return report


class RelationshipSystem:
    """System for managing NPC relationships with the player."""
    
    def __init__(self, evolution_system: EvolutionSystem, dialogue_config: Dict[str, Any]):
        """Initialize the relationship system."""
        self.evolution_system = evolution_system
        self.dialogue_config = dialogue_config
    
    def update_relationship(self, npc_id: str, action: str, impact: int) -> Dict[str, Any]:
        """Update relationship between player and NPC."""
        if npc_id not in self.dialogue_config:
            return {"success": False, "message": "NPC not found"}
        
        npc = self.dialogue_config[npc_id]
        
        # Update relationship using evolution system
        updated_npc = self.evolution_system.update_npc_relationship(npc, action, impact)
        
        # Get relationship status
        status = self.evolution_system.get_npc_relationship_status(updated_npc)
        
        return {
            "success": True,
            "npc_id": npc_id,
            "action": action,
            "impact": impact,
            "relationship_status": status,
            "current_relationship": updated_npc.get("evolution", {}).get("relationships", {}).get("player", 0)
        }
    
    def get_relationship_status(self, npc_id: str) -> str:
        """Get the current relationship status with an NPC."""
        if npc_id not in self.dialogue_config:
            return "unknown"
        
        return self.evolution_system.get_npc_relationship_status(self.dialogue_config[npc_id])
    
    def get_relationship_color(self, npc_id: str) -> str:
        """Get the color code for the relationship status."""
        status = self.get_relationship_status(npc_id)
        relationships = self.evolution_system.relationships["relationship_types"]
        
        if status in relationships:
            return relationships[status]["color"]
        
        return "#757575"  # Default gray for neutral
    
    def get_relationship_effects(self, npc_id: str) -> Dict[str, Any]:
        """Get the effects of the current relationship on interactions."""
        status = self.get_relationship_status(npc_id)
        
        effects = {
            "price_modifier": 1.0,
            "info_quality": 1.0,
            "aggression_modifier": 1.0,
            "trust_level": 0
        }
        
        if status == "trusted":
            effects.update({
                "price_modifier": 0.8,  # 20% discount
                "info_quality": 1.5,   # Better information
                "aggression_modifier": 0.5,  # Less aggressive
                "trust_level": 100
            })
        elif status == "ally":
            effects.update({
                "price_modifier": 0.9,
                "info_quality": 1.2,
                "aggression_modifier": 0.7,
                "trust_level": 75
            })
        elif status == "friendly":
            effects.update({
                "price_modifier": 0.95,
                "info_quality": 1.1,
                "aggression_modifier": 0.8,
                "trust_level": 50
            })
        elif status == "hostile":
            effects.update({
                "price_modifier": 1.3,  # 30% markup
                "info_quality": 0.7,   # Worse information
                "aggression_modifier": 1.5,  # More aggressive
                "trust_level": -50
            })
        elif status == "enemy":
            effects.update({
                "price_modifier": 1.5,  # 50% markup
                "info_quality": 0.5,
                "aggression_modifier": 2.0,
                "trust_level": -100
            })
        
        return effects


# Example usage and testing functions
def test_evolution_system():
    """Test the evolution system."""
    integration = NPCIntegrationSystem()
    
    # Test NPC evolution
    print("Testing NPC evolution...")
    results = integration.evolve_all_npcs(current_day=5)
    
    for npc_id, result in results.items():
        if result["evolved"]:
            print(f"{npc_id}: Evolved from {result['old_power']} to {result['new_power']} power")
            if result["new_traits"]:
                print(f"  New traits: {', '.join(result['new_traits'])}")
    
    # Test relationship system
    print("\nTesting relationship system...")
    relationship_result = integration.update_player_relationship("nox", "help_npc", 20)
    print(f"Relationship update: {relationship_result}")
    
    # Test conversation system
    print("\nTesting conversation system...")
    player_data = {
        "money": 5000,
        "day": 5,
        "health": 80,
        "gang_members": ["member1", "member2"]
    }
    
    response = integration.get_npc_response("nox", "squidies", player_data)
    print(f"NPC response: {response['text']}")
    
    # Test greeting generation
    greeting = integration.generate_npc_greeting("nox", player_data)
    print(f"Dynamic greeting: {greeting}")
    
    # Get evolution report
    report = integration.get_evolution_report()
    print(f"\nEvolution report: {report}")


if __name__ == "__main__":
    test_evolution_system()