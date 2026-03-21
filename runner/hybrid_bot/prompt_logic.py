"""
oCTObot Prompt Logic Layer - LLM-Driven Decision Making

Embeds oCTObot-style prompts for intelligent bot decisions:
  - "If health < X%, cast healing"
  - "If monster engaged, prioritize combat over walking"
  - "If supplies low, return to depot"
  - "If experience stagnant, rotate hunting location"

Decisions are made by encoding game state as prompts and querying LLM.
Fallback: hardcoded if-then rules for offline operation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

log = logging.getLogger("hybrid_bot.prompt_logic")


class Action(Enum):
    """Bot action types."""
    WALK = "walk"
    HEAL = "heal"
    ATTACK = "attack"
    CAST_SPELL = "cast_spell"
    PICKUP_ITEM = "pickup_item"
    EQUIP_ITEM = "equip_item"
    WAIT = "wait"  # Do nothing, pause cavebot
    ROTATE_LOCATION = "rotate_location"  # Go to next hunting spot
    RETURN_TO_DEPOT = "return_to_depot"
    FLEE = "flee"


@dataclass
class GameState:
    """Current game state snapshot for decision making."""
    hp_percent: float
    mp_percent: float
    is_poisoned: bool
    is_engaged: bool
    distance_to_target: Optional[int]  # SQMs
    target_name: Optional[str]
    current_location: str
    xp_per_hour: float
    supplies_cost_per_hour: float
    balance_per_hour: float
    item_count: int
    capacity_percent: float
    time_at_location_minutes: float


@dataclass
class Decision:
    """Decision output from LLM or heuristics."""
    action: Action
    priority: int  # 1=lowest, 10=highest
    reasoning: str
    duration_ms: Optional[int] = None  # How long to hold this action
    parameters: dict = None  # Action-specific params (e.g., spell name)


class PromptLogic:
    """
    oCTObot-style prompt-based decision layer.
    
    Usage:
      1. Snapshot game state
      2. Generate prompt from state
      3. Query LLM (or use fallback heuristics)
      4. Parse decision (action + priority)
      5. Execute action
    """
    
    def __init__(self, use_llm: bool = False, model_name: str = "gpt-3.5-turbo"):
        """
        Initialize prompt logic.
        
        Args:
            use_llm: If True, use LLM for decisions (requires API key)
                     If False, use hardcoded heuristics
            model_name: LLM model to use (e.g., "gpt-3.5-turbo", "gpt-4")
        """
        self.use_llm = use_llm
        self.model_name = model_name
        self.llm_client = None
        
        if use_llm:
            try:
                import openai
                self.llm_client = openai.OpenAI()
            except ImportError:
                log.warning("OpenAI not installed; falling back to heuristics")
                self.use_llm = False
    
    # ─── Heuristic Decision Engine (Always Available) ───────────────────────
    
    def decide_action_heuristic(self, state: GameState) -> Decision:
        """
        Make decision using hardcoded priority rules.
        
        Priority (top to bottom):
          1. Flee if heavily damaged
          2. Heal if critical health
          3. Combat: Attack engaged target
          4. Rotate: Not gaining XP, return to depot
          5. Walk: Continue cavebot path
        """
        # Priority 1: Flee if below 25% HP and engaged
        if state.hp_percent < 25 and state.is_engaged:
            return Decision(
                action=Action.FLEE,
                priority=10,
                reasoning="Critical health while engaged; fleeing to safety",
                duration_ms=5000
            )
        
        # Priority 2: Heal if below 60%
        if state.hp_percent < 60:
            spell = "exura gran" if state.hp_percent < 30 else "exura"
            return Decision(
                action=Action.HEAL,
                priority=9,
                reasoning=f"Health critical ({state.hp_percent:.0f}%); casting {spell}",
                parameters={"spell": spell}
            )
        
        # Priority 3: Attack if engaged with target
        if state.is_engaged and state.target_name:
            return Decision(
                action=Action.ATTACK,
                priority=8,
                reasoning=f"Enemy engaged: {state.target_name} at {state.distance_to_target}sqm",
                duration_ms=2000
            )
        
        # Priority 4: Depop if at 90% capacity
        if state.capacity_percent > 90:
            return Decision(
                action=Action.RETURN_TO_DEPOT,
                priority=7,
                reasoning=f"Capacity critical ({state.capacity_percent:.0f}%); returning to depot",
                duration_ms=30000
            )
        
        # Priority 5: Rotate locations if XP stagnant
        xp_threshold = 50  # XP/hour considered stagnant
        if state.xp_per_hour < xp_threshold and state.time_at_location_minutes > 45:
            return Decision(
                action=Action.ROTATE_LOCATION,
                priority=6,
                reasoning=f"XP stagnant ({state.xp_per_hour:.0f}/hr < {xp_threshold}); rotating location",
                duration_ms=60000
            )
        
        # Priority 6: Continue cavebot (walk)
        return Decision(
            action=Action.WALK,
            priority=5,
            reasoning=f"Following cavebot path at {state.current_location} (XP: {state.xp_per_hour:.0f}/hr)"
        )
    
    # ─── LLM-Based Decision Engine (Optional) ──────────────────────────────
    
    def decide_action_with_llm(self, state: GameState) -> Optional[Decision]:
        """
        Query LLM for intelligent decision based on game state.
        
        Falls back to heuristics if LLM unavailable or fails.
        """
        if not self.use_llm or not self.llm_client:
            return None
        
        # Build prompt
        prompt = self._build_state_prompt(state)
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Low temp for consistent decisions
                max_tokens=200,
            )
            
            content = response.choices[0].message.content
            decision = self._parse_llm_response(content)
            return decision
        
        except Exception as e:
            log.warning(f"LLM query failed: {e}; using heuristics")
            return None
    
    # ─── Main Decision API ────────────────────────────────────────────────
    
    def make_decision(self, state: GameState) -> Decision:
        """
        Make bot decision: try LLM, fall back to heuristics.
        
        Returns highest-priority action based on current game state.
        """
        # Try LLM first (if enabled)
        if self.use_llm:
            llm_decision = self.decide_action_with_llm(state)
            if llm_decision:
                log.info(f"LLM decision: {llm_decision.action.value} (priority {llm_decision.priority})")
                return llm_decision
        
        # Fall back to heuristics
        heuristic_decision = self.decide_action_heuristic(state)
        log.info(f"Heuristic decision: {heuristic_decision.action.value} (priority {heuristic_decision.priority})")
        return heuristic_decision
    
    # ─── Prompting Helpers ────────────────────────────────────────────────
    
    def _build_state_prompt(self, state: GameState) -> str:
        """Build natural language prompt from game state."""
        return f"""
Game State:
- Health: {state.hp_percent:.0f}%
- Mana: {state.mp_percent:.0f}%
- Poisoned: {state.is_poisoned}
- Engaged in combat: {state.is_engaged}
- Target: {state.target_name or "None"} ({state.distance_to_target or 0} SQM)
- Location: {state.current_location}
- Experience: {state.xp_per_hour:.0f} XP/hr
- Supplies cost: {state.supplies_cost_per_hour:.0f} gold/hr
- Profit: {state.balance_per_hour:.0f} gold/hr
- Items: {state.item_count}
- Capacity: {state.capacity_percent:.0f}%
- Time here: {state.time_at_location_minutes:.0f} min

What should the bot do next? Respond with JSON:
{{
    "action": "walk|heal|attack|cast_spell|flee|rotate_location|return_to_depot",
    "priority": 1-10,
    "reasoning": "Short explanation"
}}
"""
    
    def _get_system_prompt(self) -> str:
        """System prompt for oCTObot LLM personality."""
        return """
You are oCTObot, an intelligent MMORPG bot decision engine for Tibia.

Your role:
1. Analyze real-time game state
2. Prioritize actions based on survival > profit > efficiency
3. Make decisions that maximize experience gain while minimizing risk
4. Adapt to changing game conditions

Decision priorities (high to low):
- FLEE if health < 25% and engaged (survival first)
- HEAL if health < 60% (stay alive)
- ATTACK if engaged with valid target (combat)
- RETURN_TO_DEPOT if capacity > 90% (inventory management)
- ROTATE_LOCATION if XP stagnant (efficiency)
- WALK (continue cavebot path)

Respond ONLY with valid JSON. No explanations before or after JSON.
"""
    
    def _parse_llm_response(self, response: str) -> Optional[Decision]:
        """Parse JSON decision response from LLM."""
        try:
            # Extract JSON from response (in case of extra text)
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]
            
            data = json.loads(json_str)
            
            action = Action(data.get("action", "walk"))
            priority = min(10, max(1, int(data.get("priority", 5))))
            
            return Decision(
                action=action,
                priority=priority,
                reasoning=data.get("reasoning", "")
            )
        except (json.JSONDecodeError, ValueError) as e:
            log.warning(f"Failed to parse LLM response: {e}")
            return None


# ─── Prompt Templates for Specific Scenarios ──────────────────────────────

def prompt_training_mode(level: int, current_xp_percent: float) -> str:
    """Prompt for training/power-leveling scenario."""
    return f"""
You are training a level {level} character. Current training progress: {current_xp_percent:.0f}%.
Maximize experience gain. Ignore profit margins.
Where should the bot hunt? What spells should it use?
"""


def prompt_hunting_profit(balance_per_hour: float) -> str:
    """Prompt for profit-focused hunting."""
    return f"""
Current profit rate: {balance_per_hour:.0f} gold/hour.
This hunt is {'PROFITABLE' if balance_per_hour > 0 else 'LOSING MONEY'}.
Should we continue here or rotate to a better location?
"""


def prompt_resource_management(supplies_cost: float, loot_value: float) -> str:
    """Prompt for supply vs. loot decision."""
    return f"""
Supplies cost: {supplies_cost:.0f} gold/hr
Loot value: {loot_value:.0f} gold/hr
Safety margin: {'SAFE' if loot_value > supplies_cost * 1.5 else 'RISKY'}.
Adjust hunting intensity or location?
"""
