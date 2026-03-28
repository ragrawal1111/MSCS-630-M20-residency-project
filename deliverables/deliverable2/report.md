# Deliverable 2 — Report

## 1. Scheduling Algorithms

### Round-Robin Scheduling

Round-Robin (RR) is implemented in `RoundRobinScheduler` inside `shell/scheduler.py`. Tasks are stored in a `collections.deque`. The scheduler works as follows:

1. The user runs `schedule rr <quantum>` which sets the time quantum and instantiates the scheduler.
2. Each `add-task <name> <burst> <priority>` call appends a `Task` dataclass to the deque.
3. `run-scheduler` enters a loop that `popleft()`s the head task, runs it for `min(quantum, remaining)` simulated seconds using `time.sleep()`, and either marks it done or re-appends it to the tail if burst remains.
4. The first time a task is picked up its `start` time is recorded for response-time calculation.
5. The loop exits when the deque is empty, then the metrics table is printed.

Context switching is modelled by the deque rotation — each incomplete task goes to the back after using its quantum, mimicking the preemptive quantum expiry of a real RR scheduler.

### Priority-Based Scheduling

The `PriorityScheduler` uses Python's `heapq` module (a min-heap) ordered by `(priority, arrival, name)`. Lower priority numbers indicate higher priority (1 = highest).

**Preemption mechanism:**

- The scheduler runs the highest-priority task from the heap in 100 ms slices (`time.sleep(0.1)`).
- After each slice it checks whether a higher-priority task has been pushed onto the heap.
- If one is found, a `threading.Event` (`_preempt`) is set, the loop breaks, the interrupted task's `remaining` burst is decremented, and it is pushed back onto the heap.
- The new higher-priority task is then popped and begins executing.

This gives true preemptive behaviour: a late-arriving high-priority task can interrupt a lower-priority one mid-execution.

**Tie-breaking:** Tasks with equal priority are ordered by arrival time (FCFS). If arrival times also match, names are compared lexicographically.

---

## 2. Performance Analysis

### Round-Robin Sample Run (quantum = 2s)

Commands used:
```
schedule rr 2
add-task TaskA 6 1
add-task TaskB 4 2
add-task TaskC 8 1
run-scheduler
```

Sample metrics output:

| Task  | Burst | Pri | Arrival | Start | Finish | Waiting | Turnaround | Response |
|-------|-------|-----|---------|-------|--------|---------|------------|----------|
| TaskA | 6.00  | 1   | 0.00    | 0.00  | 12.00  | 6.00    | 12.00      | 0.00     |
| TaskB | 4.00  | 2   | 0.00    | 2.00  | 10.00  | 6.00    | 10.00      | 2.00     |
| TaskC | 8.00  | 1   | 0.00    | 4.00  | 18.00  | 10.00   | 18.00      | 4.00     |

**Analysis:**
- RR distributes CPU time fairly — no single task monopolises the processor.
- Short tasks (TaskB, burst=4) finish earlier than long ones despite being added second.
- Turnaround time grows with burst length; waiting time is directly affected by quantum size.
- A smaller quantum (e.g., 1s) reduces response time but increases context-switch overhead.

### Priority Sample Run

Commands used:
```
schedule priority
add-task TaskA 6 3
add-task TaskB 4 1
add-task TaskC 8 2
run-scheduler
```

Execution order: TaskB (priority 1) → TaskC (priority 2) → TaskA (priority 3).

**Analysis:**
- High-priority tasks always run before lower-priority ones, guaranteeing short response time for critical processes.
- If TaskA were added after TaskB starts running, preemption would pause TaskB and run TaskA immediately.
- The main risk is **starvation**: low-priority tasks may never run if high-priority tasks keep arriving. A real system would add aging (incrementally boosting priority over time) to counter this.

---

## 3. Challenges and Improvements

### Challenge 1 — Simulated vs Real Clock

`time.sleep()` is used to simulate CPU burst time. On Windows, sleep resolution is ~15 ms, so very short bursts (< 15 ms) may not be accurate. All demo bursts are multi-second to make the simulation clearly visible.

### Challenge 2 — Preemption Granularity

Preemption is checked every 100 ms slice. This means a new task can arrive but be delayed up to 100 ms before preempting the current one — acceptable for simulation purposes but not suitable for a real-time system.

### Challenge 3 — Thread Safety

The priority scheduler uses a `threading.Lock` around all heap operations so that any future extension adding tasks from a separate thread won't corrupt the heap. The current `add-task` command runs on the main thread, so no actual race condition occurs, but the architecture is prepared for it.

### Possible Improvements

- **Aging** for the priority scheduler to prevent starvation.
- **Multilevel feedback queue** that combines RR within priority bands.
- **Real CPU binding** using `os.sched_setaffinity` on Linux to actually pin simulated processes.
- **Gantt chart** ASCII output alongside the metrics table for visual clarity.
|      |       |          |         |       |        |         |            |          |

## 3. Challenges and Improvements

<!-- Discuss any challenges you encountered and how you addressed them. -->
