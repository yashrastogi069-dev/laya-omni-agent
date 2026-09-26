# SECURITY_AND_POLICY.md — Action Policy, Autonomy & Safety Boundaries

## 1. Prime Directive of Agent Safety
A high model confidence score must **NEVER** bypass deterministic action policy.
Even if a model reports 99.9% confidence that a destructive file deletion or process kill is desired, policy rules and confirmation gates remain absolute.

---

## 2. Action Classification

Every capability in the system belongs to an explicit `ActionClass`:

| Action Class | Definition | Default Permission | Confirmation Gate |
| :--- | :--- | :--- | :--- |
| `READ_ONLY` | Inspects data without state modification (diagnostics, search, reading files). | Auto-permitted | Never |
| `LOCAL_CREATE` | Creates new files or writes to sandbox paths. | Auto-permitted | No (unless overwriting) |
| `LOCAL_UPDATE` | Modifies existing local workspace files. | Permitted in workspace | No |
| `LOCAL_DELETE` | Removes local files or directories. | Restricted | **Mandatory** |
| `EXTERNAL_CREATE` | Registers remote resources or posts non-sensitive data. | Contextual | No |
| `EXTERNAL_UPDATE` | Modifies remote entities or state. | Restricted | Yes |
| `EXTERNAL_SEND` | Sends emails, messages, or external dispatches. | Restricted | **Mandatory** |
| `EXTERNAL_DELETE` | Destroys remote cloud resources or databases. | Forbidden by default | **Mandatory Dual-Check** |
| `SYSTEM_ACTION` | OS-level actions: terminating processes, rebooting, modifying system configs. | Restricted | **Mandatory** |
| `SECURITY_SENSITIVE` | Reading or writing credentials, tokens, SSH keys, certificates. | Restricted | **Mandatory** |
| `FINANCIAL` | Any operation incurring charges, purchasing, or transferring money. | Forbidden by default | **Mandatory** |

---

## 3. Autonomy Profiles

The runtime operates under one of five explicit autonomy profiles:

1. **`ADVISOR`**:
   - `READ_ONLY` actions only.
   - Any side effect requires explicit user authorization.
2. **`SAFE_ASSISTANT` (Default)**:
   - `READ_ONLY`, `LOCAL_CREATE`, and non-destructive `LOCAL_UPDATE` are permitted automatically.
   - Any deletion, external communication, or system action requires user confirmation.
3. **`LOCAL_OPERATOR`**:
   - Local operations (including PowerShell within workspace and process management) are permitted.
   - External dispatches and destructive deletions require confirmation.
4. **`TRUSTED_OPERATOR`**:
   - All standard operations permitted; `SECURITY_SENSITIVE` and `FINANCIAL` remain gated.
5. **`WORKFLOW_AUTHORIZED`**:
   - Scoped cryptographic token authorizing specific automated tasks with defined resource boundaries.

---

## 4. Prompt Injection Defenses & Data Boundary

All external inputs are classified strictly as **UNTRUSTED DATA**:
- Web scrape contents
- Tavily search results
- File contents read from disk
- Process / command standard outputs
- Incoming MCP / API responses

### Invariant Rules:
1. External content MUST NEVER be concatenated directly into system instructions without sanitization and XML/markdown framing:
   ```xml
   <untrusted_external_data origin="https://example.com/article" hash="a3f7...">
   &lt;escaped content&gt;
   </untrusted_external_data>
   ```
2. **Deterministic Multi-Layer Sanitization Pipeline (`omni_engine/research/sanitizer.py`)**:
   - **NFKC Unicode Normalization**: Neutralizes homoglyph evasion and compatibility spoofing.
   - **Zero-Width Character Stripping**: Removes invisible zero-width spaces (`\u200b-\u200f`, `\ufeff`, `\u202a-\u202e`).
   - **Control Code Stripping**: Eliminates non-printable ASCII control codes (`\x00-\x1f` except standard whitespace).
   - **Overt Override Neutralization**: Replaces prompt injection patterns (`ignore all previous instructions`, `you are now in developer mode`) with `[FILTERED_INSTRUCTION_OVERRIDE]`.
   - **Rigid XML Escaping**: Converts `<`, `>`, `&`, `"` to prevent synthetic tag termination attacks.
3. System instructions explicitly forbid the model from executing commands contained within `<untrusted_external_data>` blocks.
4. The deterministic runtime, not the model, enforces whether a capability call is valid and permitted.

---

## 5. Financial Safety & Browser Gating (REQ-B4)

Financial actions (`ActionClass.FINANCIAL`, `confirm_purchase`, or interactions with targets matching financial keywords / URLs like `pay`, `checkout`, `buy`, `card`, `cvv`, `billing`) represent an absolute safety boundary:
1. **Inviolable Stage 3 Policy Gating**: In `PolicyEngine`, any action classified as `FINANCIAL` or having sensitive targets tagged `financial:*` strictly requires explicit user confirmation (`user_confirmed=True`) under all autonomy tiers below `WORKFLOW_AUTHORIZED`. Even `TRUSTED_OPERATOR` cannot bypass this confirmation gate.
2. **Intrinsic Driver Gate**: `BrowserDriver` implements an intrinsic secondary check scanning the target element attributes (`is_financial`), current URL, action type, and inner text. If a financial action is dispatched without explicit confirmation, execution is halted immediately before any DOM event is dispatched.

---

## 6. Automation & n8n Safety Invariants (Phase R4)

Automated workflow execution introduces risks of Remote Code Execution (RCE), secret leakage, and runaway execution loops:
1. **The Gate Triad Invariant**:
   - Workflows created or updated via LAYA are strictly set to draft mode (`active=False`).
   - Promotion to `active=True` via `activate_workflow` strictly requires:
     1. Structural DAG validation (`is_valid=True`, cycle-free, valid triggers).
     2. Evidence-based physical receipt verifying successful execution (`status="success"`) for the exact current `workflow_hash`.
     3. Zero plaintext secrets detected across all node parameters.
   - Any parameter or connection mutation alters `workflow_hash` and immediately invalidates cached execution receipts, forcing re-testing.
2. **Zero Plaintext Secrets & Scrubber Enforcement**:
   - Inline API keys, tokens, and passwords in workflow payloads or headers are strictly prohibited. Credentials must be referenced by vault ID (`credential_id`).
   - `SecretScrubber` sanitizes headers, payload dictionaries, and node parameters against OpenAI, GitHub, AWS, Bearer/Basic, n8n API keys, private keys, and generic tokens, while preserving legitimate n8n `$json.*` and `={{ ... }}` expressions.
3. **RCE Defense in PolicyEngine**:
   - Nodes capable of executing shell commands or arbitrary code (`executeCommand`, `code`, `ssh`) are flagged as sensitive targets, escalating blast radius to `LOCAL_SYSTEM` or `SECURITY_CRITICAL` and composite risk to >= 0.70.
   - In Stage 0, Rule-0 embedded command scanning inspects `executeCommand` parameters to unconditionally deny forbidden destructive operations (`git reset --hard`, destructive drive wipes), strictly ignoring human confirmation.

---

## 7. Supervised Developer Agent & Code Safety Invariants (Phase R5)

Autonomous coding and subagent orchestration introduce severe risks of infinite thrashing loops, workspace boundary escape, test suite tampering, process tree zombies, and catastrophic repository wiping:
1. **Inviolable Safe Reversion (Rule-0 Compliance)**:
   - Autonomous coding agents must **NEVER** execute destructive git commands (`git reset --hard`, `git clean -fd`, `git push -f`).
   - All rollbacks in `WorkspaceConfiner.safe_revert()` operate on a granular, file-by-file basis: tracked files are restored individually via `git checkout -- <rel_path>`, and untracked files are unlinked individually via `os.remove()` only after verifying containment within repository boundaries.
   - Uncommitted user files outside the task scope are completely preserved.
2. **Subprocess Process-Tree Isolation & Zombie Defense**:
   - Test execution on Windows spawns under `CREATE_NEW_PROCESS_GROUP` via `DeterministicSubprocessRunner`.
   - Standard streams are drained via `communicate(timeout=...)` to prevent pipe deadlocks.
   - On timeout or process error, the entire process hierarchy is terminated using `taskkill /F /T /PID <pid>`, preventing hung processes or orphaned descendants from locking repository files.
   - Captured stdout/stderr is strictly truncated at 50,000 characters to prevent host memory exhaustion.
3. **Git Workspace Confinement & Path Traversal Immunity**:
   - `WorkspaceConfiner` verifies the repository root contains `.git` and blocks protected OS roots (`is_protected_path`).
   - All target files and operations are validated using dual containment checks (`pathlib.Path.is_relative_to` and `os.path.commonpath`), completely blocking traversal escapes (`..`, symlinks, junctions, or absolute external paths).
4. **Anti-Tampering on Test Suites**:
   - Modification to test suites (`test_*.py`, `*_test.py`, `tests/`, `test/`) is strictly prohibited by default (`allow_test_edits=False`).
   - Any attempt to modify test files raises an immediate permission exception and triggers automated rollback (`ConvergenceStatus.TEST_TAMPERING_DETECTED`), preventing agents from passing tasks by deleting or weakening tests.
5. **Deterministic Pre-Test AST Syntax Gate**:
   - All modified Python files are parsed using `ast.parse()` prior to test execution.
   - Syntax errors short-circuit immediately with line/column diagnostic receipts without invoking subprocess test commands.
6. **Rule-0 Embedded Command Defense**:
   - `PolicyEngine` Stage 0 scans both `task_prompt` and `test_commands` lists using `scan_embedded_commands()`.
   - Forbidden commands (`git reset --hard`, `git clean -fd`, `Remove-Item C:\`, drive formatting) are unconditionally denied (`is_hard_invariant=True`), completely unyielding to `user_confirmed=True`.

---

## 8. Plan Tamper Firewall & Execution Durability Gates (L14.2)

1. **Deterministic Plan Tamper Firewall**:
   - When a DAG plan is attached to a Quest, a canonical SHA-256 hash is computed via `Plan.compute_hash()` (sorting step IDs, sorting dependencies, normalizing timeouts and floats, sorting JSON argument keys) and recorded in `quest.metadata["plan_hash"]` along with `plan_provenance`.
   - Before executing the first step, `DeterministicDAGExecutor` reconstructs the plan from SQLite, recomputes the SHA-256 hash, and compares it against `quest.metadata["plan_hash"]`.
   - If any step, dependency, or argument was tampered with in SQLite, the engine immediately halts with `ExecutionFirewallError`, transition the quest to `FAILED`, and dispatches **zero** capabilities.
2. **Database-Level CAS Concurrency & Attempt Uniqueness**:
   - Mutation attempt leases are guarded at the database level via conditional CAS `UPDATE operations SET state = 'in_progress', current_attempt = current_attempt + 1 ... WHERE state IN ('pending', 'failed') AND current_attempt = ? AND current_attempt < max_attempts`, checking `cur.rowcount == 1`.
   - Enforced by a SQLite schema-level constraint: `UNIQUE(operation_id, attempt_number)`.
3. **Truthful Mutation Timeout Quarantine (`UNKNOWN_COMMIT`)**:
   - When a mutation capability times out after dispatch or experiences network uncertainty, its real-world outcome is unknown.
   - The attempt is marked `AttemptState.UNCERTAIN`, the operation is quarantined in `MutationState.UNKNOWN_COMMIT`, and the Quest is paused in `QuestStatus.PAUSED_FOR_RECONCILIATION`.
   - Automated blind retries are strictly blocked until physical evidence confirms remote state.
4. **Append-Only Reconciliation Audit Trail**:
   - All manual or evidence-based reconciliations are recorded in an append-only relational table `operation_reconciliations` capturing `reconciliation_id`, `operation_id`, `prior_state`, `reconciled_state`, `evidence`, `note`, `timestamp`, and `actor`.
5. **Transactional Fault Rollback (D1–D6)**:
   - Multi-statement mutations in `QuestStore` and `OperationStore` are wrapped in explicit database transactions. Fault injection during write operations triggers `conn.rollback()`, ensuring entity updates and audit events/attempts commit or roll back together, leaving zero orphaned rows on cold reopen.



