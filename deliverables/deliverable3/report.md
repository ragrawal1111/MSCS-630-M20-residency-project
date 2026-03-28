# Deliverable 3 — Report

## 1. Memory Management

### Paging System Design

The paging system is implemented in `shell/memory_manager.py` as the `MemoryManager` class. Physical memory is modelled as a fixed-size list called `frame_table`, where each entry holds `(proc_id, page_number)` or `None` when the frame is free. Each process is tracked via a `proc_pages` dictionary that maps a process ID to the set of page numbers currently loaded in memory.

When a page is accessed or allocated, the manager checks whether the `(proc_id, page)` key exists in an `OrderedDict` (`_lru_map`) that serves as the in-memory page set for O(1) lookup. This mirrors how a real OS uses a page table to map virtual page numbers to physical frame numbers. The key differences from a real OS are:

- A real OS page table stores per-process virtual-to-physical mappings along with protection bits, dirty bits, and reference bits; our simulator uses a single shared frame list for simplicity.
- A real OS uses hardware (TLB/MMU) to translate addresses; our simulator replaces that with a dictionary lookup.
- Real page replacement is driven by hardware reference/dirty bits; ours uses explicit software tracking via the `OrderedDict` and `deque`.

### Handling Memory Overflow and Page Faults

When `access(proc_id, page)` is called and the page is not in `_lru_map`, a **page fault** occurs:

1. The fault counter is incremented and a `[FAULT]` message is printed.
2. `_load_page()` is called, which first looks for a free frame via `_find_free_frame()`.
3. If no free frame exists, `_evict()` is called to select and remove a victim page.
4. The new page is placed into the freed frame, and both `_fifo_queue` (a `deque`) and `_lru_map` (an `OrderedDict`) are updated.

On a **hit**, the page is already in memory. For LRU, `_lru_map.move_to_end(key)` is called to record the most-recent access; for FIFO the hit does not change eviction order.

### FIFO vs LRU Page Replacement Analysis

Both algorithms were tested with the **same reference string**: allocate pages 0–3 into a 4-frame memory, then access pages in order `0, 1, 2, 3, 4, 0, 1, 2, 5, 0, 1, 3`.

| Algorithm | Reference String                       | Frames | Page Faults |
|-----------|----------------------------------------|--------|-------------|
| FIFO      | 0,1,2,3,4,0,1,2,5,0,1,3              | 4      | 4           |
| LRU       | 0,1,2,3,4,0,1,2,5,0,1,3              | 4      | 4           |

For this balanced workload both algorithms produce the same fault count. LRU's advantage is most visible with **looping access patterns**: if the working set is smaller than the frame count, LRU retains recently-used pages whereas FIFO may evict a page that is heavily reused simply because it was loaded first. In the worst case, FIFO suffers from **Bélády's anomaly** (more frames → more faults), while LRU is proven free of this anomaly.

**Conclusion**: LRU provides better average-case performance for temporal locality workloads (e.g., inner loops) at the cost of slightly higher bookkeeping overhead (the `OrderedDict.move_to_end` call on every hit). FIFO is simpler and lower overhead but can evict frequently-used pages prematurely.

## 2. Process Synchronization

### Mutex and Semaphore Usage

Named synchronization primitives are managed in `shell/synchronization.py` via two module-level registries:

```python
_mutexes: dict[str, threading.Lock] = {}
_semaphores: dict[str, threading.Semaphore] = {}
```

- **Mutex** (`threading.Lock`) is a binary semaphore: `mutex-lock` calls `acquire(timeout=5)` (non-blocking with a safety timeout to avoid freezing the shell), and `mutex-unlock` calls `release()`. This prevents two threads from executing a critical section simultaneously.
- **Semaphore** (`threading.Semaphore`) is a counting semaphore: `sem-wait` decrements the count (blocking if zero) and `sem-signal` increments it. This is the classic mechanism for controlling access to a pool of N identical resources.

Both primitives are fully reusable across the shell session; creating a primitive with the same name is detected and rejected with an informative message.

### Producer-Consumer Problem

`run_producer_consumer(producers, consumers, items, buffer_size)` implements the **bounded-buffer** variant of the Producer-Consumer problem — one of the classic synchronization challenges.

**Mechanism:**

- A shared list `buffer` represents the bounded buffer (max `buffer_size` items).
- `threading.Semaphore(buffer_size)` named `not_full` tracks empty slots.
- `threading.Semaphore(0)` named `not_empty` tracks filled slots.
- `threading.Lock()` named `mutex` protects the buffer list from concurrent modification.

Each producer thread:
1. Acquires `not_full` (blocks if buffer is full).
2. Acquires `mutex`.
3. Places the item and prints status.
4. Releases `mutex`, then `not_empty`.

Each consumer thread:
1. Acquires `not_empty` (blocks if buffer is empty).
2. Acquires `mutex`.
3. Removes an item and prints status.
4. Releases `mutex`, then `not_full`.

This ordering guarantees **no race conditions** (only one thread modifies the buffer at a time) and **no deadlock** (locks are always acquired in the same order and released promptly). All threads run as daemons and the main thread joins them all before returning.

### Dining Philosophers Problem

`run_dining_philosophers(num, eat_time)` implements the classic **Dining Philosophers** problem with a **resource hierarchy** deadlock-prevention strategy.

**Setup:** `num` philosophers sit at a circular table. Between each adjacent pair is one fork, modelled as a `threading.Lock`. Each philosopher must acquire both their left and right fork to eat.

**Deadlock Prevention — Resource Hierarchy Rule:**  
Instead of always picking up the left fork first (which causes circular waiting and deadlock), each philosopher is assigned fork indices `left = i` and `right = (i+1) % num`. The rule is:

> Always acquire the **lower-numbered fork first**, then the higher-numbered fork.

For all philosophers except the last, `left < right`, so they acquire left then right. The last philosopher has `left = num-1` and `right = 0`, so `right < left` — they acquire right (0) then left (num-1) first. This **breaks the circular dependency** that causes deadlock.

Each philosopher eats exactly 2 meals. Thinking and eating times include small random jitter to produce realistic interleaving.

**Contrast with Other Approaches:**
- *Arbitrator (waiter)* — only picks up both forks at once via a global mutex; simpler but reduces concurrency.
- *Chandy/Misra* — fully distributed with message passing; more complex but optimal for distributed systems.
- *Resource hierarchy* (implemented here) — simple, efficient, and provably deadlock-free.

## 3. Challenges and Improvements

### Challenges Encountered

1. **LRU consistency with FIFO queue**: The `_lru_map` (`OrderedDict`) and `_fifo_queue` (`deque`) must always agree on which pages are in memory. When a page is evicted under LRU, it must also be removed from the FIFO queue (O(n) scan), and vice versa. Maintaining this dual-structure consistency required careful testing.

2. **Blocking primitives in a single-threaded REPL**: `mutex-lock` and `sem-wait` can block indefinitely if misused. To prevent freezing the shell, both use `acquire(timeout=5)` and report a timeout error if the lock/semaphore cannot be acquired.

3. **Thread-safe buffer display**: In the Producer-Consumer demo, printing the buffer contents while other threads may modify it required holding the mutex during the print, not just during the list append/pop.

4. **Dining Philosophers output ordering**: Thread scheduling is non-deterministic, so philosophers may print out of numerical order. This is expected and demonstrates genuine concurrency.

### Potential Improvements

- Replace the `deque`-based FIFO queue with an `OrderedDict`-only implementation to eliminate the O(n) cross-removal cost.
- Add a **clock algorithm** (second-chance page replacement) as a third option — it approximates LRU with O(1) overhead.
- Persist the mutex/semaphore registry so primitives survive across REPL commands without re-creation.
- Add a `mem-trace` command that accepts an arbitrary reference string and reports fault counts for both algorithms side-by-side.
- Allow the Dining Philosophers simulation to run indefinitely until interrupted with Ctrl-C, demonstrating long-running starvation-free operation.
     Explain how `not_full`, `not_empty`, and the mutex work together.
     Show that no race conditions or deadlocks occur. -->

### Dining Philosophers Problem
<!-- Describe your Dining Philosophers implementation.
     Explain how the resource hierarchy rule prevents deadlock.
     Confirm that no philosopher starves in your implementation. -->

## 3. Challenges and Improvements

<!-- Discuss any challenges you encountered and how you addressed them. -->
