"""
Performance Profiler - Measure capture/command cycle times

Tracks timing for:
  - Screenshot capture (mss vs PIL fallback)
  - Vision layer (template matching)
  - Decision making (LLM vs heuristics)
  - Command execution (keyboard input latency)

Helps identify bottlenecks in the bot loop.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json

log = logging.getLogger("hybrid_bot.profiler")


@dataclass
class TimingSnapshot:
    """Single timing measurement."""
    timestamp: float
    
    capture_ms: float = 0.0          # Screenshot time
    vision_ms: float = 0.0           # Vision layer time
    decision_ms: float = 0.0         # Decision making time
    execution_ms: float = 0.0        # Command execution time
    tick_total_ms: float = 0.0       # Total tick time
    
    def to_dict(self) -> dict:
        """Convert to dict."""
        return {
            "timestamp": self.timestamp,
            "capture_ms": self.capture_ms,
            "vision_ms": self.vision_ms,
            "decision_ms": self.decision_ms,
            "execution_ms": self.execution_ms,
            "tick_total_ms": self.tick_total_ms,
        }


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    count: int = 0
    
    capture_min: float = float('inf')
    capture_max: float = 0.0
    capture_avg: float = 0.0
    capture_total: float = 0.0
    
    vision_min: float = float('inf')
    vision_max: float = 0.0
    vision_avg: float = 0.0
    vision_total: float = 0.0
    
    decision_min: float = float('inf')
    decision_max: float = 0.0
    decision_avg: float = 0.0
    decision_total: float = 0.0
    
    execution_min: float = float('inf')
    execution_max: float = 0.0
    execution_avg: float = 0.0
    execution_total: float = 0.0
    
    tick_min: float = float('inf')
    tick_max: float = 0.0
    tick_avg: float = 0.0
    tick_total: float = 0.0
    
    def update(self, snapshot: TimingSnapshot) -> None:
        """Update stats with new measurement."""
        self.count += 1
        
        # Capture stats
        self.capture_min = min(self.capture_min, snapshot.capture_ms)
        self.capture_max = max(self.capture_max, snapshot.capture_ms)
        self.capture_total += snapshot.capture_ms
        self.capture_avg = self.capture_total / self.count
        
        # Vision stats
        self.vision_min = min(self.vision_min, snapshot.vision_ms)
        self.vision_max = max(self.vision_max, snapshot.vision_ms)
        self.vision_total += snapshot.vision_ms
        self.vision_avg = self.vision_total / self.count
        
        # Decision stats
        self.decision_min = min(self.decision_min, snapshot.decision_ms)
        self.decision_max = max(self.decision_max, snapshot.decision_ms)
        self.decision_total += snapshot.decision_ms
        self.decision_avg = self.decision_total / self.count
        
        # Execution stats
        self.execution_min = min(self.execution_min, snapshot.execution_ms)
        self.execution_max = max(self.execution_max, snapshot.execution_ms)
        self.execution_total += snapshot.execution_ms
        self.execution_avg = self.execution_total / self.count
        
        # Total tick stats
        self.tick_min = min(self.tick_min, snapshot.tick_total_ms)
        self.tick_max = max(self.tick_max, snapshot.tick_total_ms)
        self.tick_total += snapshot.tick_total_ms
        self.tick_avg = self.tick_total / self.count
    
    def print_report(self) -> str:
        """Generate performance report."""
        lines = [
            "=" * 70,
            "PERFORMANCE PROFILE REPORT",
            "=" * 70,
            f"Total Ticks: {self.count:,}",
            "",
            "CAPTURE (Screenshot):",
            f"  Min/Avg/Max: {self.capture_min:.1f}ms / {self.capture_avg:.1f}ms / {self.capture_max:.1f}ms",
            "",
            "VISION (Template Matching):",
            f"  Min/Avg/Max: {self.vision_min:.1f}ms / {self.vision_avg:.1f}ms / {self.vision_max:.1f}ms",
            "",
            "DECISION (LLM/Heuristics):",
            f"  Min/Avg/Max: {self.decision_min:.1f}ms / {self.decision_avg:.1f}ms / {self.decision_max:.1f}ms",
            "",
            "EXECUTION (Command Send):",
            f"  Min/Avg/Max: {self.execution_min:.1f}ms / {self.execution_avg:.1f}ms / {self.execution_max:.1f}ms",
            "",
            "TICK TOTAL (Full Cycle):",
            f"  Min/Avg/Max: {self.tick_min:.1f}ms / {self.tick_avg:.1f}ms / {self.tick_max:.1f}ms",
            f"  Target: 100ms (10 Hz), Efficiency: {(100.0/self.tick_avg)*100:.1f}%",
            "=" * 70,
        ]
        return "\n".join(lines)


class PerformanceProfiler:
    """
    Measure performance of bot operations.
    
    Usage:
        profiler = PerformanceProfiler()
        
        # In bot loop
        with profiler.measure("capture"):
            frame = screenshot_provider.capture()
        
        with profiler.measure("vision"):
            creatures = vision_layer.detect(frame)
        
        # Get stats
        print(profiler.get_stats().print_report())
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize profiler.
        
        Args:
            output_dir: Directory to save detailed timing logs
        """
        self.output_dir = output_dir or Path("./metrics")
        self.output_dir.mkdir(exist_ok=True)
        
        self.snapshots: list[TimingSnapshot] = []
        self.current_snapshot: Optional[TimingSnapshot] = None
        self.active_timers: dict = {}
        self.stats = PerformanceStats()
    
    class TimingContext:
        """Context manager for timing code blocks."""
        
        def __init__(self, profiler: PerformanceProfiler, timer_name: str):
            self.profiler = profiler
            self.timer_name = timer_name
            self.start_time = 0.0
        
        def __enter__(self):
            self.start_time = time.perf_counter()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed_ms = (time.perf_counter() - self.start_time) * 1000.0
            
            if self.profiler.current_snapshot is None:
                self.profiler.current_snapshot = TimingSnapshot(
                    timestamp=time.time()
                )
            
            # Update snapshot based on timer name
            if self.timer_name == "capture":
                self.profiler.current_snapshot.capture_ms = elapsed_ms
            elif self.timer_name == "vision":
                self.profiler.current_snapshot.vision_ms = elapsed_ms
            elif self.timer_name == "decision":
                self.profiler.current_snapshot.decision_ms = elapsed_ms
            elif self.timer_name == "execution":
                self.profiler.current_snapshot.execution_ms = elapsed_ms
            elif self.timer_name == "tick":
                self.profiler.current_snapshot.tick_total_ms = elapsed_ms
    
    def measure(self, timer_name: str) -> TimingContext:
        """
        Create timing context.
        
        Args:
            timer_name: Name of operation ("capture", "vision", "decision", "execution", "tick")
        
        Returns:
            Context manager for timing
        """
        return self.TimingContext(self, timer_name)
    
    def record_snapshot(self) -> None:
        """Record current snapshot to history."""
        if self.current_snapshot:
            self.snapshots.append(self.current_snapshot)
            self.stats.update(self.current_snapshot)
            self.current_snapshot = None
    
    def get_stats(self) -> PerformanceStats:
        """Get aggregated statistics."""
        return self.stats
    
    def export_to_json(self, filename: str = "profile.jsonl") -> Path:
        """Export timing snapshots to JSONL file."""
        output_file = self.output_dir / filename
        
        with open(output_file, 'w') as f:
            for snapshot in self.snapshots:
                f.write(json.dumps(snapshot.to_dict()) + '\n')
        
        log.info(f"Exported {len(self.snapshots)} timing samples to {output_file}")
        return output_file
    
    def print_report(self) -> str:
        """Print performance report."""
        return self.stats.print_report()
