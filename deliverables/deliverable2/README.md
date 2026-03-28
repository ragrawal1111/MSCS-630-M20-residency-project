# Deliverable 2 — Process Scheduling

## Status: Complete

## What to Submit
- [x] Source code for scheduling algorithms (`shell/scheduler.py`)
- [x] Report (see `report.md`)
- [ ] Screenshots (place in `screenshots/` folder)

## Key Files
| File | Purpose |
|------|---------|
| `shell/scheduler.py` | `RoundRobinScheduler`, `PriorityScheduler`, metrics collection |

## Commands to Demonstrate
```
schedule rr 2           # Round-Robin with quantum=2
add-task TaskA 6 1
add-task TaskB 4 2
add-task TaskC 8 1
run-scheduler           # prints metrics table
```

```
schedule priority
add-task TaskA 6 3
add-task TaskB 4 1
add-task TaskC 8 2
run-scheduler           # TaskB runs first (priority 1 = highest)
```

## Metrics to Capture
- Waiting Time
- Turnaround Time
- Response Time

## Notes
<!-- Add implementation notes here as you work -->
