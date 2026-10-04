"""
omni_engine.verification.engine
===============================
Objective Completion Engine coordinating requirement-level verification,
negative constraint audits, physical evidence evaluation, and Quest lifecycle
closure (Checkpoint L15).

Invariants:
1. Physical Evidence Priority (Invariant 6): Physical outcome checks always outrank
   structured receipts and model prose.
2. Inviolable Rule: A semantic model MUST NOT override a deterministic physical failure.
3. Negative Constraint Verification: Explicit negative constraints ('do not modify workflows')
   are audited against the actual execution and mutation history.
4. Cryptographic Provenance: Computes and stores canonical SHA-256 evidence_hash.
"""

import time
import uuid
import re
from typing import Any, Dict, List, Optional, Union

from omni_engine.contracts.objective import ObjectiveSpec, RequirementItem
from omni_engine.contracts.quest import Quest, QuestStep, QuestStatus
from omni_engine.contracts.verification import (
    ConstraintVerification,
    ConstraintVerificationStatus,
    ObjectiveVerificationResult,
    RequirementVerification,
    RequirementVerificationStatus,
)
from omni_engine.planning.decomposer import ObjectiveDecomposer
from .registry import VerificationRegistry
from .store import VerificationStore


class ObjectiveCompletionEngine:
    """Core engine evaluating physical evidence to prove objective completion."""

    def __init__(
        self,
        registry: Optional[VerificationRegistry] = None,
        store: Optional[VerificationStore] = None,
        quest_engine: Optional[Any] = None,
    ):
        self.registry = registry if registry is not None else VerificationRegistry()
        self.store = store if store is not None else VerificationStore()
        self.quest_engine = quest_engine

    def verify_quest(
        self,
        quest: Union[str, Quest],
        objective_spec: Optional[ObjectiveSpec] = None,
        constraints: Optional[List[Dict[str, Any]]] = None,
    ) -> ObjectiveVerificationResult:
        """Evaluates whether the user's objective was physically and deterministically achieved."""
        # 1. Resolve Quest instance
        resolved_quest: Quest
        if isinstance(quest, str):
            if self.quest_engine is None:
                raise ValueError("quest_engine is required when resolving quest by ID string.")
            loaded = self.quest_engine.store.get_quest(quest)
            if not loaded:
                raise ValueError(f"Quest with ID '{quest}' not found.")
            resolved_quest = loaded
        else:
            resolved_quest = quest

        now = time.time()
        verification_id = f"verif_{uuid.uuid4().hex[:12]}"
        plan_id = resolved_quest.metadata.get("plan_id", "unknown_plan")
        goal_text = resolved_quest.goal

        # 2. Resolve ObjectiveSpec
        if objective_spec is None:
            if "objective_spec" in resolved_quest.metadata:
                try:
                    objective_spec = ObjectiveSpec.model_validate(resolved_quest.metadata["objective_spec"])
                except Exception:
                    objective_spec = ObjectiveDecomposer().decompose(goal_text)
            else:
                objective_spec = ObjectiveDecomposer().decompose(goal_text)

        # 3. Requirement Verification Loop
        requirement_results: List[RequirementVerification] = []
        steps_by_id = {s.step_id: s for s in resolved_quest.steps}

        for req in objective_spec.requirements:
            # Locate step for this requirement
            matching_step: Optional[QuestStep] = None
            if req.mapped_step_ids:
                for sid in req.mapped_step_ids:
                    if sid in steps_by_id:
                        matching_step = steps_by_id[sid]
                        break

            # Fallback: match by capability domain
            if matching_step is None:
                for s in resolved_quest.steps:
                    if s.capability_id.startswith(req.domain) or req.domain in s.capability_id:
                        matching_step = s
                        break

            # Extract receipt
            receipt: Optional[Dict[str, Any]] = None
            if matching_step is not None:
                if matching_step.execution_receipt:
                    receipt = matching_step.execution_receipt.get("tool_result", {}).get("receipt")
                    if not receipt:
                        receipt = matching_step.execution_receipt.get("tool_result", {}).get("data")
                    if not receipt:
                        receipt = matching_step.execution_receipt
                elif "receipt" in matching_step.metadata:
                    receipt = matching_step.metadata["receipt"]
                elif "tool_result" in matching_step.metadata:
                    tr = matching_step.metadata["tool_result"]
                    receipt = tr.get("receipt") or tr.get("data")

            # Route to verification registry
            req_verif = self.registry.verify_requirement(
                requirement=req,
                step=matching_step,
                receipt=receipt,
                context={"quest_id": resolved_quest.quest_id, "goal": goal_text},
            )
            requirement_results.append(req_verif)

        # 4. Negative Constraints Evaluation
        constraint_results: List[ConstraintVerification] = []
        resolved_constraints = list(constraints or [])
        if "constraints" in resolved_quest.metadata:
            resolved_constraints.extend(resolved_quest.metadata["constraints"])

        # Auto-detect negative constraints from prompt text
        lower_goal = goal_text.lower()
        if any(pat in lower_goal for pat in ("do not modify", "do not activate", "don't modify", "don't activate", "without modifying", "without activating")):
            resolved_constraints.append({
                "constraint_id": "C_NO_WORKFLOW_MUTATION",
                "description": "Do not modify or activate any workflow",
                "forbidden_actions": ["n8n.activate_workflow", "n8n.create_workflow", "n8n.trigger_workflow"],
            })
        if any(pat in lower_goal for pat in ("do not delete", "don't delete", "without deleting")):
            resolved_constraints.append({
                "constraint_id": "C_NO_DELETE",
                "description": "Do not delete files or terminate processes",
                "forbidden_actions": ["kill_process", "desktop.close_window"],
            })

        audited_op_ids = [s.step_id for s in resolved_quest.steps]

        for c_def in resolved_constraints:
            cid = c_def.get("constraint_id", f"C_{uuid.uuid4().hex[:6]}")
            cdesc = c_def.get("description", "Negative operational constraint")
            forbidden = c_def.get("forbidden_actions", [])

            violated = False
            violating_step = None

            for s in resolved_quest.steps:
                if s.capability_id in forbidden:
                    violated = True
                    violating_step = s.capability_id
                    break

            c_verif = ConstraintVerification(
                constraint_id=cid,
                description=cdesc,
                status=ConstraintVerificationStatus.VIOLATED if violated else ConstraintVerificationStatus.SATISFIED,
                violation_details=f"Forbidden action '{violating_step}' executed." if violated else None,
                checked_operations=audited_op_ids,
                timestamp=now,
            )
            constraint_results.append(c_verif)

        # 5. Aggregate Completion Decision
        mandatory_reqs = [r for r in requirement_results if r.mandatory]
        all_mandatory_verified = all(r.status == RequirementVerificationStatus.VERIFIED_SUCCESS for r in mandatory_reqs)
        no_constraints_violated = all(c.status == ConstraintVerificationStatus.SATISFIED for c in constraint_results)

        unresolved = [r.requirement_id for r in mandatory_reqs if r.status != RequirementVerificationStatus.VERIFIED_SUCCESS]
        violated_cids = [c.constraint_id for c in constraint_results if c.status == ConstraintVerificationStatus.VIOLATED]

        verified_complete = all_mandatory_verified and no_constraints_violated
        verified_failure = bool(violated_cids) or any(r.status == RequirementVerificationStatus.VERIFIED_FAILURE for r in mandatory_reqs)
        verified_partial = (not verified_complete) and any(r.status == RequirementVerificationStatus.VERIFIED_SUCCESS for r in mandatory_reqs)

        evidence_hash = ObjectiveVerificationResult.compute_evidence_hash(
            quest_id=resolved_quest.quest_id,
            plan_id=plan_id,
            requirement_results=requirement_results,
            constraint_results=constraint_results,
        )

        result = ObjectiveVerificationResult(
            verification_id=verification_id,
            quest_id=resolved_quest.quest_id,
            plan_id=plan_id,
            objective_text=goal_text,
            requirement_results=requirement_results,
            constraint_results=constraint_results,
            verified_complete=verified_complete,
            verified_partial=verified_partial,
            verified_failure=verified_failure,
            unresolved_requirements=unresolved,
            violated_constraints=violated_cids,
            evidence_hash=evidence_hash,
            verifier_version="1.0.0",
            provenance={
                "quest_id": resolved_quest.quest_id,
                "plan_id": plan_id,
                "total_requirements": len(requirement_results),
                "total_constraints": len(constraint_results),
            },
            timestamp=now,
        )

        # 6. Durable Persistence
        self.store.record_verification(result)

        # 7. Quest State Machine Lifecycle Integration
        if self.quest_engine is not None and resolved_quest.status == QuestStatus.AWAITING_VERIFICATION:
            if verified_complete:
                # Invariant 6: Transition to COMPLETED with verified physical proof
                transitioned = self.quest_engine.transition_quest(
                    resolved_quest.quest_id,
                    QuestStatus.COMPLETED,
                    reason="Objective verified physically and deterministically complete",
                    payload={"verification_id": verification_id, "evidence_hash": evidence_hash},
                )
                updated_meta = {
                    **transitioned.metadata,
                    "verification_id": verification_id,
                    "evidence_hash": evidence_hash,
                    "verified_at": now,
                }
                self.quest_engine.store.update_quest(transitioned.model_copy(update={"metadata": updated_meta}))
            elif verified_failure and (violated_cids or any(not r.repairable for r in requirement_results if r.status == RequirementVerificationStatus.VERIFIED_FAILURE)):
                # Hard / unrecoverable failure or constraint breach -> FAILED
                transitioned = self.quest_engine.transition_quest(
                    resolved_quest.quest_id,
                    QuestStatus.FAILED,
                    reason="Objective verification failed unrecoverably or constraint violated",
                    payload={"verification_id": verification_id, "evidence_hash": evidence_hash},
                )
                updated_meta = {
                    **transitioned.metadata,
                    "verification_id": verification_id,
                    "evidence_hash": evidence_hash,
                    "unresolved_requirements": unresolved,
                    "violated_constraints": violated_cids,
                }
                self.quest_engine.store.update_quest(transitioned.model_copy(update={"metadata": updated_meta}))
            else:
                # Incomplete or repairable gap: remain in AWAITING_VERIFICATION (ready for L16 replanner)
                updated_quest = resolved_quest.model_copy(
                    update={
                        "metadata": {
                            **resolved_quest.metadata,
                            "verification_id": verification_id,
                            "evidence_hash": evidence_hash,
                            "unresolved_requirements": unresolved,
                            "repairable": True,
                        }
                    }
                )
                self.quest_engine.store.update_quest(updated_quest)

        return result
