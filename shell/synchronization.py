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

_mutexes: dict[str, threading.Lock] = {}
_semaphores: dict[str, threading.Semaphore] = {}


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
                return   # no more items coming
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

    done_event = threading.Event()
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
