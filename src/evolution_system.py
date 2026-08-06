import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

class EvolutionEventType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

@dataclass
class EvolutionEvent:
    name: str
    description: str
    event_type: EvolutionEventType
    power_change: int = 0
    trait_chance: float = 0.0
    ally_gain: bool = False
    ally_loss: bool = False
    wealth_gain: int = 0
    impairment: bool = False
    location_change: bool = False
    secrecy_increase: bool = False
    wisdom_gain: int = 0

class EvolutionSystem:
    def __init__(self, config_path: str = "model/npc_evolution_config.json"):
        """Initialize the evolution system with configuration."""
        with open(config_path, 'r') as f:
            self.config = json.load(f)["npc_evolution_system"]
        
        self.power_levels = self.config["power_levels"]["levels"]
        self.traits = self._build_trait_dict()
        self.relationships = self.config["relationships"]
        self.events = self._build_event_dict()
    
    def _build_trait_dict(self) -> Dict[str, Dict]:
        """Build a unified trait dictionary from config."""
        traits = {}
        for trait_list in [self.config["traits"]["positive_traits"], 
                          self.config["traits"]["negative_traits"], 
                          self.config["traits"]["neutral_traits"]]:
            for trait in trait_list:
                traits[trait["name"]] = trait
        return traits
    
    def _build_event_dict(self) -> Dict[str, EvolutionEvent]:
        """Build event dictionary from config."""
        events = {}
        for event_type in ["positive_events", "negative_events", "neutral_events"]:
            for event_data in self.config["evolution_events"][event_type]:
                event_type_enum = EvolutionEventType(event_type.replace("_events", ""))
                event = EvolutionEvent(
                    name=event_data["name"],
                    description=event_data["description"],
                    event_type=event_type_enum,
                    power_change=event_data.get("power_gain", 0) - event_data.get("power_loss", 0),
                    trait_chance=event_data.get("trait_chance", 0.0),
                    ally_gain=event_data.get("ally_gain", False),
                    ally_loss=event_data.get("ally_loss", False),
                    wealth_gain=event_data.get("wealth_gain", 0),
                    impairment=event_data.get("impairment", False),
                    location_change=event_data.get("location_change", False),
                    secrecy_increase=event_data.get("secrecy_increase", False),
                    wisdom_gain=event_data.get("wisdom_gain", 0)
                )
                events[event.name] = event
        return events
    
    def get_power_level_name(self, power: int) -> str:
        """Get the power level name for a given power value."""
        for level in reversed(self.power_levels):
            if power >= level["min_power"]:
                return level["name"]
        return self.power_levels[0]["name"]
    
    def get_power_level_multiplier(self, power: int) -> Tuple[float, float]:
        """Get HP and damage multipliers for a given power level."""
        for level in reversed(self.power_levels):
            if power >= level["min_power"]:
                return level["hp_multiplier"], level["damage_multiplier"]
        return self.power_levels[0]["hp_multiplier"], self.power_levels[0]["damage_multiplier"]
    
    def should_evolve_npc(self, npc: Dict[str, Any], current_day: int) -> bool:
        """Determine if an NPC should evolve based on various triggers."""
        evolution_config = self.config["evolution_triggers"]
        
        # Time-based evolution
        if evolution_config["time_based"]["enabled"]:
            last_evolution = npc.get("evolution", {}).get("memory", {}).get("last_evolution", "2026-01-01")
            last_date = datetime.strptime(last_evolution, "%Y-%m-%d")
            days_since = (datetime.now() - last_date).days
            
            if days_since >= evolution_config["time_based"]["days_between_evolution"]:
                if random.random() < evolution_config["time_based"]["chance_per_npc_per_day"]:
                    return True
        
        # Player interaction-based evolution
        if evolution_config["player_interaction"]["enabled"]:
            player_relationship = npc.get("evolution", {}).get("relationships", {}).get("player", 0)
            if abs(player_relationship) >= evolution_config["player_interaction"]["relationship_threshold"]:
                return True
        
        # Combat outcome-based evolution
        if evolution_config["combat_outcomes"]["enabled"]:
            # Check for win/loss streaks in memory
            significant_events = npc.get("evolution", {}).get("memory", {}).get("significant_events", [])
            recent_combat = [e for e in significant_events if e["type"] in ["combat_victory", "combat_defeat"]]
            recent_combat = recent_combat[-5:]  # Last 5 combat events
            
            if len(recent_combat) >= evolution_config["combat_outcomes"]["win_streak_trigger"]:
                victories = sum(1 for e in recent_combat if e["type"] == "combat_victory")
                if victories >= evolution_config["combat_outcomes"]["win_streak_trigger"]:
                    return True
            
            if len(recent_combat) >= evolution_config["combat_outcomes"]["loss_streak_trigger"]:
                defeats = sum(1 for e in recent_combat if e["type"] == "combat_defeat")
                if defeats >= evolution_config["combat_outcomes"]["loss_streak_trigger"]:
                    return True
        
        return False
    
    def evolve_npc(self, npc: Dict[str, Any], current_day: int) -> Dict[str, Any]:
        """Evolve an NPC based on current conditions."""
        if not self.should_evolve_npc(npc, current_day):
            return npc
        
        # Create evolution data if it doesn't exist
        if "evolution" not in npc:
            npc["evolution"] = {
                "power_level": 100,
                "evolution_points": 0,
                "traits": [],
                "relationships": {"player": 0},
                "memory": {
                    "last_evolution": datetime.now().strftime("%Y-%m-%d"),
                    "significant_events": [],
                    "player_interactions": []
                },
                "status_effects": [],
                "location_history": [npc.get("location", "unknown")],
                "evolution_stage": "Weak"
            }
        
        evolution_data = npc["evolution"]
        
        # Determine evolution event type based on current state
        event_type = self._determine_event_type(evolution_data)
        available_events = [e for e in self.events.values() if e.event_type == event_type]
        
        if not available_events:
            return npc
        
        # Select random event
        selected_event = random.choice(available_events)
        
        # Apply event effects
        self._apply_event_effects(npc, selected_event, current_day)
        
        # Update evolution stage
        evolution_data["evolution_stage"] = self.get_power_level_name(evolution_data["power_level"])
        
        # Update last evolution date
        evolution_data["memory"]["last_evolution"] = datetime.now().strftime("%Y-%m-%d")
        
        return npc
    
    def _determine_event_type(self, evolution_data: Dict[str, Any]) -> EvolutionEventType:
        """Determine what type of evolution event should occur."""
        # Base probability distribution
        if evolution_data["power_level"] < 200:
            # Weak NPCs more likely to have negative events
            roll = random.random()
            if roll < 0.4:
                return EvolutionEventType.NEGATIVE
            elif roll < 0.7:
                return EvolutionEventType.NEUTRAL
            else:
                return EvolutionEventType.POSITIVE
        elif evolution_data["power_level"] > 500:
            # Strong NPCs more likely to have positive events
            roll = random.random()
            if roll < 0.5:
                return EvolutionEventType.POSITIVE
            elif roll < 0.8:
                return EvolutionEventType.NEUTRAL
            else:
                return EvolutionEventType.NEGATIVE
        else:
            # Average NPCs have balanced events
            roll = random.random()
            if roll < 0.33:
                return EvolutionEventType.POSITIVE
            elif roll < 0.66:
                return EvolutionEventType.NEUTRAL
            else:
                return EvolutionEventType.NEGATIVE
    
    def _apply_event_effects(self, npc: Dict[str, Any], event: EvolutionEvent, current_day: int):
        """Apply the effects of an evolution event to an NPC."""
        evolution_data = npc["evolution"]
        
        # Apply power changes
        evolution_data["power_level"] = max(0, evolution_data["power_level"] + event.power_change)
        
        # Apply wealth changes (if NPC has inventory)
        if hasattr(npc, 'drugs') and event.wealth_gain > 0:
            # Add random drugs based on wealth gain
            drug_types = list(npc["drugs"].keys())
            for _ in range(event.wealth_gain // 100):
                drug = random.choice(drug_types)
                npc["drugs"][drug] = npc["drugs"].get(drug, 0) + random.randint(1, 3)
        
        # Apply trait changes
        if event.trait_chance > 0 and random.random() < event.trait_chance:
            available_traits = [t for t in self.traits.keys() if t not in evolution_data["traits"]]
            if available_traits:
                new_trait = random.choice(available_traits)
                evolution_data["traits"].append(new_trait)
        
        # Apply ally changes
        if event.ally_gain:
            evolution_data["relationships"]["new_ally"] = 50
        elif event.ally_loss:
            # Remove a random ally
            allies = [name for name, rel in evolution_data["relationships"].items() if rel > 30 and name != "player"]
            if allies:
                ally_to_remove = random.choice(allies)
                del evolution_data["relationships"][ally_to_remove]
        
        # Apply impairment
        if event.impairment:
            if "addicted" not in evolution_data["traits"]:
                evolution_data["traits"].append("Addicted")
            evolution_data["status_effects"].append("withdrawal")
        
        # Apply location changes
        if event.location_change:
            # This would be handled by the main game logic
            pass
        
        # Apply secrecy increase
        if event.secrecy_increase:
            if "Secretive" not in evolution_data["traits"]:
                evolution_data["traits"].append("Secretive")
        
        # Apply wisdom gain
        if event.wisdom_gain > 0:
            if "Wise" not in evolution_data["traits"]:
                evolution_data["traits"].append("Wise")
        
        # Record the event
        evolution_data["memory"]["significant_events"].append({
            "type": "evolution_event",
            "description": event.description,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "impact": abs(event.power_change)
        })
    
    def update_npc_relationship(self, npc: Dict[str, Any], player_action: str, impact: int) -> Dict[str, Any]:
        """Update NPC relationship with player based on actions."""
        if "evolution" not in npc:
            return npc
        
        evolution_data = npc["evolution"]
        relationships = evolution_data["relationships"]
        
        # Get relationship change from config
        change_value = self.relationships["relationship_changes"].get(player_action, 0)
        change_value *= (impact / 10.0)  # Scale by impact
        
        # Apply relationship change
        current_relationship = relationships.get("player", 0)
        new_relationship = max(-100, min(100, current_relationship + change_value))
        relationships["player"] = new_relationship
        
        # Record interaction in memory
        evolution_data["memory"]["player_interactions"].append({
            "action": player_action,
            "impact": impact,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "relationship_before": current_relationship,
            "relationship_after": new_relationship
        })
        
        # Keep only last 20 interactions
        if len(evolution_data["memory"]["player_interactions"]) > 20:
            evolution_data["memory"]["player_interactions"] = evolution_data["memory"]["player_interactions"][-20:]
        
        return npc
    
    def get_npc_relationship_status(self, npc: Dict[str, Any]) -> str:
        """Get the relationship status with the player."""
        if "evolution" not in npc:
            return "neutral"
        
        player_rel = npc["evolution"]["relationships"].get("player", 0)
        
        for status, bounds in self.relationships["relationship_types"].items():
            if bounds["min"] <= player_rel <= bounds["max"]:
                return status
        
        return "neutral"
    
    def apply_trait_effects(self, npc: Dict[str, Any], player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply trait effects to NPC behavior and stats."""
        if "evolution" not in npc:
            return npc
        
        traits = npc["evolution"]["traits"]
        
        # Apply trait effects
        for trait_name in traits:
            if trait_name in self.traits:
                trait = self.traits[trait_name]
                effect = trait["effect"]
                
                if effect == "price_discount" and hasattr(npc, 'drugs'):
                    # Apply price discounts
                    pass  # Would be handled in pricing logic
                elif effect == "info_bonus":
                    # Improve information quality
                    pass  # Would be handled in dialogue logic
                elif effect == "suspicious":
                    # Increase suspicion
                    pass  # Would be handled in interaction logic
        
        return npc
    
    def cleanup_old_memories(self, npc: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up old memories to prevent data bloat."""
        if "evolution" not in npc:
            return npc
        
        evolution_data = npc["evolution"]
        memory = evolution_data["memory"]
        
        # Clean up significant events (keep last 10)
        if len(memory["significant_events"]) > 10:
            memory["significant_events"] = memory["significant_events"][-10:]
        
        # Clean up location history (keep last 5)
        if len(evolution_data["location_history"]) > 5:
            evolution_data["location_history"] = evolution_data["location_history"][-5:]
        
        return npc