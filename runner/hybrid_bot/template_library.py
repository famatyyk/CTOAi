"""
Template Library Manager - Load and manage creature/minimap templates

Handles loading sprite templates from disk, server APIs, or cache.
Templates are resized to 25% for fast matching (per research paper).

Usage:
    from runner.hybrid_bot.template_library import TemplateLibrary
    
    lib = TemplateLibrary()
    lib.load_creatures(["wasp", "tarantula", "giant_spider"])
    lib.load_minimap_sections(game_world_bounds)
    
    # Get template for matching
    wasp_template = lib.get_creature("wasp")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from urllib.request import urlopen

import cv2
import numpy as np

log = logging.getLogger("hybrid_bot.template_library")


@dataclass
class Template:
    """Template metadata."""
    name: str
    template_type: str  # "creature", "minimap", "ui"
    image: np.ndarray
    original_size: Tuple[int, int]
    resized_size: Tuple[int, int]
    scale_factor: float  # Usually 0.25
    confidence_threshold: float  # For matching


class TemplateLibrary:
    """
    Central template management system.
    
    Templates are stored resized to 25% per research paper optimization.
    Supports loading from:
      1. Local disk cache
      2. Server API (tibiapi, cipsoft)
      3. Generated from game captures
    """
    
    SCALE_FACTOR = 0.25  # Resize to 25% per paper
    
    def __init__(
        self,
        cache_dir: Path | str = "./templates",
        server_url: Optional[str] = None,
        use_cache: bool = True,
    ):
        """
        Initialize template library.
        
        Args:
            cache_dir: Local directory for cached templates
            server_url: Optional server API for downloading templates
            use_cache: If True, cache downloaded templates locally
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.server_url = server_url
        self.use_cache = use_cache
        
        # In-memory template storage
        self.creatures: Dict[str, Template] = {}
        self.minimap_sections: Dict[str, Template] = {}
        self.ui_elements: Dict[str, Template] = {}
        
        log.info(f"Template library initialized at: {self.cache_dir}")
    
    # ─── Creature Templates ────────────────────────────────────────────────
    
    def load_creatures(self, creature_names: List[str]) -> int:
        """
        Load creature templates by name.
        
        Args:
            creature_names: List of creature names (e.g., ["wasp", "tarantula"])
        
        Returns:
            Number of successfully loaded templates
        """
        loaded = 0
        for name in creature_names:
            try:
                template = self._load_creature(name)
                if template:
                    self.creatures[name] = template
                    loaded += 1
            except Exception as e:
                log.warning(f"Failed to load creature '{name}': {e}")
        
        log.info(f"Loaded {loaded}/{len(creature_names)} creature templates")
        return loaded
    
    def _load_creature(self, name: str) -> Optional[Template]:
        """Load single creature template from cache or server."""
        # Try local cache first
        cache_file = self.cache_dir / f"creature_{name}.png"
        if cache_file.exists():
            return self._load_from_disk(cache_file, "creature", name)
        
        # Try server API
        if self.server_url:
            try:
                return self._load_from_server(f"{self.server_url}/creatures/{name}", "creature", name)
            except Exception as e:
                log.debug(f"Server load failed for {name}: {e}")
        
        # Fallback: create blank template (to be filled during gameplay)
        log.warning(f"No template found for creature '{name}'; creating placeholder")
        blank = np.zeros((32, 32, 3), dtype=np.uint8)
        return Template(
            name=name,
            template_type="creature",
            image=blank,
            original_size=(128, 128),
            resized_size=(32, 32),
            scale_factor=self.SCALE_FACTOR,
            confidence_threshold=0.7
        )
    
    # ─── Minimap Templates ─────────────────────────────────────────────────
    
    def load_minimap_sections(
        self,
        world_bounds: Tuple[int, int, int, int],
        section_size: int = 100
    ) -> int:
        """
        Load minimap template sections for world bounds.
        
        Args:
            world_bounds: (min_x, min_y, max_x, max_y)
            section_size: Size of minimap sections in SQMs
        
        Returns:
            Number of loaded sections
        """
        min_x, min_y, max_x, max_y = world_bounds
        loaded = 0
        
        for x in range(min_x, max_x, section_size):
            for y in range(min_y, max_y, section_size):
                coord_name = f"minimap_{x}_{y}_7"  # z=7 (ground floor)
                
                try:
                    # Try cache first
                    cache_file = self.cache_dir / f"{coord_name}.png"
                    if cache_file.exists():
                        template = self._load_from_disk(cache_file, "minimap", coord_name)
                    # Try server API
                    elif self.server_url:
                        template = self._load_from_server(
                            f"{self.server_url}/minimap/{x}/{y}",
                            "minimap",
                            coord_name
                        )
                    else:
                        template = None
                    
                    if template:
                        self.minimap_sections[coord_name] = template
                        loaded += 1
                
                except Exception as e:
                    log.debug(f"Failed to load minimap {coord_name}: {e}")
        
        log.info(f"Loaded {loaded} minimap sections")
        return loaded
    
    # ─── File I/O ──────────────────────────────────────────────────────────
    
    def _load_from_disk(self, path: Path, tpl_type: str, name: str) -> Optional[Template]:
        """Load template from disk file."""
        try:
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is None or img.size == 0:
                log.warning(f"Invalid image file: {path}")
                return None
            
            original_h, original_w = img.shape[:2]
            
            # Check if already resized
            is_resized = original_w <= 32 and original_h <= 32
            
            if not is_resized:
                # Resize to 25%
                img = cv2.resize(img, None, fx=self.SCALE_FACTOR, fy=self.SCALE_FACTOR)
            
            h, w = img.shape[:2]
            confidence = 0.7 if tpl_type == "creature" else 0.75
            
            return Template(
                name=name,
                template_type=tpl_type,
                image=img,
                original_size=(original_w, original_h),
                resized_size=(w, h),
                scale_factor=self.SCALE_FACTOR if not is_resized else 1.0,
                confidence_threshold=confidence
            )
        
        except Exception as e:
            log.error(f"Failed to load template from {path}: {e}")
            return None
    
    def _load_from_server(self, url: str, tpl_type: str, name: str) -> Optional[Template]:
        """Load template from remote server."""
        try:
            response = urlopen(url, timeout=5)
            img_data = response.read()
            
            # Decode image from bytes
            img_array = np.frombuffer(img_data, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None or img.size == 0:
                log.warning(f"Invalid image from server: {url}")
                return None
            
            original_h, original_w = img.shape[:2]
            
            # Resize to 25%
            img = cv2.resize(img, None, fx=self.SCALE_FACTOR, fy=self.SCALE_FACTOR)
            h, w = img.shape[:2]
            
            # Cache locally if enabled
            if self.use_cache:
                cache_file = self.cache_dir / f"{tpl_type}_{name}.png"
                cv2.imwrite(str(cache_file), img)
                log.debug(f"Cached template: {cache_file}")
            
            return Template(
                name=name,
                template_type=tpl_type,
                image=img,
                original_size=(original_w, original_h),
                resized_size=(w, h),
                scale_factor=self.SCALE_FACTOR,
                confidence_threshold=0.7
            )
        
        except Exception as e:
            log.error(f"Failed to load from server ({url}): {e}")
            return None
    
    def save_template(self, template: Template) -> bool:
        """Cache template to disk."""
        try:
            cache_file = self.cache_dir / f"{template.template_type}_{template.name}.png"
            cv2.imwrite(str(cache_file), template.image)
            log.debug(f"Saved template: {cache_file}")
            return True
        except Exception as e:
            log.error(f"Failed to save template: {e}")
            return False
    
    # ─── Retrieval ─────────────────────────────────────────────────────────
    
    def get_creature(self, name: str) -> Optional[Template]:
        """Get creature template by name."""
        return self.creatures.get(name)
    
    def get_minimap_section(self, x: int, y: int, z: int = 7) -> Optional[Template]:
        """Get minimap template by world coordinates."""
        key = f"minimap_{x}_{y}_{z}"
        return self.minimap_sections.get(key)
    
    def get_all_creatures(self) -> Dict[str, Template]:
        """Get all loaded creature templates."""
        return self.creatures.copy()
    
    # ─── Statistics ────────────────────────────────────────────────────────
    
    def get_stats(self) -> dict:
        """Get library statistics."""
        total_creatures = len(self.creatures)
        total_minimap = len(self.minimap_sections)
        
        creature_memory = sum(t.image.nbytes for t in self.creatures.values())
        minimap_memory = sum(t.image.nbytes for t in self.minimap_sections.values())
        
        return {
            "creatures_loaded": total_creatures,
            "minimap_sections_loaded": total_minimap,
            "creature_memory_mb": creature_memory / (1024 * 1024),
            "minimap_memory_mb": minimap_memory / (1024 * 1024),
            "cache_directory": str(self.cache_dir),
            "server_url": self.server_url,
        }
    
    def print_stats(self) -> str:
        """Format statistics for logging."""
        stats = self.get_stats()
        return f"""
Template Library Stats:
  Creatures: {stats['creatures_loaded']}
  Minimap sections: {stats['minimap_sections_loaded']}
  Memory: {stats['creature_memory_mb']:.1f}MB creatures + {stats['minimap_memory_mb']:.1f}MB minimap
  Cache: {stats['cache_directory']}
"""


# ─── Pre-configured template sets ──────────────────────────────────────────

TIBIA_COMMON_CREATURES = [
    "wasp",
    "tarantula",
    "giant_spider",
    "rotworm",
    "carrion_worm",
    "nomad",
    "desert_nomad",
    "goblins",
    "cave_rat",
    "rat",
    "bug",
    "dragon",
    "dragon_lord",
]

TIBIA_TUTORIAL_AREA = (390, 396, 430, 430)  # World bounds
TIBIA_WASP_CAVE = (520, 540, 600, 580)
TIBIA_NOMAD_LAND = (490, 470, 640, 590)


def create_default_library(cache_dir: str = "./templates") -> TemplateLibrary:
    """Create pre-configured library for common Tibia locations."""
    lib = TemplateLibrary(cache_dir=cache_dir)
    
    # Load common creatures
    lib.load_creatures(TIBIA_COMMON_CREATURES)
    
    # Load common hunting areas
    lib.load_minimap_sections(TIBIA_WASP_CAVE)
    lib.load_minimap_sections(TIBIA_NOMAD_LAND)
    
    log.info(f"Created default library: {lib.print_stats()}")
    return lib


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Test library creation
    lib = create_default_library()
    print(lib.print_stats())
