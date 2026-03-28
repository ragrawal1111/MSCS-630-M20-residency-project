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
        self.proc_pages: dict[str, set] = {}

        # FIFO queue — stores (proc_id, page_num) in load order
        self._fifo_queue: deque = deque()

        # LRU ordered dict — key=(proc_id,page) , value irrelevant; ordered by recency
        self._lru_map: OrderedDict = OrderedDict()

        self.page_faults = 0
        self.page_hits = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_free_frame(self) -> int | None:
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
            # Remove from fifo queue (O(n) but acceptable for simulation)
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

    def alloc(self, proc_id: str, pages: list[int]) -> None:
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
_mem: MemoryManager | None = None


def set_memory_manager(m: MemoryManager) -> None:
    global _mem
    _mem = m


def get_memory_manager() -> MemoryManager | None:
    return _mem
