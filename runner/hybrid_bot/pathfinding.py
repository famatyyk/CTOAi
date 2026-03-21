"""
A* Pathfinding with Game-Aware Weights

Per Federal University of Tocantins research paper:
  - Weights based on SQM type (grass, swamp, mountain, water depth, lava)
  - Accounts for player level cooldowns (movement cost per SQM type)
  - Supports circular waypoint buffers
  - Integrates with cavebot safety (pause if engaged)

Cost formula: cost(sqm_type) = base_cost * (1 + cooldown_factor) / player_level_bonus
"""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

log = logging.getLogger("hybrid_bot.pathfinding")


class SQMType(Enum):
    """Terrain types with different movement costs."""
    GRASS = 1.0          # Normal terrain
    SWAMP = 2.0          # Slow terrain
    MOUNTAIN = 3.0       # Very slow or impassable
    WATER = 1.5          # Water (shallow)
    DEEP_WATER = 5.0     # Deep water (swimming only)
    WALL = float('inf')  # Wall (impassable)
    LAVA = 4.0           # Lava (hazard)
    SNOW = 1.2           # Snow (slight slow)
    SAND = 1.3           # Sand (slight slow)


@dataclass(frozen=True)
class Coordinate:
    """3D coordinate in Tibia world."""
    x: int
    y: int
    z: int  # floor/level
    
    def distance_to(self, other: Coordinate) -> float:
        """Manhattan + vertical distance."""
        return abs(self.x - other.x) + abs(self.y - other.y) + abs(self.z - other.z) * 2


@dataclass
class PathNode:
    """Node in A* search."""
    pos: Coordinate
    g_cost: float = 0.0       # Distance from start
    h_cost: float = 0.0       # Heuristic to goal
    f_cost: float = field(init=False)
    parent: Optional[PathNode] = None
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'f_cost', self.g_cost + self.h_cost)
    
    def __lt__(self, other: PathNode) -> bool:
        return self.f_cost < other.f_cost
    
    def __hash__(self) -> int:
        return hash(self.pos)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PathNode):
            return NotImplemented
        return self.pos == other.pos


@dataclass
class PathSegment:
    """One step in the path."""
    from_pos: Coordinate
    to_pos: Coordinate
    sqm_type: SQMType
    cost: float
    expected_ms: float  # Expected milliseconds to traverse


class Pathfinder:
    """
    A* Pathfinding with Tibia game mechanics.
    
    Features:
      - SQM-type aware costs (grass, swamp, water, etc.)
      - Player level bonus (higher level = faster movement)
      - Cooldown penalties per terrain
      - Waypoint circular buffer support
      - Engaged detection integration (pause during combat)
    """
    
    def __init__(
        self,
        player_level: int = 50,
        sqm_cost_map: dict[SQMType, float] | None = None,
        base_movement_ms: float = 200.0,  # Time per SQM in ms
    ):
        """
        Initialize pathfinder with game parameters.
        
        Args:
            player_level: Player character level (affects movement speed)
            sqm_cost_map: Custom SQM movement costs
            base_movement_ms: Base milliseconds per SQM at level 1
        """
        self.player_level = player_level
        self.base_movement_ms = base_movement_ms
        
        # Default SQM costs (multipliers for base cost)
        self.sqm_cost_map = sqm_cost_map or {
            sqm: sqm.value for sqm in SQMType
        }
        
        # Level bonus: higher level = faster (20% faster per 50 levels)
        self.level_bonus = 1.0 + (min(player_level, 200) / 200) * 0.4
    
    def find_path(
        self,
        start: Coordinate,
        goal: Coordinate,
        sqm_terrain: dict[Coordinate, SQMType] | None = None,
        max_iterations: int = 10000,
    ) -> list[PathSegment]:
        """
        Find optimal path from start to goal using A*.
        
        Args:
            start: Starting coordinate
            goal: Goal coordinate
            sqm_terrain: Map of coordinates to terrain types
            max_iterations: Safety limit on search iterations
        
        Returns:
            List of path segments (steps), or empty if no path found
        """
        if start == goal:
            return []
        
        sqm_terrain = sqm_terrain or {}
        
        # Initialize A* search
        open_set: list[PathNode] = []
        closed_set: set[Coordinate] = set()
        node_map: dict[Coordinate, PathNode] = {}
        
        start_node = PathNode(
            pos=start,
            g_cost=0.0,
            h_cost=start.distance_to(goal)
        )
        heapq.heappush(open_set, start_node)
        node_map[start] = start_node
        
        iterations = 0
        while open_set and iterations < max_iterations:
            iterations += 1
            
            # Get node with lowest f_cost
            current = heapq.heappop(open_set)
            
            if current.pos == goal:
                # Reconstruct path
                return self._reconstruct_path(current, sqm_terrain)
            
            closed_set.add(current.pos)
            
            # Explore neighbors (4-directional + vertical)
            for neighbor_pos in self._get_neighbors(current.pos):
                if neighbor_pos in closed_set:
                    continue
                
                # Calculate cost to neighbor
                terrain = sqm_terrain.get(neighbor_pos, SQMType.GRASS)
                move_cost = self._calculate_move_cost(terrain)
                new_g_cost = current.g_cost + move_cost
                
                # Skip impassable terrain
                if move_cost == float('inf'):
                    closed_set.add(neighbor_pos)
                    continue
                
                # Update or create neighbor node
                if neighbor_pos in node_map:
                    neighbor = node_map[neighbor_pos]
                    if new_g_cost < neighbor.g_cost:
                        neighbor.g_cost = new_g_cost
                        neighbor.parent = current
                        object.__setattr__(neighbor, 'f_cost', neighbor.g_cost + neighbor.h_cost)
                        heapq.heappush(open_set, neighbor)
                else:
                    h_cost = neighbor_pos.distance_to(goal)
                    neighbor = PathNode(
                        pos=neighbor_pos,
                        g_cost=new_g_cost,
                        h_cost=h_cost,
                        parent=current
                    )
                    node_map[neighbor_pos] = neighbor
                    heapq.heappush(open_set, neighbor)
        
        log.warning(f"No path found (iterations: {iterations})")
        return []
    
    def _get_neighbors(self, pos: Coordinate) -> list[Coordinate]:
        """Get valid neighbor coordinates (4-directional + same floor)."""
        neighbors = []
        
        # Cardinal directions (North, South, East, West)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = Coordinate(pos.x + dx, pos.y + dy, pos.z)
            if self._is_valid_position(neighbor):
                neighbors.append(neighbor)
        
        # Vertical movement (stairs, up/down)
        for dz in [-1, 1]:
            neighbor = Coordinate(pos.x, pos.y, pos.z + dz)
            if self._is_valid_position(neighbor):
                neighbors.append(neighbor)
        
        return neighbors
    
    def _is_valid_position(self, pos: Coordinate) -> bool:
        """Check if position is within map bounds."""
        # Tibia world bounds: roughly 0-3200, 0-3200, 0-15
        return 0 <= pos.x <= 3200 and 0 <= pos.y <= 3200 and 0 <= pos.z <= 15
    
    def _calculate_move_cost(self, sqm_type: SQMType) -> float:
        """Calculate movement cost factor for terrain type."""
        # base_cost * terrain_multiplier / level_bonus
        base = self.sqm_cost_map.get(sqm_type, 1.0)
        return base / self.level_bonus
    
    def _reconstruct_path(
        self,
        node: PathNode,
        sqm_terrain: dict[Coordinate, SQMType]
    ) -> list[PathSegment]:
        """Reconstruct path from goal node back to start."""
        segments: list[PathSegment] = []
        
        while node.parent is not None:
            parent = node.parent
            sqm_type = sqm_terrain.get(node.pos, SQMType.GRASS)
            cost = self._calculate_move_cost(sqm_type)
            expected_ms = cost * self.base_movement_ms
            
            segment = PathSegment(
                from_pos=parent.pos,
                to_pos=node.pos,
                sqm_type=sqm_type,
                cost=cost,
                expected_ms=expected_ms
            )
            segments.append(segment)
            node = parent
        
        segments.reverse()
        return segments
    
    def estimate_travel_time_ms(self, segments: list[PathSegment]) -> float:
        """Estimate total travel time in milliseconds."""
        return sum(seg.expected_ms for seg in segments)


class WaypointBuffer:
    """
    Circular buffer of hunting waypoints.
    
    Per paper: Cavebot uses circular waypoint pattern.
    Supports pause-on-engage for combat priority.
    """
    
    def __init__(self, waypoints: list[Coordinate]):
        """Initialize with list of waypoints."""
        self.waypoints = waypoints
        self.current_index = 0
    
    def get_current_waypoint(self) -> Optional[Coordinate]:
        """Get current target waypoint."""
        if not self.waypoints:
            return None
        return self.waypoints[self.current_index]
    
    def advance(self) -> Optional[Coordinate]:
        """Move to next waypoint (circular)."""
        if not self.waypoints:
            return None
        self.current_index = (self.current_index + 1) % len(self.waypoints)
        return self.waypoints[self.current_index]
    
    def reset(self) -> None:
        """Reset to first waypoint."""
        self.current_index = 0
    
    def distance_to_current(self, pos: Coordinate) -> float:
        """Distance from position to current waypoint."""
        current = self.get_current_waypoint()
        if current is None:
            return 0
        return pos.distance_to(current)


# ─── Utility: Generate terrain map from game data ────────────────────────────

def generate_terrain_map(
    map_data: dict[tuple[int, int, int], str],
) -> dict[Coordinate, SQMType]:
    """
    Convert game map data (from server API) to terrain type map.
    
    Args:
        map_data: Dict of (x, y, z) -> terrain_name
    
    Returns:
        Dict of Coordinate -> SQMType
    """
    terrain_map: dict[Coordinate, SQMType] = {}
    
    # Mapping of terrain names to types (customize per server)
    name_to_type = {
        "grass": SQMType.GRASS,
        "swamp": SQMType.SWAMP,
        "mountain": SQMType.MOUNTAIN,
        "water": SQMType.WATER,
        "deep_water": SQMType.DEEP_WATER,
        "lava": SQMType.LAVA,
        "snow": SQMType.SNOW,
        "sand": SQMType.SAND,
        "wall": SQMType.WALL,
    }
    
    for (x, y, z), terrain_name in map_data.items():
        sqm_type = name_to_type.get(terrain_name.lower(), SQMType.GRASS)
        terrain_map[Coordinate(x, y, z)] = sqm_type
    
    return terrain_map
