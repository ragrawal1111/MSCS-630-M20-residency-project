"""
=============================================================================
Deliverable 3 — Memory Management & Synchronization: Source Code
=============================================================================
This file consolidates all source modules required for Deliverable 3:
  • shell/memory_manager.py   — paging with FIFO and LRU page replacement
  • shell/synchronization.py  — mutex/semaphore primitives, Producer-Consumer,
                                 Dining Philosophers
  • main.py additions         — shell command handlers for all D3 commands

Memory management commands:
  mem-init <frames> [fifo|lru]       — initialise memory with N frames
  mem-alloc <proc_id> <pages...>     — pre-load pages for a process
  mem-access <proc_id> <page>        — simulate a memory access (HIT/FAULT)
  mem-status                         — print the current frame table
  mem-free <proc_id>                 — release all frames for a process

Synchronization commands:
  mutex-create <name>
  mutex-lock   <name>
  mutex-unlock <name>
  sem-create   <name> <value>
  sem-wait     <name>
  sem-signal   <name>
  run-producer-consumer <producers> <consumers> <items> <buffer_size>
  run-dining-philosophers <num_philosophers> <eat_time>
=============================================================================
"""

# =============================================================================
# FILE: shell/memory_manager.py
# =============================================================================
"""
memory_manager.py — Paging system with FIFO and LRU page replacement.

Shell commands (wired in main.py):
  mem-init <frames> [fifo|lru]   — initialise with N frames, choose algorithm
  mem-alloc <proc_id> <pages>    — allocate page numbers to a process
  mem-access <proc_id> <page>    — simulate a memory access (HIT / FAULT)
  mem-status                     — print current frame table
  mem-free <proc_id>             — release all pages for a process
"""

from collections import OrderedDict, deque


class MemoryManager:
    """Simulates physical memory as a fixed number of frames."""

    def __init__(self, num_frames: int, algorithm: str = "fifo"):
        self.num_frames = num_frames
        self.algorithm = algorithm.lower()

        # frame_table: frame_id -> (proc_id, page_num) or None
        self.frame_table: list = [None] * num_frames

        # Per-process page sets  {proc_id: set of page numbers loaded}
        self.proc_pages: dict = {}

        # FIFO queue — stores (proc_id, page_num) in load order
        self._fifo_queue: deque = deque()

        # LRU ordered dict — key=(proc_id,page), ordered by recency
        self._lru_map: OrderedDict = OrderedDict()

        self.page_faults = 0
        self.page_hits = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_free_frame(self):
        for i, slot in enumerate(self.frame_table):
            if slot is None:
                return i
        return None

    def _evict(self) -> int:
        """Evict a page according to the replacement algorithm.
        Returns the freed frame index."""
        if self.algorithm == "fifo":
            victim_key = self._fifo_queue.popleft()
        else:  # lru
            victim_key, _ = self._lru_map.popitem(last=False)

        victim_proc, victim_page = victim_key

        # Remove from the other structure too (keep them consistent)
        if self.algorithm == "fifo":
            self._lru_map.pop(victim_key, None)
        else:
            try:
                self._fifo_queue.remove(victim_key)
            except ValueError:
                pass

        # Free the frame
        frame_idx = next(
            i for i, slot in enumerate(self.frame_table)
            if slot == victim_key
        )
        self.frame_table[frame_idx] = None

        # Update proc_pages
        if victim_proc in self.proc_pages:
            self.proc_pages[victim_proc].discard(victim_page)

        print(f"  [EVICT] {victim_proc} page {victim_page} "
              f"evicted from frame {frame_idx} ({self.algorithm.upper()})")
        return frame_idx

    def _load_page(self, proc_id: str, page: int) -> None:
        """Load (proc_id, page) into a free or evicted frame."""
        frame_idx = self._find_free_frame()
        if frame_idx is None:
            frame_idx = self._evict()

        key = (proc_id, page)
        self.frame_table[frame_idx] = key
        self._fifo_queue.append(key)
        self._lru_map[key] = True

        self.proc_pages.setdefault(proc_id, set()).add(page)
        print(f"  [LOAD ] {proc_id} page {page} → frame {frame_idx}")

    # ------------------------------------------------------------------
    # Public commands
    # ------------------------------------------------------------------

    def alloc(self, proc_id: str, pages: list) -> None:
        """Pre-load a set of pages for a process."""
        print(f"Allocating {len(pages)} pages for {proc_id}: {pages}")
        for page in pages:
            key = (proc_id, page)
            if key in self._lru_map:
                print(f"  Page {page} already loaded for {proc_id}")
            else:
                self._load_page(proc_id, page)

    def access(self, proc_id: str, page: int) -> None:
        """Simulate a memory access. Prints HIT or FAULT."""
        key = (proc_id, page)
        if key in self._lru_map:
            # HIT — update LRU order
            self._lru_map.move_to_end(key)
            self.page_hits += 1
            frame_idx = next(i for i, s in enumerate(self.frame_table) if s == key)
            print(f"  [HIT  ] {proc_id} page {page} in frame {frame_idx}")
        else:
            # FAULT
            self.page_faults += 1
            print(f"  [FAULT] {proc_id} page {page} — page fault #{self.page_faults}")
            self._load_page(proc_id, page)

    def status(self) -> None:
        """Print the current frame table."""
        print(f"\n{'Frame':<8} {'Process':<10} {'Page':<8}")
        print("-" * 26)
        for i, slot in enumerate(self.frame_table):
            if slot is None:
                print(f"{i:<8} {'—':<10} {'—':<8}")
            else:
                proc, page = slot
                print(f"{i:<8} {proc:<10} {page:<8}")
        print(f"\nPage faults: {self.page_faults}  |  Hits: {self.page_hits}\n")

    def free(self, proc_id: str) -> None:
        """Release all frames held by proc_id."""
        freed = 0
        for i, slot in enumerate(self.frame_table):
            if slot and slot[0] == proc_id:
                key = slot
                self.frame_table[i] = None
                self._lru_map.pop(key, None)
                try:
                    self._fifo_queue.remove(key)
                except ValueError:
                    pass
                freed += 1
        self.proc_pages.pop(proc_id, None)
        print(f"Freed {freed} frame(s) for {proc_id}")


# ---------------------------------------------------------------------------
# Active singleton
# ---------------------------------------------------------------------------
_mem = None


def set_memory_manager(m: MemoryManager) -> None:
    global _mem
    _mem = m


def get_memory_manager():
    return _mem


# =============================================================================
# FILE: shell/synchronization.py
# =============================================================================
"""
synchronization.py — Mutex/semaphore primitives, Producer-Consumer,
                     and Dining Philosophers for Deliverable 3.

Shell commands (wired in main.py):
  mutex-create <name>
  mutex-lock   <name>
  mutex-unlock <name>
  sem-create   <name> <value>
  sem-wait     <name>
  sem-signal   <name>
  run-producer-consumer <producers> <consumers> <items> <buffer_size>
  run-dining-philosophers <num_philosophers> <eat_time>
"""

import threading
import time
import random

# ---------------------------------------------------------------------------
# Named primitives registry
# ---------------------------------------------------------------------------

_mutexes: dict = {}
_semaphores: dict = {}


def mutex_create(name: str) -> None:
    if name in _mutexes:
        print(f"shell: mutex-create: '{name}' already exists")
        return
    _mutexes[name] = threading.Lock()
    print(f"Mutex '{name}' created")


def mutex_lock(name: str) -> None:
    if name not in _mutexes:
        print(f"shell: mutex-lock: '{name}' not found. Use mutex-create first.")
        return
    acquired = _mutexes[name].acquire(timeout=5)
    if acquired:
        print(f"Mutex '{name}' locked")
    else:
        print(f"shell: mutex-lock: '{name}' timed out (already held?)")


def mutex_unlock(name: str) -> None:
    if name not in _mutexes:
        print(f"shell: mutex-unlock: '{name}' not found")
        return
    try:
        _mutexes[name].release()
        print(f"Mutex '{name}' unlocked")
    except RuntimeError:
        print(f"shell: mutex-unlock: '{name}' was not locked")


def sem_create(name: str, value: int) -> None:
    if name in _semaphores:
        print(f"shell: sem-create: '{name}' already exists")
        return
    _semaphores[name] = threading.Semaphore(value)
    print(f"Semaphore '{name}' created (initial={value})")


def sem_wait(name: str) -> None:
    if name not in _semaphores:
        print(f"shell: sem-wait: '{name}' not found. Use sem-create first.")
        return
    acquired = _semaphores[name].acquire(timeout=5)
    if acquired:
        print(f"Semaphore '{name}' decremented (wait OK)")
    else:
        print(f"shell: sem-wait: '{name}' timed out (value=0?)")


def sem_signal(name: str) -> None:
    if name not in _semaphores:
        print(f"shell: sem-signal: '{name}' not found")
        return
    _semaphores[name].release()
    print(f"Semaphore '{name}' incremented (signal OK)")


# ---------------------------------------------------------------------------
# Producer-Consumer
# ---------------------------------------------------------------------------

def run_producer_consumer(
    num_producers: int,
    num_consumers: int,
    total_items: int,
    buffer_size: int,
) -> None:
    """Classic bounded-buffer Producer-Consumer using semaphores + mutex."""

    buffer: list = []
    mutex   = threading.Lock()
    not_full  = threading.Semaphore(buffer_size)   # slots available
    not_empty = threading.Semaphore(0)              # items available

    produced_count = [0]
    consumed_count = [0]
    lock_count = threading.Lock()

    print(f"\n[Producer-Consumer] producers={num_producers}, consumers={num_consumers}, "
          f"items={total_items}, buffer={buffer_size}")
    print("-" * 60)

    def producer(pid: int):
        while True:
            with lock_count:
                if produced_count[0] >= total_items:
                    return
                produced_count[0] += 1
                item = produced_count[0]

            not_full.acquire()
            with mutex:
                buffer.append(item)
                print(f"  Producer-{pid} produced item {item:3d}  "
                      f"| buffer={buffer[:]}")
            not_empty.release()
            time.sleep(random.uniform(0.05, 0.15))

    def consumer(cid: int):
        while True:
            acquired = not_empty.acquire(timeout=3)
            if not acquired:
                return
            with mutex:
                if not buffer:
                    not_empty.release()
                    return
                item = buffer.pop(0)
                print(f"  Consumer-{cid} consumed item {item:3d}  "
                      f"| buffer={buffer[:]}")
            not_full.release()
            with lock_count:
                consumed_count[0] += 1
            time.sleep(random.uniform(0.05, 0.2))

    threads = []
    for i in range(num_producers):
        t = threading.Thread(target=producer, args=(i + 1,), daemon=True)
        threads.append(t)
    for i in range(num_consumers):
        t = threading.Thread(target=consumer, args=(i + 1,), daemon=True)
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    print("-" * 60)
    print(f"Done. Produced: {produced_count[0]}, Consumed: {consumed_count[0]}\n")


# ---------------------------------------------------------------------------
# Dining Philosophers
# ---------------------------------------------------------------------------

def run_dining_philosophers(num: int, eat_time: float) -> None:
    """
    Deadlock-free Dining Philosophers using resource hierarchy.
    Philosopher i always picks up fork min(i, right) before max(i, right).
    """

    forks = [threading.Lock() for _ in range(num)]
    print(f"\n[Dining Philosophers] philosophers={num}, eat_time={eat_time}s")
    print("-" * 60)

    meals = [0] * num

    def philosopher(idx: int):
        left  = idx
        right = (idx + 1) % num
        # Resource hierarchy: always acquire lower-numbered fork first
        first, second = (left, right) if left < right else (right, left)

        for _ in range(2):   # each philosopher eats twice
            # Think
            think = random.uniform(0.05, 0.2)
            print(f"  Philosopher {idx} is THINKING for {think:.2f}s")
            time.sleep(think)

            # Pick up forks
            print(f"  Philosopher {idx} WAITING for forks {first} and {second}")
            forks[first].acquire()
            forks[second].acquire()

            # Eat
            print(f"  Philosopher {idx} is EATING  for {eat_time}s "
                  f"(forks {first} & {second})")
            time.sleep(eat_time)
            meals[idx] += 1

            # Put down forks
            forks[second].release()
            forks[first].release()
            print(f"  Philosopher {idx} finished eating (total meals: {meals[idx]})")

    threads = [threading.Thread(target=philosopher, args=(i,), daemon=True)
               for i in range(num)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    print("-" * 60)
    print(f"All philosophers finished. Meals eaten: {meals}\n")


# =============================================================================
# FILE: main.py  (Deliverable 3 — memory & synchronization command handlers)
# =============================================================================
"""
Command handlers for memory management and synchronization commands.
In the full project these live in main.py and are dispatched by the REPL loop.
"""
import sys


def _cmd_mem_init(args: list) -> None:
    """mem-init <frames> [fifo|lru]"""
    if not args:
        print("shell: mem-init: usage: mem-init <frames> [fifo|lru]")
        return
    try:
        frames = int(args[0])
    except ValueError:
        print(f"shell: mem-init: invalid frame count '{args[0]}'")
        return
    algo = args[1].lower() if len(args) > 1 else "fifo"
    if algo not in ("fifo", "lru"):
        print(f"shell: mem-init: unknown algorithm '{algo}'. Use fifo or lru.")
        return
    set_memory_manager(MemoryManager(frames, algo))
    print(f"Memory manager initialised: {frames} frames, {algo.upper()} replacement.")


def _cmd_mem_alloc(args: list) -> None:
    """mem-alloc <proc_id> <page0> [page1 ...]"""
    if len(args) < 2:
        print("shell: mem-alloc: usage: mem-alloc <proc_id> <pages...>")
        return
    mem = get_memory_manager()
    if mem is None:
        print("shell: mem-alloc: no memory manager. Run 'mem-init' first.")
        return
    proc_id = args[0]
    try:
        pages = [int(p) for p in args[1:]]
    except ValueError:
        print("shell: mem-alloc: page numbers must be integers")
        return
    mem.alloc(proc_id, pages)


def _cmd_mem_access(args: list) -> None:
    """mem-access <proc_id> <page>"""
    if len(args) < 2:
        print("shell: mem-access: usage: mem-access <proc_id> <page>")
        return
    mem = get_memory_manager()
    if mem is None:
        print("shell: mem-access: no memory manager. Run 'mem-init' first.")
        return
    try:
        page = int(args[1])
    except ValueError:
        print(f"shell: mem-access: invalid page number '{args[1]}'")
        return
    mem.access(args[0], page)


def _cmd_mem_status(args: list) -> None:
    """mem-status"""
    mem = get_memory_manager()
    if mem is None:
        print("shell: mem-status: no memory manager. Run 'mem-init' first.")
        return
    mem.status()


def _cmd_mem_free(args: list) -> None:
    """mem-free <proc_id>"""
    if not args:
        print("shell: mem-free: usage: mem-free <proc_id>")
        return
    mem = get_memory_manager()
    if mem is None:
        print("shell: mem-free: no memory manager. Run 'mem-init' first.")
        return
    mem.free(args[0])


def _cmd_mutex_create(args: list) -> None:
    if not args:
        print("shell: mutex-create: usage: mutex-create <name>"); return
    mutex_create(args[0])


def _cmd_mutex_lock(args: list) -> None:
    if not args:
        print("shell: mutex-lock: usage: mutex-lock <name>"); return
    mutex_lock(args[0])


def _cmd_mutex_unlock(args: list) -> None:
    if not args:
        print("shell: mutex-unlock: usage: mutex-unlock <name>"); return
    mutex_unlock(args[0])


def _cmd_sem_create(args: list) -> None:
    if len(args) < 2:
        print("shell: sem-create: usage: sem-create <name> <value>"); return
    try:
        val = int(args[1])
    except ValueError:
        print(f"shell: sem-create: invalid value '{args[1]}'"); return
    sem_create(args[0], val)


def _cmd_sem_wait(args: list) -> None:
    if not args:
        print("shell: sem-wait: usage: sem-wait <name>"); return
    sem_wait(args[0])


def _cmd_sem_signal(args: list) -> None:
    if not args:
        print("shell: sem-signal: usage: sem-signal <name>"); return
    sem_signal(args[0])


def _cmd_run_producer_consumer(args: list) -> None:
    """run-producer-consumer <producers> <consumers> <items> <buffer_size>"""
    if len(args) < 4:
        print("shell: run-producer-consumer: usage: run-producer-consumer "
              "<producers> <consumers> <items> <buffer_size>")
        return
    try:
        p, c, items, buf = int(args[0]), int(args[1]), int(args[2]), int(args[3])
    except ValueError:
        print("shell: run-producer-consumer: all arguments must be integers"); return
    run_producer_consumer(p, c, items, buf)


def _cmd_run_dining_philosophers(args: list) -> None:
    """run-dining-philosophers <num> <eat_time>"""
    if len(args) < 2:
        print("shell: run-dining-philosophers: usage: "
              "run-dining-philosophers <num> <eat_time>")
        return
    try:
        num = int(args[0])
        eat = float(args[1])
    except ValueError:
        print("shell: run-dining-philosophers: invalid arguments"); return
    run_dining_philosophers(num, eat)


# ---------------------------------------------------------------------------
# Standalone demo  (python source_code.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Memory Manager Demo (FIFO, 3 frames) ===")
    _cmd_mem_init(["3", "fifo"])
    _cmd_mem_alloc(["P1", "0", "1", "2"])
    _cmd_mem_alloc(["P2", "3"])          # triggers eviction
    _cmd_mem_access(["P1", "0"])         # should be FAULT (evicted)
    _cmd_mem_access(["P2", "3"])         # should be HIT
    _cmd_mem_status([])
    _cmd_mem_free(["P1"])

    print("\n=== Producer-Consumer Demo ===")
    _cmd_run_producer_consumer(["2", "2", "6", "3"])

    print("\n=== Dining Philosophers Demo ===")
    _cmd_run_dining_philosophers(["4", "0.2"])
