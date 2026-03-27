# Deliverable 4 — Report

## 1. Integration Overview

<!-- Provide a detailed overview of how all components from previous
     deliverables were integrated into a single shell. Describe how
     the modules communicate and share state. -->

### Component Map
| Component | Module | Integrated In |
|-----------|--------|--------------|
| Process Management | `process_manager.py` | `main.py` dispatcher |
| Scheduling | `scheduler.py` | `main.py` dispatcher |
| Memory Management | `memory_manager.py` | `main.py` dispatcher |
| Synchronization | `synchronization.py` | `main.py` dispatcher |
| Piping | `pipe_handler.py` | `parser.py` → `main.py` |
| Security | `security.py` | Every command execution path |

## 2. Piping Implementation

<!-- Describe how piping is implemented. Explain how subprocess stdout
     is connected to the next process's stdin, how file descriptors are
     managed, and how the pipeline is flushed and cleaned up. -->

## 3. Security Mechanisms

### User Authentication
<!-- Describe the login flow. Explain how passwords are hashed and
     salted, how sessions are maintained, and how failed attempts are handled. -->

### File Permissions
<!-- Describe how the permission table works. Explain how access checks
     are performed before each file-accessing command and how violations
     are reported to the user. -->

### Role-Based Access Control
<!-- Describe the difference between admin and user roles and how each
     role's capabilities are enforced throughout the shell. -->

## 4. Challenges and Improvements

<!-- Discuss any challenges you encountered during integration and
     how you addressed them. Also discuss any improvements you would
     make given more time. -->
