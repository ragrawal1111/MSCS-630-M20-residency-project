"""
scheduler.py — Process scheduling algorithms for Deliverable 2.

Provides:
  RoundRobinScheduler   — time-quantum based cycling via deque
  PriorityScheduler     — min-heap by priority with preemption via threading.Event

Shell commands handled in main.py:
  schedule rr <quantum>              — create a Round-Robin session
  schedule priority                  — create a Priority session
  add-task <name> <burst> <priority> — add a task to active session
  run-scheduler                      — execute and print metrics table
"""

import heapq
import threading
import time
from collections import deque
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Shared data structure
# ---------------------------------------------------------------------------

@dataclass
class Task:
    name: str
    burst: float          # total CPU time needed (seconds)
    priority: int         # lower number = higher priority
    arrival: float = field(default_factory=time.time)

    # Metrics filled in during execution
    start: float = 0.0
    finish: float = 0.0
    remaining: float = 0.0

    def __post_init__(self):
        self.remaining = self.burst

    # For heapq comparison (priority, arrival, name)
    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority < other.priority
        if self.arrival != other.arrival:
            return self.arrival < other.arrival
        return self.name < other.name


def _print_metrics(tasks: list[Task]) -> None:
    """Print a formatted metrics table for all completed tasks."""
    header = f"{'Task':<12} {'Burst':>6} {'Pri':>4} {'Arrival':>9} {'Start':>9} {'Finish':>9} {'Waiting':>9} {'Turnaround':>11} {'Response':>9}"
    print("\n" + "=" * len(header))
    print(header)
    print("-" * len(header))
    for t in tasks:
        turnaround = t.finish - t.arrival
        waiting    = turnaround - t.burst
        response   = t.start - t.arrival
        print(
            f"{t.name:<12} {t.burst:>6.2f} {t.priority:>4} "
            f"{t.arrival:>9.2f} {t.start:>9.2f} {t.finish:>9.2f} "
            f"{waiting:>9.2f} {turnaround:>11.2f} {response:>9.2f}"
        )
    print("=" * len(header) + "\n")


# ---------------------------------------------------------------------------
# Round-Robin Scheduler
# ---------------------------------------------------------------------------

class RoundRobinScheduler:
    """Simulates Round-Robin scheduling with a configurable time quantum."""

    def __init__(self, quantum: float):
        self.quantum = quantum
        self.queue: deque[Task] = deque()
        self._completed: list[Task] = []

    def add_task(self, name: str, burst: float, priority: int) -> None:
        self.queue.append(Task(name=name, burst=burst, priority=priority))
        print(f"  Task '{name}' added (burst={burst}s, priority={priority})")

    def run(self) -> None:
        if not self.queue:
            print("scheduler: no tasks to run")
            return

        print(f"\n[Round-Robin | quantum={self.quantum}s]")
        current_time = time.time()
        # Normalise arrival times so they display from 0
        base = self.queue[0].arrival
        for t in self.queue:
            t.arrival = round(t.arrival - base, 3)

        clock = 0.0  # simulated clock (seconds from base)

        while self.queue:
            task = self.queue.popleft()

            if task.start == 0.0 and task.remaining == task.burst:
                task.start = clock

            run_for = min(self.quantum, task.remaining)
            print(f"  t={clock:.2f}  Running '{task.name}' for {run_for:.2f}s "
                  f"(remaining after: {task.remaining - run_for:.2f}s)")
            time.sleep(run_for)
            clock += run_for
            task.remaining -= run_for

            if task.remaining <= 0:
                task.finish = clock
                self._completed.append(task)
                print(f"  t={clock:.2f}  '{task.name}' DONE")
            else:
                self.queue.append(task)

        _print_metrics(self._completed)
        self._completed.clear()


# ---------------------------------------------------------------------------
# Priority Scheduler (with preemption)
# ---------------------------------------------------------------------------

class PriorityScheduler:
    """
    Simulates preemptive Priority scheduling.

    A background listener thread waits for new tasks added during execution.
    When a higher-priority task arrives it sets a preemption event that
    interrupts the currently running task.
    """

    def __init__(self):
        self._heap: list[Task] = []
        self._lock = threading.Lock()
        self._preempt = threading.Event()
        self._pending: list[Task] = []    # tasks added before run()
        self._completed: list[Task] = []

    def add_task(self, name: str, burst: float, priority: int) -> None:
        task = Task(name=name, burst=burst, priority=priority)
        with self._lock:
            heapq.heappush(self._heap, task)
        print(f"  Task '{name}' added (burst={burst}s, priority={priority})")

    def run(self) -> None:
        if not self._heap:
            print("scheduler: no tasks to run")
            return

        print("\n[Priority Scheduler | preemptive]")

        # Normalise arrival times
        base = self._heap[0].arrival
        with self._lock:
            for t in self._heap:
                t.arrival = round(abs(t.arrival - base), 3)

        clock = 0.0

        while True:
            with self._lock:
                if not self._heap:
                    break
                task = heapq.heappop(self._heap)

            if task.start == 0.0 and task.remaining == task.burst:
                task.start = clock

            print(f"  t={clock:.2f}  Running '{task.name}' "
                  f"(priority={task.priority}, remaining={task.remaining:.2f}s)")

            self._preempt.clear()
            slice_size = 0.1          # check for preemption every 100 ms
            elapsed = 0.0

            while elapsed < task.remaining:
                step = min(slice_size, task.remaining - elapsed)
                time.sleep(step)
                elapsed += step

                # Check if a higher-priority task has arrived
                with self._lock:
                    if self._heap and self._heap[0].priority < task.priority:
                        self._preempt.set()
                        break

            task.remaining -= elapsed

            if task.remaining <= 0.01:
                clock += task.burst if task.start == clock else elapsed
                # Recalculate finish properly
                task.finish = clock
                self._completed.append(task)
                print(f"  t={clock:.2f}  '{task.name}' DONE")
            else:
                # Preempted — re-queue with updated remaining
                clock += elapsed
                print(f"  t={clock:.2f}  '{task.name}' PREEMPTED "
                      f"(remaining={task.remaining:.2f}s)")
                with self._lock:
                    heapq.heappush(self._heap, task)

        _print_metrics(self._completed)
        self._completed.clear()


# ---------------------------------------------------------------------------
# Active session singleton (reset by 'schedule' command)
# ---------------------------------------------------------------------------

_active_scheduler = None


def set_scheduler(scheduler) -> None:
    global _active_scheduler
    _active_scheduler = scheduler


def get_scheduler():
    return _active_scheduler
