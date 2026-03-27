# Project Checklist — Advanced Shell Simulation

Track progress for all four deliverables. Mark items with `[x]` as you complete them.

---

## Deliverable 1: Basic Shell Implementation and Process Management

### Core Shell
- [x] REPL loop reads user input and dispatches commands
- [x] Command tokenizer handles quoted strings and escapes (`shlex.split`)
- [x] Background execution detected via trailing `&`
- [x] Unknown commands print `shell: command not found: <cmd>`
- [x] Graceful exit on `Ctrl+C` and `Ctrl+D`

### Built-in Commands
- [x] `cd [dir]` — changes working directory, handles non-existent paths
- [x] `pwd` — prints current working directory
- [x] `exit` — exits the shell cleanly
- [x] `echo [text]` — prints text to stdout
- [x] `clear` — clears the terminal screen
- [x] `ls` — lists files in current directory
- [x] `cat [file]` — prints file contents, handles missing files
- [x] `mkdir [dir]` — creates directory, handles existing paths
- [x] `rmdir [dir]` — removes empty directory, handles non-empty case
- [x] `rm [file]` — removes file, handles missing files
- [x] `touch [file]` — creates or updates file timestamp
- [x] `kill [pid]` — sends SIGTERM to process, handles invalid PIDs

### Process Management
- [x] Foreground processes block the shell until completion
- [x] Background processes (`cmd &`) run without blocking
- [x] Job table tracks all background/stopped processes
- [x] `jobs` — lists all jobs with ID, PID, status, and command
- [x] `fg [job_id]` — brings a background job to the foreground
- [x] `bg [job_id]` — resumes a stopped job in the background
- [x] Zombie processes are reaped via `waitpid`

### Error Handling
- [x] Invalid command → helpful error message
- [x] Missing arguments → usage hint printed
- [x] Permission denied → clear error message
- [x] File not found → clear error message

### Report
- [x] Source code submitted
- [ ] Screenshots: built-in commands running
- [ ] Screenshots: foreground and background process execution
- [ ] Screenshots: error handling in action
- [x] Report section: process creation and management explained
- [x] Report section: error handling approach described
- [x] Report section: challenges and improvements discussed

---

## Deliverable 2: Process Scheduling

### Round-Robin Scheduler
- [ ] `schedule rr <quantum>` sets up a Round-Robin session with given time quantum
- [ ] `add-task <name> <burst> <priority>` adds tasks to the queue
- [ ] `run-scheduler` executes all tasks in Round-Robin order
- [ ] Tasks are cycled using a deque; incomplete tasks re-queued
- [ ] `time.sleep()` simulates process execution
- [ ] Completed tasks removed from queue automatically
- [ ] Quantum is configurable per session

### Priority-Based Scheduler
- [ ] `schedule priority` sets up a Priority-Based session
- [ ] Tasks stored in a min-heap (`heapq`) ordered by priority
- [ ] Highest-priority task always selected next
- [ ] Equal-priority tasks handled FCFS (arrival order tie-break)
- [ ] Preemption: higher-priority task added mid-run interrupts current task
- [ ] Preemption implemented via `threading.Event`

### Metrics
- [ ] Arrival time recorded per task
- [ ] Start time recorded per task
- [ ] Finish time recorded per task
- [ ] Waiting time calculated: `turnaround - burst`
- [ ] Turnaround time calculated: `finish - arrival`
- [ ] Response time calculated: `start - arrival`
- [ ] Metrics table printed after `run-scheduler` completes

### Report
- [ ] Source code submitted
- [ ] Screenshots: Round-Robin execution with quantum config and switching
- [ ] Screenshots: Priority-Based execution showing preemption
- [ ] Screenshots: metrics table output
- [ ] Report section: Round-Robin algorithm explained
- [ ] Report section: Priority-Based algorithm and preemption explained
- [ ] Report section: performance analysis with metrics
- [ ] Report section: challenges and improvements discussed

---

## Deliverable 3: Memory Management and Process Synchronization

### Paging System
- [ ] `mem-init <frames> [fifo|lru]` initializes memory manager
- [ ] `mem-alloc <proc_id> <pages>` assigns pages to a process
- [ ] `mem-access <proc_id> <page>` simulates page access (HIT or FAULT)
- [ ] Page fault count tracked and displayed
- [ ] `mem-status` shows all frames with current contents
- [ ] `mem-free <proc_id>` deallocates all pages for a process

### FIFO Page Replacement
- [ ] Pages evicted in the order they were loaded (queue-based)
- [ ] Victim frame identified and replaced on overflow
- [ ] FIFO queue updated after each replacement

### LRU Page Replacement
- [ ] Pages evicted based on least-recent access time
- [ ] LRU order updated on every access (hit or fault)
- [ ] Correct victim selected on overflow

### Process Synchronization — Primitives
- [ ] `mutex-create <name>` creates a named mutex (`threading.Lock`)
- [ ] `mutex-lock <name>` acquires mutex
- [ ] `mutex-unlock <name>` releases mutex
- [ ] `sem-create <name> <value>` creates a named semaphore (`threading.Semaphore`)
- [ ] `sem-wait <name>` decrements semaphore (blocks if zero)
- [ ] `sem-signal <name>` increments semaphore

### Producer-Consumer
- [ ] `run-producer-consumer <producers> <consumers> <items> <buffer_size>` runs demo
- [ ] Semaphores `not_full` and `not_empty` control buffer access
- [ ] Mutex protects buffer list from concurrent modification
- [ ] No race conditions or deadlocks occur during execution
- [ ] Output shows producers/consumers running concurrently

### Dining Philosophers
- [ ] `run-dining-philosophers <num> <eat_time>` runs demo
- [ ] Each fork represented by a `threading.Lock`
- [ ] Resource hierarchy rule: always acquire lower-numbered fork first
- [ ] No deadlock occurs during execution
- [ ] Output shows philosophers thinking, waiting, and eating

### Report
- [ ] Source code submitted
- [ ] Screenshots: memory allocation and deallocation
- [ ] Screenshots: FIFO page replacement in action
- [ ] Screenshots: LRU page replacement in action
- [ ] Screenshots: Producer-Consumer synchronization output
- [ ] Screenshots: Dining Philosophers output
- [ ] Report section: paging system design and comparison to real OS
- [ ] Report section: page fault and replacement analysis
- [ ] Report section: mutex/semaphore usage explained
- [ ] Report section: synchronization problem solution described
- [ ] Report section: challenges and improvements discussed

---

## Deliverable 4: Integration and Security

### Piping
- [ ] Input lines with `|` detected and split into segments
- [ ] Each segment spawned as a subprocess with `stdout=PIPE`
- [ ] Each process's `stdin` connected to previous process's `stdout`
- [ ] File descriptors closed after use (no fd leaks)
- [ ] Arbitrary chain length supported (`cmd1 | cmd2 | cmd3 | ...`)
- [ ] Piping works with built-in commands where applicable

### User Authentication
- [ ] Login prompt shown on shell startup
- [ ] Passwords stored as SHA-256(salt + password), never plaintext
- [ ] Timing-safe comparison used (`hmac.compare_digest`)
- [ ] Maximum 3 login attempts before session rejected
- [ ] `whoami` prints current username and role
- [ ] `passwd` allows user to change own password

### Role-Based Access Control
- [ ] Two roles defined: `admin` and `user`
- [ ] Admin has full access to all commands and files
- [ ] Standard user restricted to read-only on system files
- [ ] Standard user has read/write/execute in their home directory only
- [ ] `useradd <user>` is admin-only
- [ ] `chmod <file> <perm>` is admin-only

### File Permissions
- [ ] Permission table loaded from `data/permissions.json`
- [ ] Every file-accessing command checks permissions before executing
- [ ] `Permission denied` message shown on access violation
- [ ] Permissions persist across shell sessions (saved to JSON)

### Full Integration
- [ ] All modules imported and wired together in `main.py`
- [ ] Security check applied before every command execution
- [ ] Scheduler, memory manager, and sync tools accessible from the main REPL
- [ ] Piping works alongside existing job control and security checks
- [ ] No regressions from previous deliverables

### Report
- [ ] Complete integrated source code submitted
- [ ] Screenshots: piping with 2+ commands chained
- [ ] Screenshots: login with admin and standard user accounts
- [ ] Screenshots: file permission enforcement in action
- [ ] Report section: integration overview covering all deliverable components
- [ ] Report section: piping implementation explained
- [ ] Report section: authentication and permission system described
- [ ] Report section: challenges and improvements discussed

---

## General Quality Checklist

- [ ] All commands handle missing or incorrect arguments gracefully
- [ ] Error messages follow format: `shell: <command>: <reason>`
- [ ] No hardcoded passwords or sensitive data in source files
- [ ] Code is modular — each OS concept in its own module
- [ ] All modules have been manually tested end-to-end
- [ ] Unit tests written for core logic (scheduler, memory, security)
- [ ] `README.md` is complete and accurate
- [ ] All four deliverable report sections are written
