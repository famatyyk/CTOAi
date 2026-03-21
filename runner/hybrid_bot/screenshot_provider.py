"""
Screenshot Provider - Capture game window

Implements fast screenshot capture using mss (fastest) with PIL fallback.

Usage:
    from runner.hybrid_bot.screenshot_provider import ScreenshotProvider
    
    provider = ScreenshotProvider(window_title="Tibia Client")
    frame = provider.capture()  # Returns np.ndarray (BGR format for OpenCV)
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import cv2
import numpy as np

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

log = logging.getLogger("hybrid_bot.screenshot")


class ScreenshotProvider:
    """
    Captures game window screenshots for vision processing.
    
    Strategies (in order of preference):
      1. MSS (fastest, ~20ms per frame)
      2. PIL/ImageGrab (medium, ~30ms per frame)
      3. Fallback stub (returns None)
    """
    
    def __init__(
        self,
        window_title: str = "Tibia Client",
        monitor_index: int = 1,
        use_mss: bool = True,
        game_window_bounds: Optional[Tuple[int, int, int, int]] = None,
    ):
        """
        Initialize screenshot provider.
        
        Args:
            window_title: Window title to find (Windows-specific)
            monitor_index: Monitor to capture (1-based for mss)
            use_mss: Prefer mss if available
            game_window_bounds: Manual (left, top, right, bottom) if auto-detect fails
        """
        self.window_title = window_title
        self.monitor_index = monitor_index
        self.use_mss = use_mss and HAS_MSS
        self.game_window_bounds = game_window_bounds
        
        self.mss_instance: Optional[mss.mss] = None
        self.capture_method = "none"
        
        self._initialize_capture_method()
        log.info(f"Screenshot provider initialized: {self.capture_method}")
    
    def _initialize_capture_method(self) -> None:
        """Select best available capture method."""
        if self.use_mss and HAS_MSS:
            try:
                self.mss_instance = mss.mss()
                self.capture_method = "mss"
                log.info(f"Using mss (fastest)")
                return
            except Exception as e:
                log.warning(f"mss initialization failed: {e}; trying PIL")
        
        if HAS_PIL:
            self.capture_method = "pil"
            log.info(f"Using PIL/ImageGrab")
            return
        
        log.warning("No screenshot method available (install mss or Pillow)")
        self.capture_method = "none"
    
    def capture(self) -> Optional[np.ndarray]:
        """
        Capture game screen.
        
        Returns:
            BGR numpy array (OpenCV format) or None if capture fails
        """
        try:
            if self.capture_method == "mss" and self.mss_instance:
                return self._capture_mss()
            elif self.capture_method == "pil":
                return self._capture_pil()
            else:
                log.warning("Screenshot provider not initialized")
                return None
        except Exception as e:
            log.error(f"Screenshot capture failed: {e}")
            return None
    
    def _capture_mss(self) -> Optional[np.ndarray]:
        """Capture using mss (fastest)."""
        try:
            # Get monitor bounds
            if self.game_window_bounds:
                # Manual bounds: (left, top, right, bottom)
                left, top, right, bottom = self.game_window_bounds
                monitor_dict = {
                    "left": left,
                    "top": top,
                    "width": right - left,
                    "height": bottom - top,
                }
                screenshot = self.mss_instance.grab(monitor_dict)
            else:
                # Auto: use specified monitor
                if self.monitor_index < len(self.mss_instance.monitors):
                    monitor = self.mss_instance.monitors[self.monitor_index]
                else:
                    monitor = self.mss_instance.monitors[1]
                
                screenshot = self.mss_instance.grab(monitor)
            
            # Convert RGBA to BGR (OpenCV format)
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGBA2BGR)
            return frame
        
        except Exception as e:
            log.error(f"mss capture failed: {e}")
            return None
    
    def _capture_pil(self) -> Optional[np.ndarray]:
        """Capture using PIL/ImageGrab (medium speed)."""
        try:
            if self.game_window_bounds:
                # Manual bounds: (left, top, right, bottom)
                bbox = self.game_window_bounds
            else:
                # Full screen
                bbox = None
            
            # Grab screenshot (RGB format)
            img = ImageGrab.grab(bbox=bbox)
            
            # Convert RGB to BGR for OpenCV
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            return frame
        
        except Exception as e:
            log.error(f"PIL capture failed: {e}")
            return None
    
    def get_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Get current capture bounds (left, top, right, bottom)."""
        if self.game_window_bounds:
            return self.game_window_bounds
        
        if self.capture_method == "mss" and self.mss_instance:
            try:
                monitor = self.mss_instance.monitors[self.monitor_index]
                return (monitor["left"], monitor["top"], 
                        monitor["left"] + monitor["width"],
                        monitor["top"] + monitor["height"])
            except (IndexError, KeyError):
                pass
        
        return None
    
    def set_bounds(self, bounds: Tuple[int, int, int, int]) -> None:
        """Manually set capture bounds for faster performance."""
        self.game_window_bounds = bounds
        log.info(f"Set capture bounds: {bounds}")
    
    def close(self) -> None:
        """Clean up resources."""
        if self.mss_instance:
            self.mss_instance.close()
            self.mss_instance = None


# ─── Utility: Auto-detect Tibia window ──────────────────────────────────

def find_tibia_window() -> Optional[Tuple[int, int, int, int]]:
    """
    Attempt to auto-detect Tibia game window bounds.
    
    Windows-specific using pygetwindow.
    Returns (left, top, right, bottom) or None.
    """
    try:
        import pygetwindow
        
        # Try common Tibia window titles
        tibia_titles = [
            "Tibia Client",
            "Tibia",
            "MythibiaV2",
            "Mythibia",
        ]
        
        for title in tibia_titles:
            windows = pygetwindow.getWindowsWithTitle(title)
            if windows:
                win = windows[0]
                # Return bounds: (left, top, right, bottom)
                return (win.left, win.top, win.right, win.bottom)
    
    except ImportError:
        log.warning("pygetwindow not installed; cannot auto-detect window")
    except Exception as e:
        log.warning(f"Failed to auto-detect Tibia window: {e}")
    
    return None


# ─── Example usage ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time
    
    logging.basicConfig(level=logging.DEBUG)
    
    # Initialize provider
    provider = ScreenshotProvider()
    
    # Capture a frame
    frame = provider.capture()
    if frame is not None:
        print(f"Captured: {frame.shape}")
        
        # Optionally save for inspection
        cv2.imwrite("screenshot_test.png", frame)
        print("Saved to: screenshot_test.png")
    else:
        print("Failed to capture screenshot")
    
    # Benchmark capture speed
    print("\nBenchmarking capture speed...")
    start = time.time()
    for _ in range(10):
        provider.capture()
    elapsed = (time.time() - start) / 10
    print(f"Average capture time: {elapsed * 1000:.1f}ms")
    
    provider.close()
