# lessons.md — Durable Engineering Lessons

## Lesson 1: Documentation Drift Outpaces Reality
- **Observation**: The initial README claimed 23+ tools including detailed Playwright primitives (`browser_navigate`, `browser_click_element`, `browser_type_text`). In reality, only 2 monolithic browser functions existed.
- **Principle**: Code and automated test assertions are the only verifiable truth. Documentation must be generated or verified against running tests, never written aspirational-first without immediate implementation.

## Lesson 2: Invisible Failures in Fixed Slices
- **Observation**: In `system1.py`, `list(tool_catalog.items())[:12]` was used to construct criteria. This silently severed 11 out of 23 tools from ever being chosen by the system.
- **Principle**: Never use magic hard-coded slices on dynamic registries. When limits are necessary, implement hierarchical grouping (e.g., Domain → Skill → Capability) with explicit logging and fail-open fallbacks.

## Lesson 3: The "Prompt-as-Argument" Fallacy
- **Observation**: `AutonomousPlanner` called `tool_func(mission_prompt)`, passing user text like "read the file README.md" directly to `tool_file_read(filepath)`. The tool attempted to open a file with the literal string name, failing 100% of the time.
- **Principle**: Natural language is NOT an argument. An explicit typed argument resolution step (regex, structured entity extraction, or schema-guided model generation) is mandatory between user intent and tool execution.

## Lesson 4: Execution Count ≠ True Learning
- **Observation**: `OmniMemory` marked a tool as "successful" simply because `tool_func()` returned without an unhandled Python exception. A tool that returned "File not found" or "Query returned 0 rows" was counted as a success.
- **Principle**: Memory must log verified outcome status (`success: bool`, `exit_code: int`, `receipt: dict`), not raw invocations.

## Lesson 5: Automated Tests Are Essential Grounding
- **Observation**: Prior to Checkpoint L0, zero automated test assertions (`assert`) existed in the codebase. As a result, a blatant `NameError: name 're' is not defined` in `tool_safe_math` sat undetected in production.
- **Principle**: Every single tool and decision layer must have at least one automated unit test executed by CI/test runners.

## Lesson 6: Token Blacklisting Is Insufficient for Safe Evaluation
- **Observation**: Blacklisting strings like `import` and `open` in `eval()` or AST does not protect against computational exhaustion attacks like `9**9**9**9`, which will lock the Python GIL and freeze the agent process.
- **Principle**: Sandboxed execution must use an explicit AST NodeVisitor whitelist that only allows verified operations, enforces numeric bounds on exponents, and pairs with execution timeouts.

## Lesson 7: Hierarchical Two-Level Locking Prevents Swap Races
- **Observation**: Separating model lifecycle synchronization from inference concurrency naively can cause deadlocks if an inference thread triggers a model swap while holding an inference semaphore. In C++ PyTorch runtimes, mutating loaded weights during active forward passes causes access violation segfaults.
- **Principle**: Model swaps and evictions must acquire the Level 1 lock (`_MODEL_LIFECYCLE_LOCK`) and exclusively drain all Level 2 inference permits before modifying model state. Threads holding inference permits must never acquire the lifecycle lock.

## Lesson 8: Windows RAM Fluctuations Mandate Debounced Eviction
- **Observation**: Windows 10 available RAM fluctuates by 200–800 MB due to OS file caching and background services. Evicting a 1.64 GB ModernBERT model on an instantaneous dip below a headroom threshold causes catastrophic eviction thrashing, where each request triggers a 47–69 second cold start.
- **Principle**: RAM eviction must require multiple consecutive threshold breaches over time (e.g., 3 breaches over >= 5 seconds) and only execute when the system is completely idle (zero active inferences).
