"""
Vision Layer - Template Matching for Game State Detection

Per Federal University of Tocantins research paper:
  - GPS Algorithm: Minimap template matching (resized 25% for speed)
  - Healing Algorithm: Pixel color detection on health bar
  - Target Algorithm: Creature sprite template matching

Dependencies: opencv-python, numpy
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

log = logging.getLogger("hybrid_bot.vision")


def _vision_deps_available() -> bool:
    return cv2 is not None and np is not None


@dataclass
class GPSPosition:
    """Game world coordinates from template matching."""
    x: int
    y: int
    z: int  # floor/level
    confidence: float  # 0.0-1.0 match score


@dataclass
class HealthState:
    """Player health detected from pixel analysis on health bar."""
    hp_percent: float  # 0.0-100.0
    is_critical: bool  # True if red/pink pixels detected
    is_poisoned: bool  # Detection based on green overlay


@dataclass
class TargetInfo:
    """Detected monster from creature sprite template matching."""
    name: str
    x: int
    y: int
    distance: int  # in SQMs
    is_engaged: bool  # Red/pink outline in target window
    confidence: float  # Template match score


class VisionLayer:
    """
    Template matching based vision system.
    
    Optimizations per research paper:
      - Resize images to 25% for faster matching
      - Preload and cache templates
      - Use multi-scale matching for robustness
    """
    
    def __init__(self, templates_dir: Path | str | None = None):
        """Initialize vision layer with template cache."""
        self.templates_dir = Path(templates_dir) if templates_dir else Path.cwd() / "templates"
        self.minimap_templates: dict[str, np.ndarray] = {}
        self.creature_templates: dict[str, np.ndarray] = {}
        self.ui_templates: dict[str, np.ndarray] = {}
        
        # Cache for speed optimization
        self._gps_cache: Optional[GPSPosition] = None
        self._health_cache: Optional[HealthState] = None

        if not _vision_deps_available():
            log.warning("Vision dependencies unavailable; running in degraded mode (no template matching)")
            return

        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load and cache all template images (25% resized)."""
        if not self.templates_dir.exists():
            log.warning(f"Templates directory not found: {self.templates_dir}")
            return
        
        # Example: load gameworld map sections as templates
        for tmpl_file in self.templates_dir.glob("minimap_*.png"):
            try:
                img = cv2.imread(str(tmpl_file), cv2.IMREAD_COLOR)
                if img is not None:
                    # Resize to 25% per paper optimization
                    small = cv2.resize(img, None, fx=0.25, fy=0.25)
                    self.minimap_templates[tmpl_file.stem] = small
                    log.debug(f"Loaded template: {tmpl_file.stem}")
            except Exception as e:
                log.warning(f"Failed to load {tmpl_file}: {e}")
    
    # ─── GPS Algorithm (Position Detection) ────────────────────────────────────
    
    def detect_position_from_minimap(self, minimap_screenshot: np.ndarray) -> Optional[GPSPosition]:
        """
        GPS Algorithm: Template match minimap vs preloaded map sections.
        
        Per paper: Minimap resized to 25% of actual size for speed.
        Returns global coordinates (x, y, z/floor).
        """
        if not _vision_deps_available():
            return self._gps_cache

        if minimap_screenshot is None or minimap_screenshot.size == 0:
            log.warning("Empty minimap screenshot")
            return None
        
        # Resize screenshot to 25% to match template size
        small_minimap = cv2.resize(minimap_screenshot, None, fx=0.25, fy=0.25)
        
        best_match: Optional[Tuple[str, float, tuple]] = None
        best_score = 0.0
        
        # Compare against all cached templates
        for template_name, template in self.minimap_templates.items():
            try:
                # Template matching (cv2.TM_CCOEFF_NORMED gives 0.0-1.0 score)
                result = cv2.matchTemplate(small_minimap, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_score:
                    best_score = max_val
                    best_match = (template_name, max_val, max_loc)
            except cv2.error as e:
                log.debug(f"Template match failed for {template_name}: {e}")
                continue
        
        if best_match and best_score > 0.7:  # Confidence threshold
            template_name, score, (px, py) = best_match
            
            # Parse world coords from template name (e.g., "minimap_1000_2000_7")
            parts = template_name.split("_")
            if len(parts) >= 4:
                try:
                    base_x = int(parts[1]) + px * 4  # Undo 25% resize
                    base_y = int(parts[2]) + py * 4
                    base_z = int(parts[3])
                    
                    pos = GPSPosition(x=base_x, y=base_y, z=base_z, confidence=score)
                    log.info(f"GPS detected: {pos}")
                    self._gps_cache = pos
                    return pos
                except ValueError:
                    log.warning(f"Could not parse coords from template: {template_name}")
        
        log.debug(f"No reliable position found (best: {best_score:.2f})")
        return self._gps_cache  # Return cached position if no new match
    
    # ─── Healing Algorithm (Health Bar Detection) ──────────────────────────────
    
    def detect_health_from_healthbar(self, healthbar_region: np.ndarray) -> HealthState:
        """
        Healing Algorithm: Detect health by pixel color on health bar.
        
        Per paper: Check for red/pink pixels (hit/need heal).
        Returns HP percentage and critical status.
        """
        if not _vision_deps_available():
            return self._health_cache or HealthState(hp_percent=100.0, is_critical=False, is_poisoned=False)

        if healthbar_region is None or healthbar_region.size == 0:
            return HealthState(hp_percent=100.0, is_critical=False, is_poisoned=False)
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(healthbar_region, cv2.COLOR_BGR2HSV)
        
        # Red health (critical): H 0-10 or 170-180, high S
        red_lower = np.array([0, 100, 100])
        red_upper = np.array([10, 255, 255])
        red_mask1 = cv2.inRange(hsv, red_lower, red_upper)
        
        red_lower2 = np.array([170, 100, 100])
        red_upper2 = np.array([180, 255, 255])
        red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
        
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        
        # Green health (poison): H 40-80
        green_lower = np.array([40, 100, 100])
        green_upper = np.array([80, 255, 255])
        green_mask = cv2.inRange(hsv, green_lower, green_upper)
        
        # Calculate percentages
        red_pixels = cv2.countNonZero(red_mask)
        green_pixels = cv2.countNonZero(green_mask)
        total_pixels = healthbar_region.size
        
        red_pct = (red_pixels / total_pixels) * 100 if total_pixels > 0 else 0
        green_pct = (green_pixels / total_pixels) * 100 if total_pixels > 0 else 0
        
        # HP is inverse of red (more red = lower HP)
        hp_percent = max(0, 100 - (red_pct * 2))
        is_critical = red_pct > 20  # Significant red = critical
        is_poisoned = green_pct > 10  # Green pixels = poisoned
        
        health = HealthState(
            hp_percent=hp_percent,
            is_critical=is_critical,
            is_poisoned=is_poisoned
        )
        
        log.debug(f"Health: {health.hp_percent:.1f}% (critical={is_critical}, poisoned={is_poisoned})")
        self._health_cache = health
        return health
    
    # ─── Target Algorithm (Monster Detection) ──────────────────────────────────
    
    def detect_creatures_from_sprites(
        self, 
        game_screen: np.ndarray, 
        creature_db: dict[str, np.ndarray] | None = None
    ) -> list[TargetInfo]:
        """
        Target Algorithm: Template match creature sprites.
        
        Per paper: Match against preconfigured hunting list.
        Returns list of detected monsters with confidence.
        """
        if not _vision_deps_available():
            return []

        if game_screen is None or game_screen.size == 0:
            return []
        
        if creature_db is None:
            creature_db = self.creature_templates
        
        detected: list[TargetInfo] = []
        
        for creature_name, creature_template in creature_db.items():
            try:
                result = cv2.matchTemplate(game_screen, creature_template, cv2.TM_CCOEFF_NORMED)
                
                # Find all matches above threshold
                threshold = 0.7
                matches = np.where(result >= threshold)
                
                for (y, x) in zip(matches[0], matches[1]):
                    h, w = creature_template.shape[:2]
                    center_x = x + w // 2
                    center_y = y + h // 2
                    score = result[y, x]
                    
                    # Simple distance estimation (SQMs from screen center)
                    screen_h, screen_w = game_screen.shape[:2]
                    distance = int(((screen_h // 2 - center_y) ** 2 + (screen_w // 2 - center_x) ** 2) ** 0.5 / 32)
                    
                    target = TargetInfo(
                        name=creature_name,
                        x=center_x,
                        y=center_y,
                        distance=max(1, distance),
                        is_engaged=False,  # Checked separately via target window
                        confidence=float(score)
                    )
                    detected.append(target)
                    log.debug(f"Detected {creature_name} at distance {distance} (conf: {score:.2f})")
            
            except cv2.error as e:
                log.debug(f"Creature template match failed for {creature_name}: {e}")
                continue
        
        # Sort by distance (closest first)
        detected.sort(key=lambda t: t.distance)
        return detected
    
    def detect_engagement_from_target_window(self, target_window: np.ndarray) -> bool:
        """
        Check if current target is engaged (red/pink outline detected).
        Per paper's target algorithm.
        """
        if not _vision_deps_available():
            return False

        if target_window is None or target_window.size == 0:
            return False
        
        # Look for red outline (high saturation red)
        hsv = cv2.cvtColor(target_window, cv2.COLOR_BGR2HSV)
        
        red_lower = np.array([0, 150, 100])
        red_upper = np.array([10, 255, 255])
        red_mask1 = cv2.inRange(hsv, red_lower, red_upper)
        
        red_lower2 = np.array([170, 150, 100])
        red_upper2 = np.array([180, 255, 255])
        red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
        
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        red_pixels = cv2.countNonZero(red_mask)
        
        # Significant red = engaged
        is_engaged = red_pixels > (target_window.size * 0.1)
        log.debug(f"Target engagement: {is_engaged}")
        return is_engaged


# ─── Utility functions ──────────────────────────────────────────────────────

def extract_healthbar_region(game_screen: np.ndarray, ui_layout: str = "tibia_classic") -> Optional[np.ndarray]:
    """
    Extract health bar region from game screen based on UI layout.
    
    Args:
        game_screen: Full game screenshot
        ui_layout: "tibia_classic" | "tibia_modern" | "custom"
    
    Returns:
        Health bar region as numpy array, or None
    """
    h, w = game_screen.shape[:2]
    
    # Tibia classic: health bar top-left corner
    if ui_layout == "tibia_classic":
        x1, y1 = 10, 10
        x2, y2 = 70, 30
    elif ui_layout == "tibia_modern":
        x1, y1 = 10, 40
        x2, y2 = 150, 65
    else:
        # Custom: expect coordinates passed separately
        return None
    
    return game_screen[y1:y2, x1:x2]


def extract_minimap_region(game_screen: np.ndarray, ui_layout: str = "tibia_classic") -> Optional[np.ndarray]:
    """Extract minimap region from game screen."""
    h, w = game_screen.shape[:2]
    
    # Tibia classic: minimap top-right corner
    if ui_layout == "tibia_classic":
        x1 = w - 130
        y1 = 10
        x2 = w - 10
        y2 = 140
    elif ui_layout == "tibia_modern":
        x1 = w - 200
        y1 = 10
        x2 = w - 10
        y2 = 210
    else:
        return None
    
    return game_screen[y1:y2, x1:x2]


def extract_target_window(game_screen: np.ndarray, ui_layout: str = "tibia_classic") -> Optional[np.ndarray]:
    """Extract target info window region."""
    h, w = game_screen.shape[:2]
    
    # Tibia classic: target window left side, mid-height
    if ui_layout == "tibia_classic":
        x1, y1 = 10, h // 2 - 50
        x2, y2 = 200, h // 2 + 50
    elif ui_layout == "tibia_modern":
        x1, y1 = 10, h // 2 - 80
        x2, y2 = 250, h // 2 + 80
    else:
        return None
    
    return game_screen[y1:y2, x1:x2]
