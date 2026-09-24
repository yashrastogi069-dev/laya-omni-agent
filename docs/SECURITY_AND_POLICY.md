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


