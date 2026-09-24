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

## Lesson 9: Cryptographic Passage Hashing Defeats Citation Hallucination
- **Observation**: Generative models and heuristics frequently cite plausible-looking but non-existent sources (e.g. `[ev_1234567890]`) when synthesizing multi-page research digests.
- **Principle**: An immutable evidence ledger indexed by passage-level SHA-256 hashes must serve as the single source of truth. Post-synthesis citation verification must deterministically scan all citation tokens, verify ledger inclusion, and quarantine invalid references to `[UNVERIFIED_CITATION: <id>]`.

## Lesson 10: Explicit Depth Tuples in Crawl Queues Prevent Spider Traps
- **Observation**: When candidate URLs are placed in a flat list queue (`urls_to_crawl: List[str]`), shallow link expansion (depth <= 1) can accidentally traverse into depth 2 if child links are popped after seed URLs are exhausted.
- **Principle**: Crawl queues must track explicit `(url: str, depth: int)` tuples. Link extraction must strictly check `depth < max_crawl_depth` before appending child URLs with `depth + 1`.

## Lesson 11: Python Function Scope Local `import` Creates Shadow `UnboundLocalError`
- **Observation**: Placing `import re` inside a single conditional branch of a function (e.g. `if capability_id == "file_write": import re`) causes Python bytecode compilation to treat `re` as a local variable for the ENTIRE function scope. When any other branch executes `re.search()`, Python throws `UnboundLocalError` even though `re` is imported at the module level.
- **Principle**: Never place conditional or nested `import` statements inside functions when the module is already imported at module level. Standard library modules must strictly be imported at top level.

## Lesson 12: Dual-Key Addressing & Pre-Action Staleness Verification Defeats SPA Churn
- **Observation**: In modern Single Page Applications (React/Vue/Angular), DOM nodes are frequently destroyed and replaced during client-side state changes. Relying solely on a transient numeric index (`@1`) risks clicking the wrong target if an element moves or shifts between snapshot capture and action dispatch.
- **Principle**: Pair transient DOM indices (`@1..@N` stamped with `data-laya-idx`) with semantic fingerprints (tag, role, accessible text). Before executing physical input, verify node attachment and attribute consistency. If a mismatch is detected, halt execution immediately with a structured staleness error rather than firing blind clicks.

