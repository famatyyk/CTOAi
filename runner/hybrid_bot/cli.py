#!/usr/bin/env python3
"""
Hybrid Tibia Bot - CLI Entry Point

Usage:
    python hybrid_bot_cli.py --help
    python hybrid_bot_cli.py run --level 50 --location "Wasp Cave"
    python hybrid_bot_cli.py benchmark --compare-manual 5000 500
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from runner.hybrid_bot import (
    BotConfig,
    HybridBotRunner,
    MetricsCollector,
)
from runner.hybrid_bot.screenshot_provider import ScreenshotProvider
from runner.hybrid_bot.command_executor import CommandExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s"
)
log = logging.getLogger("hybrid_bot.cli")


async def cmd_run(args) -> int:
    """Run bot in hunting mode."""
    config = BotConfig(
        player_level=args.level,
        use_llm=args.use_llm,
        max_health_before_heal=args.heal_threshold,
        critical_health=args.critical_threshold,
        update_interval_ms=args.tick_ms,
        metrics_dir=Path(args.metrics_dir),
    )
    
    # Initialize real components
    screenshot_provider = ScreenshotProvider(window_title="Tibia Client")
    command_executor = CommandExecutor()
    
    bot = HybridBotRunner(
        config=config,
        screenshot_provider=screenshot_provider,
        command_executor=command_executor,
    )
    
    # Set waypoints if provided
    if args.waypoints:
        waypoints = json.loads(args.waypoints)
        bot.set_waypoints(waypoints)
    
    # Start hunting
    bot.start_hunting_location(args.location)
    
    try:
        await bot.run()
        return 0
    except Exception as e:
        log.error(f"Bot error: {e}")
        return 1


def cmd_benchmark(args) -> int:
    """Benchmark bot against manual metrics."""
    from runner.hybrid_bot.metrics import compare_with_manual_metrics
    
    # Load metrics from file
    collector = MetricsCollector(output_dir=args.metrics_dir, disable_file_output=True)
    if args.metrics_file:
        snapshots = collector.load_snapshots_from_file(args.metrics_file)
        collector.snapshots = snapshots
    
    # Get session summary
    summary = collector.get_session_summary()
    
    # Compare with manual (if provided)
    if args.manual_xp and args.manual_profit:
        comparison = compare_with_manual_metrics(
            summary,
            manual_xp_per_hour=args.manual_xp,
            manual_balance_per_hour=args.manual_profit
        )
        
        print("\n" + "=" * 60)
        print("BOT vs MANUAL COMPARISON")
        print("=" * 60)
        print(f"Bot XP/hour:             {comparison['bot_xp_per_hour']:.0f}")
        print(f"Manual XP/hour:          {comparison['manual_xp_per_hour']:.0f}")
        print(f"Performance:             {comparison['performance_relative_to_manual']}")
        print()
        print(f"Bot Profit/hour:         {comparison['bot_balance_per_hour']:.0f}g")
        print(f"Manual Profit/hour:      {comparison['manual_balance_per_hour']:.0f}g")
        print(f"Profitability:           {comparison['profit_relative_to_manual']}")
        print()
        print(f"Status:                  {comparison['status']}")
        print("=" * 60)
    
    # Print session report
    print(collector.print_session_report())
    
    return 0


def cmd_export(args) -> int:
    """Export metrics as CSV."""
    collector = MetricsCollector(output_dir=args.metrics_dir, disable_file_output=True)
    
    if args.input:
        snapshots = collector.load_snapshots_from_file(args.input)
        collector.snapshots = snapshots
    
    output_file = Path(args.output)
    collector.export_metrics_csv(output_file)
    log.info(f"Exported {len(collector.snapshots)} snapshots to {output_file}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hybrid Tibia Bot - Template Matching + A* + LLM Logic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run bot at level 50 in Wasp Cave
  python hybrid_bot_cli.py run --level 50 --location "Wasp Cave"
  
  # Run with LLM decision making (GPT-4)
  python hybrid_bot_cli.py run --level 100 --use-llm --llm-model gpt-4
  
  # Benchmark current metrics against manual performance
  python hybrid_bot_cli.py benchmark --metrics-file metrics_20260321_120000.jsonl \\
      --manual-xp 5000 --manual-profit 500
  
  # Export metrics to CSV
  python hybrid_bot_cli.py export --input metrics_20260321_120000.jsonl
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # RUN command
    run_parser = subparsers.add_parser("run", help="Start bot hunting")
    run_parser.add_argument(
        "--level", type=int, default=50,
        help="Player character level (default: 50)"
    )
    run_parser.add_argument(
        "--location", default="Wasp Cave",
        help="Hunting location name (default: Wasp Cave)"
    )
    run_parser.add_argument(
        "--waypoints", default=None,
        help='JSON list of waypoints: [{"x":100,"y":100,"z":7}, ...]'
    )
    run_parser.add_argument(
        "--use-llm", action="store_true",
        help="Use LLM for decision making (requires API key)"
    )
    run_parser.add_argument(
        "--llm-model", default="gpt-3.5-turbo",
        help="LLM model to use (default: gpt-3.5-turbo)"
    )
    run_parser.add_argument(
        "--heal-threshold", type=float, default=60.0,
        help="Health % to trigger healing (default: 60)"
    )
    run_parser.add_argument(
        "--critical-threshold", type=float, default=25.0,
        help="Critical health % (default: 25)"
    )
    run_parser.add_argument(
        "--tick-ms", type=int, default=100,
        help="Bot tick interval in ms (default: 100, ~10Hz)"
    )
    run_parser.add_argument(
        "--metrics-dir", default="./metrics",
        help="Directory for metrics output (default: ./metrics)"
    )
    run_parser.set_defaults(func=cmd_run)
    
    # BENCHMARK command
    bench_parser = subparsers.add_parser("benchmark", help="Compare metrics")
    bench_parser.add_argument(
        "--metrics-file",
        help="Metrics JSONL file to analyze"
    )
    bench_parser.add_argument(
        "--metrics-dir", default="./metrics",
        help="Metrics directory (default: ./metrics)"
    )
    bench_parser.add_argument(
        "--manual-xp", type=float,
        help="Manual player XP/hour (for comparison)"
    )
    bench_parser.add_argument(
        "--manual-profit", type=float,
        help="Manual player profit/hour (for comparison)"
    )
    bench_parser.set_defaults(func=cmd_benchmark)
    
    # EXPORT command
    export_parser = subparsers.add_parser("export", help="Export metrics")
    export_parser.add_argument(
        "--input",
        help="Input metrics JSONL file"
    )
    export_parser.add_argument(
        "--output", default="metrics_export.csv",
        help="Output CSV file (default: metrics_export.csv)"
    )
    export_parser.add_argument(
        "--metrics-dir", default="./metrics",
        help="Metrics directory (default: ./metrics)"
    )
    export_parser.set_defaults(func=cmd_export)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Handle async commands
    if asyncio.iscoroutinefunction(args.func):
        return asyncio.run(args.func(args))
    else:
        return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
