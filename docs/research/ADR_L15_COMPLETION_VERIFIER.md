# ADR-020: Evidence-Based Completion Verifier, Deterministic Verifier Registry & Requirement-Level Objective Verification (L15)

- **Date**: 2026-10-04
- **Status**: ACCEPTED
- **Context**: 
  In the LAYA Omni Agent architecture, Checkpoint L14.3 successfully unified pre-execution objective decomposition, hierarchical routing, skill and template augmentation, semantic validation, policy enforcement, operation ledger deduplication, and deterministic DAG execution. When execution traversal completes, Kahn's algorithm transitions the Quest from `RUNNING` to `QuestStatus.AWAITING_VERIFICATION` (Invariant 6).
  However, tool execution success does NOT equate to objective success. A `ToolResult.outcome == SUCCESS` merely indicates that a Python function completed without throwing an unhandled exception or returning an intercepted error string. It does not prove that:
  1. The requested real-world artifact actually exists on the filesystem.
  2. The target service or process changed state in the intended manner.
  3. All decomposed mandatory requirements of the user's objective were satisfied.
  4. Explicit negative constraints (e.g. "do not modify workflows", "do not delete files") were strictly honored.
  5. The generated report or answer truthfully reflects physical evidence without hallucination.

- **Decision**:
  Implement Checkpoint L15 (Evidence-Based Completion Verifier & Completion Engine) adhering to the following architectural design:

  1. **Strict Evidence Hierarchy (Physical Evidence Priority)**:
     - Tier 1: Direct Physical State Probe (filesystem existence, file size, content hash, process table, TCP port probe).
     - Tier 2: Structured Execution Receipt (`ToolResult.receipt`, `ExecutionReceipt`, `N8nExecutionReceipt`, `BrowserDriver` physical receipts).
     - Tier 3: Deterministic Derived Validation (AST syntax verification, cryptographic citation matching against `EvidenceLedger`).
     - Tier 4: Bounded Semantic Judgment (System 1 / Generative classifier with strict schema) applied strictly to evaluate subjective quality ONLY after Tier 1–3 pass.
     - Tier 5: Prose Output (Presentation only; permanently prohibited from being used as evidence).
     - *Hard Invariant*: A semantic model MUST NEVER override a deterministic physical failure. If a file is missing on disk, the objective CANNOT be marked complete, regardless of model claims.

  2. **Strongly Typed Verification Contracts (`omni_engine/contracts/verification.py`)**:
     - `RequirementVerification`: Discrete verification record for each `RequirementItem` from `ObjectiveSpec`.
     - `ConstraintVerification`: Verification record for negative or operational constraints.
     - `ObjectiveVerificationResult`: Aggregate objective-level outcome with canonical cryptographic `evidence_hash`, listing `verified_complete`, `verified_partial`, `verified_failure`, `unresolved_requirements`, and `violated_constraints`.

  3. **Extensible Deterministic Verifier Registry (`VerificationRegistry`)**:
     - Decoupled family-specific verifiers:
       - `FileVerifier`: Verifies path existence, expected type, size bounds, content conditions, bytes written, SHA-256 content hash.
       - `ProcessVerifier`: Verifies process state (running vs terminated), PID matching, and name validation.
       - `DesktopVerifier`: Verifies local service port connectivity (TCP/HTTP health) and window state.
       - `BrowserVerifier`: Verifies URL, screenshot artifact on disk, and DOM mutation receipts.
       - `CommandVerifier`: Verifies subprocess exit codes, zero test failures, and expected output text.
       - `GitVerifier`: Verifies repository branch, clean/dirty worktree status, and commit presence.
       - `N8nVerifier`: Verifies workflow existence, active/inactive flag, execution receipt status, and zero plaintext secrets.
       - `DataVerifier`: Verifies SQLite database table existence and row count conditions.
       - `ResearchVerifier`: Verifies evidence ledger existence, cryptographic citation resolution, and absence of `UNVERIFIED_CITATION` tags.

  4. **Requirement-Level & Negative Constraint Completion Engine (`ObjectiveCompletionEngine`)**:
     - Evaluates each mandatory requirement in `ObjectiveSpec.requirements`.
     - Maps step outputs, receipts, and target entities to registered verifiers.
     - Inspects Quest step execution history and ledger mutation history against negative constraints (e.g. detecting prohibited mutation attempts).
     - Computes canonical SHA-256 `evidence_hash`.

  5. **Durable Verification Persistence & Quest State Transitions**:
     - Appends verification records to SQLite table `quest_verifications` (`verification_id`, `quest_id`, `plan_id`, `verified_complete`, `evidence_hash`, `timestamp`).
     - Quest state transition from `AWAITING_VERIFICATION`:
       - If `verified_complete == True` → transitions to `QuestStatus.COMPLETED`, logs `QuestEventEnum.QUEST_COMPLETED`.
       - If `verified_complete == False` and unrecoverable/constraint violation → transitions to `QuestStatus.FAILED`, logs `QuestEventEnum.QUEST_FAILED`.
       - If incomplete/repairable → remains in `QuestStatus.AWAITING_VERIFICATION` (attaching verification report to metadata for L16 Replanner).

- **Consequences**:
  - Guarantees Invariant 6 (Evidence-Based Completion): No Quest can transition to `COMPLETED` without verified physical proof.
  - Eliminates false-success completions where tools report success but real-world state is unchanged.
  - Establishes a durable, restart-safe evidence receipt foundation for Checkpoint L16 (Controlled Replanner).
