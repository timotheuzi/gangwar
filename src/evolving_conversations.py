import json
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re

class EvolvingConversationSystem:
    def __init__(self, dialogue_config_path: str = "model/npc_dialogues.json"):
        """Initialize the evolving conversation system."""
        with open(dialogue_config_path, 'r') as f:
            self.dialogue_config = json.load(f)
        
        self.conversation_memory = {}
        self.topic_weights = {
            "squidies": 0.8,
            "police": 0.7,
            "weapons": 0.9,
            "money": 0.6,
            "buy": 1.0,
            "fight": 0.8,
            "tech": 0.9,
            "secrets": 0.7,
            "watchers": 0.8,
            "parts": 0.5,
            "bargains": 0.4,
            "rules": 0.6,
            "threats": 0.7,
            "hacking": 0.9,
            "information": 0.8,
            "zone": 0.8,
            "protection": 0.7,
            "stories": 0.6,
            "directions": 0.7,
            "order": 0.8,
            "resistance": 0.9,
            "actions": 0.8,
            "crafting": 0.7,
            "upgrades": 0.6,
            "knowledge": 0.8,
            "warnings": 0.9,
            "protection": 0.7,
            "help": 0.8,
            "story": 0.6,
            "training": 0.7,
            "duel": 0.9,
            "blade": 0.8,
            "woods": 0.6,
            "axe": 0.5,
            "code": 0.8,
            "help": 0.7,
            "company": 0.9,
            "escape": 0.8,
            "fight": 0.9,
            "territory": 0.8,
            "sanctum": 0.9,
            "technology": 0.8,
            "access": 0.7
        }
    
    def get_npc_response(self, npc_id: str, topic: str, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get an evolving response from an NPC based on memory and context."""
        if npc_id not in self.dialogue_config:
            return {"text": "I don't know who you're talking to.", "cost": 0, "effect": None}
        
        npc_data = self.dialogue_config[npc_id]
        
        # Get base responses for the topic
        if topic not in npc_data["topics"]:
            return {"text": "I don't have anything to say about that.", "cost": 0, "effect": None}
        
        topic_data = npc_data["topics"][topic]
        base_responses = topic_data["responses"]
        
        # Get conversation history
        conversation_key = f"{npc_id}_{topic}"
        conversation_history = self.conversation_memory.get(conversation_key, [])
        
        # Calculate response weights based on evolution, memory, and context
        weighted_responses = []
        
        for i, response in enumerate(base_responses):
            weight = self._calculate_response_weight(
                response, 
                npc_data, 
                player_data, 
                conversation_history, 
                i
            )
            weighted_responses.append((response, weight))
        
        # Select response based on weights
        if not weighted_responses:
            return base_responses[0] if base_responses else {"text": "I have nothing to say.", "cost": 0, "effect": None}
        
        # Use weighted random selection
        total_weight = sum(weight for _, weight in weighted_responses)
        if total_weight <= 0:
            return weighted_responses[0][0]
        
        random_value = random.uniform(0, total_weight)
        current_weight = 0
        
        for response, weight in weighted_responses:
            current_weight += weight
            if random_value <= current_weight:
                # Record this interaction
                self._record_conversation(conversation_key, topic, response, player_data)
                return response
        
        return weighted_responses[0][0]
    
    def _calculate_response_weight(self, response: Dict[str, Any], npc_data: Dict[str, Any], 
                                 player_data: Dict[str, Any], conversation_history: List[Dict], 
                                 response_index: int) -> float:
        """Calculate the weight for a response based on various factors."""
        base_weight = 1.0
        
        # Factor 1: Response cost and player wealth
        if "cost" in response:
            cost = response["cost"]
            player_money = player_data.get("money", 0)
            if cost > 0:
                if cost > player_money * 2:  # Very expensive
                    base_weight *= 0.1
                elif cost > player_money:  # Expensive
                    base_weight *= 0.5
                elif cost < player_money * 0.1:  # Cheap
                    base_weight *= 1.5
        
        # Factor 2: Player stats and response conditions
        if "conditions" in response:
            conditions = response["conditions"]
            condition_weight = self._evaluate_conditions(conditions, player_data, npc_data, response)
            base_weight *= condition_weight
        
        # Factor 3: Conversation history (avoid repetition)
        if conversation_history:
            recent_responses = [h["response_text"] for h in conversation_history[-3:]]
            if response["text"] in recent_responses:
                base_weight *= 0.3  # Reduce weight for repeated responses
        
        # Factor 4: NPC evolution and traits
        if "evolution" in npc_data:
            evolution_weight = self._get_evolution_weight(response, npc_data["evolution"], player_data)
            base_weight *= evolution_weight
        
        # Factor 5: Topic relevance and current events
        topic_weight = self._get_topic_weight(response, npc_data, player_data)
        base_weight *= topic_weight
        
        # Factor 6: Random variation
        base_weight *= random.uniform(0.8, 1.2)
        
        return max(base_weight, 0.1)  # Minimum weight to prevent complete exclusion
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], player_data: Dict[str, Any], 
                           npc_data: Dict[str, Any], response: Dict[str, Any]) -> float:
        """Evaluate response conditions and return a weight multiplier."""
        weight = 1.0
        
        # Wealth-based conditions
        if "min_money" in conditions:
            if player_data.get("money", 0) < conditions["min_money"]:
                return 0.0
        
        if "max_money" in conditions:
            if player_data.get("money", 0) > conditions["max_money"]:
                return 0.0
        
        # Gang size conditions
        if "min_members" in conditions:
            if len(player_data.get("gang_members", [])) < conditions["min_members"]:
                return 0.0
        
        if "max_members" in conditions:
            if len(player_data.get("gang_members", [])) > conditions["max_members"]:
                return 0.0
        
        # Health conditions
        if "min_health" in conditions:
            if player_data.get("health", 100) < conditions["min_health"]:
                return 0.0
        
        if "max_health" in conditions:
            if player_data.get("health", 100) > conditions["max_health"]:
                return 0.0
        
        # Day conditions
        if "min_day" in conditions:
            if player_data.get("day", 1) < conditions["min_day"]:
                return 0.0
        
        # Relationship conditions
        if "min_relationship" in conditions:
            # This would need to be implemented with the evolution system
            pass
        
        # Weight factors from response
        if "weight_factors" in response:
            weight_factors = response["weight_factors"]
            
            # Wealth weight
            if "wealth_weight" in weight_factors:
                wealth = player_data.get("money", 0)
                if wealth < 1000:
                    weight *= weight_factors["wealth_weight"].get("poor", 1.0)
                elif wealth < 5000:
                    weight *= weight_factors["wealth_weight"].get("medium", 1.0)
                else:
                    weight *= weight_factors["wealth_weight"].get("rich", 1.0)
            
            # Gang size weight
            if "gang_size_weight" in weight_factors:
                gang_size = len(player_data.get("gang_members", []))
                if gang_size < 3:
                    weight *= weight_factors["gang_size_weight"].get("small", 1.0)
                elif gang_size < 6:
                    weight *= weight_factors["gang_size_weight"].get("medium", 1.0)
                else:
                    weight *= weight_factors["gang_size_weight"].get("large", 1.0)
            
            # Health weight
            if "health_weight" in weight_factors:
                health = player_data.get("health", 100)
                if health < 25:
                    weight *= weight_factors["health_weight"].get("low", 1.0)
                elif health < 75:
                    weight *= weight_factors["health_weight"].get("medium", 1.0)
                else:
                    weight *= weight_factors["health_weight"].get("high", 1.0)
        
        return weight
    
    def _get_evolution_weight(self, response: Dict[str, Any], evolution_data: Dict[str, Any], 
                            player_data: Dict[str, Any]) -> float:
        """Get weight adjustment based on NPC evolution and traits."""
        weight = 1.0
        
        # Power level effects
        power_level = evolution_data.get("power_level", 100)
        if power_level > 500:  # Strong NPCs are more confident
            weight *= 1.2
        elif power_level < 100:  # Weak NPCs are more cautious
            weight *= 0.8
        
        # Trait effects
        traits = evolution_data.get("traits", [])
        
        for trait in traits:
            if trait == "Wise":
                # Wise NPCs provide better information
                if response.get("effect") == "has_info":
                    weight *= 1.5
            
            elif trait == "Generous":
                # Generous NPCs offer better deals
                if response.get("cost", 0) == 0:
                    weight *= 1.3
            
            elif trait == "Greedy":
                # Greedy NPCs charge more
                if response.get("cost", 0) > 0:
                    weight *= 1.2
            
            elif trait == "Paranoid":
                # Paranoid NPCs are suspicious
                if "suspicious" in response.get("text", "").lower():
                    weight *= 1.5
            
            elif trait == "Honorable":
                # Honorable NPCs prefer fair deals
                if response.get("cost", 0) == 0 or "fair" in response.get("text", "").lower():
                    weight *= 1.3
        
        # Relationship with player
        player_relationship = evolution_data.get("relationships", {}).get("player", 0)
        if player_relationship > 50:  # Friendly
            weight *= 1.2
        elif player_relationship < -30:  # Hostile
            weight *= 0.7
        
        return weight
    
    def _get_topic_weight(self, response: Dict[str, Any], npc_data: Dict[str, Any], 
                         player_data: Dict[str, Any]) -> float:
        """Get weight adjustment based on topic relevance and current events."""
        weight = 1.0
        
        # Time-based weighting
        current_hour = datetime.now().hour
        if 6 <= current_hour <= 12:  # Morning
            if "morning" in response.get("text", "").lower():
                weight *= 1.3
        elif 13 <= current_hour <= 18:  # Afternoon
            if "afternoon" in response.get("text", "").lower():
                weight *= 1.3
        else:  # Evening/Night
            if "night" in response.get("text", "").lower():
                weight *= 1.3
        
        # Recent events in player data
        recent_events = player_data.get("recent_events", [])
        for event in recent_events[-3:]:  # Last 3 events
            if event.get("type") == "combat" and "fight" in response.get("text", "").lower():
                weight *= 1.4
            elif event.get("type") == "purchase" and "buy" in response.get("text", "").lower():
                weight *= 1.4
            elif event.get("type") == "information" and "know" in response.get("text", "").lower():
                weight *= 1.4
        
        return weight
    
    def _record_conversation(self, conversation_key: str, topic: str, response: Dict[str, Any], 
                           player_data: Dict[str, Any]):
        """Record a conversation for future reference."""
        if conversation_key not in self.conversation_memory:
            self.conversation_memory[conversation_key] = []
        
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "response_text": response["text"],
            "response_cost": response.get("cost", 0),
            "response_effect": response.get("effect"),
            "player_money": player_data.get("money", 0),
            "player_day": player_data.get("day", 1),
            "player_health": player_data.get("health", 100)
        }
        
        self.conversation_memory[conversation_key].append(conversation_entry)
        
        # Keep only last 10 conversations per topic
        if len(self.conversation_memory[conversation_key]) > 10:
            self.conversation_memory[conversation_key] = self.conversation_memory[conversation_key][-10:]
    
    def get_memory_summary(self, npc_id: str, topic: str) -> Dict[str, Any]:
        """Get a summary of conversation memory for an NPC and topic."""
        conversation_key = f"{npc_id}_{topic}"
        history = self.conversation_memory.get(conversation_key, [])
        
        if not history:
            return {
                "total_conversations": 0,
                "last_conversation": None,
                "average_cost": 0,
                "common_topics": [],
                "player_relationship_trend": "neutral"
            }
        
        # Calculate summary statistics
        total_cost = sum(entry.get("response_cost", 0) for entry in history)
        average_cost = total_cost / len(history)
        
        # Get common response themes
        response_texts = [entry["response_text"] for entry in history]
        common_words = self._get_common_words(response_texts)
        
        # Determine relationship trend
        relationship_trend = self._calculate_relationship_trend(history)
        
        return {
            "total_conversations": len(history),
            "last_conversation": history[-1]["timestamp"],
            "average_cost": round(average_cost, 2),
            "common_topics": common_words[:5],
            "player_relationship_trend": relationship_trend,
            "recent_responses": [entry["response_text"] for entry in history[-3:]]
        }
    
    def _get_common_words(self, texts: List[str]) -> List[str]:
        """Extract common words from response texts."""
        word_freq = {}
        for text in texts:
            words = re.findall(r'\b\w+\b', text.lower())
            for word in words:
                if len(word) > 3:  # Ignore short words
                    word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top 10 most common words
        return sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)
    
    def _calculate_relationship_trend(self, history: List[Dict]) -> str:
        """Calculate the trend of player relationship based on conversation history."""
        if len(history) < 3:
            return "neutral"
        
        # Simple trend analysis based on response costs and effects
        positive_interactions = sum(1 for entry in history 
                                  if entry.get("response_cost", 0) == 0 or 
                                  entry.get("response_effect") == "has_info")
        negative_interactions = sum(1 for entry in history 
                                  if entry.get("response_cost", 0) > 1000)
        
        if positive_interactions > negative_interactions * 2:
            return "improving"
        elif negative_interactions > positive_interactions * 2:
            return "worsening"
        else:
            return "stable"
    
    def generate_dynamic_greeting(self, npc_id: str, player_data: Dict[str, Any]) -> str:
        """Generate a dynamic greeting based on NPC evolution and player history."""
        if npc_id not in self.dialogue_config:
            return "Hello."
        
        npc_data = self.dialogue_config[npc_id]
        greetings = npc_data.get("greetings", ["Hello."])
        
        # Get conversation history
        conversation_key = f"{npc_id}_general"
        history = self.conversation_memory.get(conversation_key, [])
        
        # Select greeting based on relationship and history
        if history:
            # Use more personalized greeting if there's history
            recent_greetings = [h for h in history if h.get("topic") == "greeting"]
            if len(recent_greetings) > 3:
                # Long-term relationship
                return random.choice([
                    f"Ah, {player_data.get('name', 'friend')}, back again I see.",
                    "Welcome back. The streets have been quiet without you.",
                    "You look like you've been through some things. Care to share?"
                ])
            else:
                # Recent interactions
                return random.choice([
                    "Good to see you again.",
                    "What brings you back this way?",
                    "You look like you need something."
                ])
        else:
            # First time meeting
            return random.choice(greetings)
    
    def cleanup_old_conversations(self, max_age_days: int = 30):
        """Clean up old conversation memory to prevent data bloat."""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for conversation_key in list(self.conversation_memory.keys()):
            history = self.conversation_memory[conversation_key]
            # Keep only recent conversations
            recent_history = [h for h in history 
                            if datetime.fromisoformat(h["timestamp"]) > cutoff_date]
            
            if recent_history:
                self.conversation_memory[conversation_key] = recent_history
            else:
                del self.conversation_memory[conversation_key]