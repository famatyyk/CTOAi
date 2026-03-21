"""
Metrics Collection - XP, Balance, Supplies Tracking

Per Federal University of Tocantis research paper validation metrics:
  - XP Gain (main measure of effectiveness)
  - Supplies Cost (gold spent on potions)
  - Balance (Loot - Supplies profit)
  - Killed Monsters count (linear dependent on XP)
  - Loot value (linear dependent on XP)

All metrics collected in JSONL format for analysis.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger("hybrid_bot.metrics")


@dataclass
class MetricsSnapshot:
    """Snapshot of metrics at a point in time."""
    timestamp: str
    location: str
    duration_seconds: float
    
    # Primary metrics (from paper)
    xp_gained: int
    monsters_killed: int
    loot_value_gold: float
    supplies_cost_gold: float
    balance_gold: float
    
    # Derived metrics
    xp_per_hour: float
    balance_per_hour: float
    supplies_per_hour: float
    
    # Status metrics
    player_health_percent: float
    player_level: int
    distance_traveled_sqm: int
    
    # Optional
    notes: str = ""


@dataclass
class SessionMetrics:
    """Aggregated metrics for entire session."""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    
    total_xp: int = 0
    total_monsters: int = 0
    total_loot_gold: float = 0.0
    total_supplies_gold: float = 0.0
    total_balance_gold: float = 0.0
    
    total_duration_hours: float = 0.0
    average_xp_per_hour: float = 0.0
    average_balance_per_hour: float = 0.0
    
    locations_visited: list[str] = None
    
    def __post_init__(self):
        if self.locations_visited is None:
            self.locations_visited = []


class MetricsCollector:
    """
    Collect and aggregate bot performance metrics.
    
    Outputs:
      - Real-time snapshot every N seconds
      - JSONL log file for post-analysis
      - Session summary at end
    """
    
    def __init__(
        self,
        output_dir: Path | str = ".",
        snapshot_interval_seconds: float = 60.0,
        disable_file_output: bool = False
    ):
        """
        Initialize metrics collector.
        
        Args:
            output_dir: Directory for JSONL metrics files
            snapshot_interval_seconds: How often to snapshot metrics
            disable_file_output: If True, only collect in-memory (no file writes)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_interval = snapshot_interval_seconds
        self.disable_file_output = disable_file_output
        
        # Session tracking
        self.session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.metrics_file: Optional[Path] = None
        if not disable_file_output:
            self.metrics_file = self.output_dir / f"metrics_{self.session_id}.jsonl"
        
        # In-memory snapshots
        self.snapshots: list[MetricsSnapshot] = []
        self.last_snapshot_time = datetime.utcnow()
    
    # ─── Metric Collection API ────────────────────────────────────────────
    
    def record_snapshot(
        self,
        location: str,
        duration_seconds: float,
        xp_gained: int,
        monsters_killed: int,
        loot_value_gold: float,
        supplies_cost_gold: float,
        player_health_percent: float = 100.0,
        player_level: int = 50,
        distance_traveled_sqm: int = 0,
        notes: str = ""
    ) -> MetricsSnapshot:
        """
        Record a metrics snapshot.
        
        Returns the snapshot object (also stores in memory & file).
        """
        # Calculate derived metrics
        duration_hours = duration_seconds / 3600.0
        balance = loot_value_gold - supplies_cost_gold
        
        xp_per_hour = xp_gained / duration_hours if duration_hours > 0 else 0
        balance_per_hour = balance / duration_hours if duration_hours > 0 else 0
        supplies_per_hour = supplies_cost_gold / duration_hours if duration_hours > 0 else 0
        
        snapshot = MetricsSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            location=location,
            duration_seconds=duration_seconds,
            xp_gained=xp_gained,
            monsters_killed=monsters_killed,
            loot_value_gold=loot_value_gold,
            supplies_cost_gold=supplies_cost_gold,
            balance_gold=balance,
            xp_per_hour=xp_per_hour,
            balance_per_hour=balance_per_hour,
            supplies_per_hour=supplies_per_hour,
            player_health_percent=player_health_percent,
            player_level=player_level,
            distance_traveled_sqm=distance_traveled_sqm,
            notes=notes
        )
        
        # Store in memory
        self.snapshots.append(snapshot)
        self.last_snapshot_time = datetime.utcnow()
        
        # Write to file
        if self.metrics_file and not self.disable_file_output:
            self._append_snapshot_to_file(snapshot)
        
        log.info(f"Snapshot: {location} XP={xp_gained} Balance={balance:.0f}g")
        return snapshot
    
    # ─── File I/O ────────────────────────────────────────────────────────
    
    def _append_snapshot_to_file(self, snapshot: MetricsSnapshot) -> None:
        """Append snapshot as JSON line to metrics file."""
        try:
            with open(self.metrics_file, 'a') as f:
                json.dump(asdict(snapshot), f)
                f.write('\n')
        except IOError as e:
            log.warning(f"Failed to write metrics file: {e}")
    
    def load_snapshots_from_file(self, filepath: Path | str) -> list[MetricsSnapshot]:
        """Load metrics snapshots from JSONL file."""
        snapshots = []
        filepath = Path(filepath)
        
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        snapshots.append(MetricsSnapshot(**data))
        except (IOError, json.JSONDecodeError) as e:
            log.error(f"Failed to load metrics: {e}")
        
        return snapshots
    
    # ─── Analysis Functions ────────────────────────────────────────────────
    
    def get_session_summary(self) -> SessionMetrics:
        """Calculate aggregated session metrics."""
        if not self.snapshots:
            return SessionMetrics(session_id=self.session_id)
        
        first = self.snapshots[0]
        last = self.snapshots[-1]
        
        total_xp = sum(s.xp_gained for s in self.snapshots)
        total_monsters = sum(s.monsters_killed for s in self.snapshots)
        total_loot = sum(s.loot_value_gold for s in self.snapshots)
        total_supplies = sum(s.supplies_cost_gold for s in self.snapshots)
        total_duration = sum(s.duration_seconds for s in self.snapshots) / 3600.0
        
        locations = sorted(set(s.location for s in self.snapshots))
        
        balance = total_loot - total_supplies
        avg_xp_per_hour = total_xp / total_duration if total_duration > 0 else 0
        avg_balance_per_hour = balance / total_duration if total_duration > 0 else 0
        
        return SessionMetrics(
            session_id=self.session_id,
            start_time=first.timestamp,
            end_time=last.timestamp,
            total_xp=total_xp,
            total_monsters=total_monsters,
            total_loot_gold=total_loot,
            total_supplies_gold=total_supplies,
            total_balance_gold=balance,
            total_duration_hours=total_duration,
            average_xp_per_hour=avg_xp_per_hour,
            average_balance_per_hour=avg_balance_per_hour,
            locations_visited=locations
        )
    
    def get_location_stats(self, location: str) -> dict:
        """Get aggregated stats for a specific location."""
        location_snapshots = [s for s in self.snapshots if s.location == location]
        
        if not location_snapshots:
            return {"location": location, "snapshots": 0}
        
        return {
            "location": location,
            "snapshots": len(location_snapshots),
            "total_xp": sum(s.xp_gained for s in location_snapshots),
            "total_monsters": sum(s.monsters_killed for s in location_snapshots),
            "average_xp_per_hour": sum(s.xp_per_hour for s in location_snapshots) / len(location_snapshots),
            "average_balance_per_hour": sum(s.balance_per_hour for s in location_snapshots) / len(location_snapshots),
            "most_recent": location_snapshots[-1].timestamp,
        }
    
    def print_session_report(self) -> str:
        """Format session report as string."""
        summary = self.get_session_summary()
        
        report = f"""
╔════════════════════════════════════════════════════════════╗
║ BOT SESSION METRICS REPORT
╠════════════════════════════════════════════════════════════╣
║ SESSION ID: {summary.session_id}
║ Started: {summary.start_time} | Ended: {summary.end_time}
║ Duration: {summary.total_duration_hours:.2f} hours
╠════════════════════════════════════════════════════════════╣
║ PRIMARY METRICS (per research paper)
║ 
║ XP GAIN
║   Total: {summary.total_xp:,} XP
║   Rate: {summary.average_xp_per_hour:.0f} XP/hour
║
║ SUPPLIES COST
║   Total: {summary.total_supplies_gold:.0f} gold
║   Rate: {summary.total_supplies_gold / max(1, summary.total_duration_hours):.0f} gold/hour
║
║ LOOT VALUE
║   Total: {summary.total_loot_gold:.0f} gold
║   Monsters killed: {summary.total_monsters:,}
║
║ PROFIT BALANCE
║   Total: {summary.total_balance_gold:.0f} gold
║   Rate: {summary.average_balance_per_hour:.0f} gold/hour
║   Status: {'✅ PROFITABLE' if summary.total_balance_gold > 0 else '❌ LOSS'}
╠════════════════════════════════════════════════════════════╣
║ LOCATIONS VISITED: {', '.join(summary.locations_visited)}
╚════════════════════════════════════════════════════════════╝
"""
        return report
    
    def export_metrics_csv(self, output_file: Path | str) -> None:
        """Export snapshots as CSV for spreadsheet analysis."""
        import csv
        
        output_file = Path(output_file)
        try:
            with open(output_file, 'w', newline='') as f:
                if self.snapshots:
                    writer = csv.DictWriter(f, fieldnames=asdict(self.snapshots[0]).keys())
                    writer.writeheader()
                    for snapshot in self.snapshots:
                        writer.writerow(asdict(snapshot))
                    log.info(f"Exported metrics to {output_file}")
        except IOError as e:
            log.warning(f"Failed to export CSV: {e}")


# ─── Utility: Comparison with Manual Benchmarks ────────────────────────────

def compare_with_manual_metrics(
    bot_metrics: SessionMetrics,
    manual_xp_per_hour: float,
    manual_balance_per_hour: float
) -> dict:
    """
    Compare bot performance with manual player benchmarks.
    
    Per paper: Validates that bot plays consistently vs. manual.
    """
    xp_ratio = bot_metrics.average_xp_per_hour / manual_xp_per_hour if manual_xp_per_hour > 0 else 0
    balance_ratio = bot_metrics.average_balance_per_hour / manual_balance_per_hour if manual_balance_per_hour > 0 else 0
    
    return {
        "bot_xp_per_hour": bot_metrics.average_xp_per_hour,
        "manual_xp_per_hour": manual_xp_per_hour,
        "xp_ratio": xp_ratio,
        "performance_relative_to_manual": f"{xp_ratio * 100:.0f}%",
        
        "bot_balance_per_hour": bot_metrics.average_balance_per_hour,
        "manual_balance_per_hour": manual_balance_per_hour,
        "balance_ratio": balance_ratio,
        "profit_relative_to_manual": f"{balance_ratio * 100:.0f}%",
        
        "status": (
            "✅ EXCEEDS MANUAL" if xp_ratio >= 1.0
            else "⚠️ BELOW MANUAL" if xp_ratio < 0.9
            else "🟡 COMPARABLE"
        )
    }
