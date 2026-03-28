# Deliverable 3 — Memory Management and Process Synchronization

## Status: Complete

## What to Submit
- [x] Source code (`shell/memory_manager.py`, `shell/synchronization.py`)
- [x] Report (see `report.md`)
- [x] Screenshots (place in `screenshots/` folder)

## Key Files
| File | Purpose |
|------|---------|
| `shell/memory_manager.py` | Frame table, page fault handling, FIFO/LRU eviction |
| `shell/synchronization.py` | Mutex/semaphore wrappers, Producer-Consumer, Dining Philosophers |

## Memory Commands to Demonstrate
```
mem-init 4 fifo         # 4 frames, FIFO replacement
mem-alloc P1 3
mem-access P1 0         # HIT or FAULT
mem-access P1 1
mem-access P1 3         # triggers page fault + replacement
mem-status
mem-free P1

mem-init 4 lru          # same scenario with LRU
```

## Synchronization Commands to Demonstrate
```
run-producer-consumer 2 2 10 4
run-dining-philosophers 5 1
```

## Notes
<!-- Add implementation notes here as you work -->
