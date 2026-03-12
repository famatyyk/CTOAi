# Pathing Spec

## Goal
Provide deterministic waypoint traversal with retry on blocked tile.

## Rules
- route loops when last waypoint is reached
- blocked tile retry counter increments up to max retries
- on retry budget exhausted, caller decides fallback strategy
