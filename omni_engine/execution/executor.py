"""Deterministic DAG Executor for LAYA Autonomous V2 Runtime.

Coordinates multi-step DAG execution across persistent SQLite Quests,
Operation Ledger deduplication, Policy Engine gates, and real Capability engines.
Enforces Single Coordinator Dispatch, Mutation Barriers, and Invariant 6 (Checkpoint L14).
"""

import concurrent.futures
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from ..contracts.capability import IdempotencyClass, ToolResult
from ..contracts.enums import ActionClass, AutonomyProfile, ErrorCode, RetryPolicy
from ..contracts.execution import (
    ExecutionError,
    ExecutionFirewallError,
    MissingInputError,
    PolicyBlockedExecutionError,
    QuestAlreadyRunningError,
    QuestExecutionSummary,
    StepExecutionReceipt,
    UnresolvedArgumentError,
)
from ..contracts.operation import MutationState
from ..contracts.plan import Plan, PlanStep, PlanType
from ..contracts.policy import PolicyDecision, PolicyEffect
from ..contracts.quest import (
    Quest,
    QuestNotFoundError,
    QuestStatus,
    QuestStep,
    StepNotFoundError,
    StepStatus,
    TERMINAL_QUEST_STATES,
)
from ..capabilities.registry import CapabilityRegistry
from ..operations.ledger import OperationLedger
from ..planning.validator import DeterministicPlanValidator
from ..policy.engine import PolicyEngine
from ..quest.engine import QuestEngine
from .dynamic_resolver import DynamicResolver

logger = logging.getLogger(__name__)


class DeterministicDAGExecutor:
    """Orchestrates deterministic DAG plan execution with persistent state and safety guarantees."""

    def __init__(
        self,
        quest_engine: QuestEngine,
        capability_registry: CapabilityRegistry,
        policy_engine: PolicyEngine,
        operation_ledger: OperationLedger,
        plan_validator: Optional[DeterministicPlanValidator] = None,
        max_parallel_workers: int = 4,
    ):
        self.quest_engine = quest_engine
        self.capability_registry = capability_registry
        self.policy_engine = policy_engine
        self.operation_ledger = operation_ledger
        self.plan_validator = plan_validator or DeterministicPlanValidator(
            capability_registry=capability_registry,
            policy_engine=policy_engine,
        )
        self.max_parallel_workers = max(1, max_parallel_workers)

        # In-memory lease registry (BLK-5)
        self._active_leases: Set[str] = set()
        self._lease_lock = threading.Lock()

        # Strict mutation barrier lock (BLK-4)
        self._mutation_lock = threading.Lock()

    # =========================================================================
    # Public Execution Entry Points
    # =========================================================================

    def execute(
        self,
        quest_id: str,
        inputs: Optional[Dict[str, Any]] = None,
        plan: Optional[Plan] = None,
    ) -> QuestExecutionSummary:
        """Executes a multi-step Quest from its current planned or created state.
        
        Args:
            quest_id: Target quest identifier.
            inputs: Quest-level runtime inputs for dynamic $inputs.<key> resolution.
            plan: Optional explicit Plan to validate and attach if not yet planned.
            
        Returns:
            QuestExecutionSummary envelope.
            
        Raises:
            QuestNotFoundError: If quest does not exist.
            QuestAlreadyRunningError: If an execution lease is already active for this quest.
            ExecutionFirewallError: If plan validation fails.
        """
        self._acquire_lease(quest_id)
        try:
            return self._execute_internal(quest_id, inputs=inputs, plan=plan)
        finally:
            self._release_lease(quest_id)

    def resume(
        self,
        quest_id: str,
        user_confirmation: bool = False,
        user_inputs: Optional[Dict[str, Any]] = None,
    ) -> QuestExecutionSummary:
        """Resumes a paused Quest from SQLite persistence.
        
        Args:
            quest_id: Target quest identifier.
            user_confirmation: User confirmation response for confirmation pauses.
            user_inputs: Additional user input dictionary for input pauses.
            
        Returns:
            QuestExecutionSummary envelope.
            
        Raises:
            QuestNotFoundError: If quest does not exist.
            QuestAlreadyRunningError: If an execution lease is already active.
            ExecutionError: If quest is not in a resumable state.
        """
        self._acquire_lease(quest_id)
        try:
            return self._resume_internal(
                quest_id,
                user_confirmation=user_confirmation,
                user_inputs=user_inputs,
            )
        finally:
            self._release_lease(quest_id)

    def cancel(
        self,
        quest_id: str,
        reason: str = "Execution cancelled by user",
    ) -> QuestExecutionSummary:
        """Cancels a quest and transitions uncompleted steps to CANCELLED.
        
        Args:
            quest_id: Target quest identifier.
            reason: Cancellation reason or audit justification.
            
        Returns:
            QuestExecutionSummary envelope.
            
        Raises:
            QuestNotFoundError: If quest does not exist.
        """
        self._acquire_lease(quest_id)
        try:
            start_time = time.perf_counter()
            quest = self.quest_engine.get_quest(quest_id)
            if not quest:
                raise QuestNotFoundError(f"Quest '{quest_id}' not found.")

            initial_status = quest.status
            if quest.status in TERMINAL_QUEST_STATES:
                return QuestExecutionSummary(
                    quest_id=quest_id,
                    initial_status=initial_status,
                    final_status=quest.status,
                    total_steps=len(quest.steps),
                    completed_steps=sum(1 for s in quest.steps if s.status == StepStatus.COMPLETED),
                    failed_steps=sum(1 for s in quest.steps if s.status == StepStatus.FAILED),
                    error=f"Quest is already in terminal state '{quest.status.value}'",
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 3),
                )

            # Cancel all uncompleted steps
            cancelled_steps_count = 0
            for step in quest.steps:
                if step.status not in (
                    StepStatus.COMPLETED,
                    StepStatus.FAILED,
                    StepStatus.SKIPPED,
                    StepStatus.CANCELLED,
                ):
                    self.quest_engine.transition_step(
                        quest_id,
                        step.step_id,
                        StepStatus.CANCELLED,
                        error=f"Cancelled: {reason}",
                    )
                    cancelled_steps_count += 1

            # Transition quest to CANCELLED
            updated_quest = self.quest_engine.transition_quest(
                quest_id,
                QuestStatus.CANCELLED,
                reason=reason,
            )

            completed_count = sum(1 for s in updated_quest.steps if s.status == StepStatus.COMPLETED)
            failed_count = sum(1 for s in updated_quest.steps if s.status == StepStatus.FAILED)

            return QuestExecutionSummary(
                quest_id=quest_id,
                initial_status=initial_status,
                final_status=QuestStatus.CANCELLED,
                total_steps=len(updated_quest.steps),
                completed_steps=completed_count,
                failed_steps=failed_count,
                error=f"Quest cancelled: {reason}",
                latency_ms=round((time.perf_counter() - start_time) * 1000, 3),
            )
        finally:
            self._release_lease(quest_id)

    # =========================================================================
    # Internal Execution Engine
    # =========================================================================

    def _execute_internal(
        self,
        quest_id: str,
        inputs: Optional[Dict[str, Any]] = None,
        plan: Optional[Plan] = None,
    ) -> QuestExecutionSummary:
        start_time = time.perf_counter()
        quest = self.quest_engine.get_quest(quest_id)
        if not quest:
            raise QuestNotFoundError(f"Quest '{quest_id}' not found.")

        initial_status = quest.status

        # 1. Plan Verification Firewall (ADR-016 / Invariant 5)
        active_plan = plan or self._reconstruct_plan(quest)
        validation_report = self.plan_validator.validate(active_plan, autonomy_profile=quest.autonomy_profile)
        if not validation_report.is_valid:
            error_msg = f"Plan validation firewall rejected plan: {validation_report.errors}"
            self.quest_engine.transition_quest(
                quest_id,
                QuestStatus.FAILED,
                reason="Plan validation failed",
                payload={"errors": validation_report.errors},
            )
            raise ExecutionFirewallError(error_msg)

        # 2. Attach plan if in CREATED status
        if quest.status == QuestStatus.CREATED:
            from ..planning.engine import StructuredDAGPlanner
            planner = StructuredDAGPlanner(capability_registry=self.capability_registry)
            planner.attach_to_quest(self.quest_engine, active_plan)
            quest = self.quest_engine.get_quest(quest_id)

        # 3. Transition PLANNED -> RUNNING
        if quest.status == QuestStatus.PLANNED:
            quest = self.quest_engine.transition_quest(quest_id, QuestStatus.RUNNING, reason="Starting DAG execution")

        # 4. Coordinator Loop
        return self._run_coordinator_loop(quest_id, inputs or {}, start_time, initial_status)

    def _resume_internal(
        self,
        quest_id: str,
        user_confirmation: bool = False,
        user_inputs: Optional[Dict[str, Any]] = None,
    ) -> QuestExecutionSummary:
        start_time = time.perf_counter()
        quest = self.quest_engine.get_quest(quest_id)
        if not quest:
            raise QuestNotFoundError(f"Quest '{quest_id}' not found.")

        initial_status = quest.status
        if quest.status not in (
            QuestStatus.PAUSED_FOR_CONFIRMATION,
            QuestStatus.PAUSED_FOR_INPUT,
            QuestStatus.PAUSED_FOR_RECONCILIATION,
        ):
            raise ExecutionError(f"Cannot resume quest '{quest_id}' in non-paused status '{quest.status.value}'.")

        # Handle confirmation response
        confirmed_step_id: Optional[str] = None
        if quest.status == QuestStatus.PAUSED_FOR_CONFIRMATION:
            if not user_confirmation:
                # User explicitly rejected confirmation -> fail quest
                self.quest_engine.transition_quest(
                    quest_id,
                    QuestStatus.FAILED,
                    reason="User rejected action confirmation",
                )
                return QuestExecutionSummary(
                    quest_id=quest_id,
                    initial_status=initial_status,
                    final_status=QuestStatus.FAILED,
                    total_steps=len(quest.steps),
                    completed_steps=sum(1 for s in quest.steps if s.status == StepStatus.COMPLETED),
                    failed_steps=1,
                    error="Execution rejected by user confirmation gate",
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 3),
                )
            # Find the paused step to grant confirmation
            for step in quest.steps:
                if step.status == StepStatus.PAUSED:
                    confirmed_step_id = step.step_id
                    break

        elif quest.status == QuestStatus.PAUSED_FOR_RECONCILIATION:
            for step in quest.steps:
                if step.status == StepStatus.AWAITING_RECONCILIATION:
                    op_id = f"op_{quest_id}_{step.step_id}_{step.capability_id}"
                    op = self.operation_ledger.get_operation(op_id)
                    if op and op.state == MutationState.COMMITTED:
                        self.quest_engine.transition_step(
                            quest_id,
                            step.step_id,
                            StepStatus.COMPLETED,
                            execution_receipt=op.execution_receipt or {"status": "reconciled_committed"},
                        )
                    elif op and op.state == MutationState.FAILED:
                        if op.current_attempt < op.max_attempts:
                            self.quest_engine.transition_step(
                                quest_id,
                                step.step_id,
                                StepStatus.READY,
                            )
                        else:
                            self.quest_engine.transition_step(
                                quest_id,
                                step.step_id,
                                StepStatus.FAILED,
                                error=op.error or "Operation failed and exhausted attempts",
                            )
                    else:
                        raise ExecutionError(
                            f"Cannot resume quest '{quest_id}': step '{step.step_id}' "
                            f"is still in UNKNOWN_COMMIT and not reconciled."
                        )
            # Refresh quest model after step status updates
            quest = self.quest_engine.get_quest(quest_id)

        # Merge user inputs if resuming from input pause
        merged_inputs = dict(quest.metadata.get("inputs", {}))
        if user_inputs:
            merged_inputs.update(user_inputs)
        quest.metadata["inputs"] = merged_inputs
        self.quest_engine.store.update_quest(quest)

        # Transition PAUSED -> RUNNING
        quest = self.quest_engine.transition_quest(
            quest_id,
            QuestStatus.RUNNING,
            reason="Resuming execution after reconciliation or user response",
        )

        return self._run_coordinator_loop(
            quest_id,
            merged_inputs,
            start_time,
            initial_status,
            confirmed_step_id=confirmed_step_id,
        )

    # =========================================================================
    # Single Coordinator Dispatcher Loop (BLK-1)
    # =========================================================================

    def _run_coordinator_loop(
        self,
        quest_id: str,
        inputs: Dict[str, Any],
        start_time: float,
        initial_status: QuestStatus,
        confirmed_step_id: Optional[str] = None,
    ) -> QuestExecutionSummary:
        """Executes the Kahn-style DAG traversal on a single coordinator thread."""
        quest = self.quest_engine.get_quest(quest_id)
        if not quest:
            raise QuestNotFoundError(f"Quest '{quest_id}' not found.")

        # Build effective inputs from metadata and parameters (AUDIT-12)
        effective_inputs = dict(quest.metadata.get("inputs", {}))
        if inputs:
            effective_inputs.update(inputs)
        if effective_inputs != quest.metadata.get("inputs"):
            quest.metadata["inputs"] = effective_inputs
            self.quest_engine.store.update_quest(quest)

        # Plan timeout budget (AUDIT-15)
        provenance = quest.metadata.get("plan_provenance", {})
        timeout_budget_s = (
            provenance.get("timeout_budget_s")
            or quest.metadata.get("timeout_budget_s")
            or 3600.0
        )

        # Build in-memory state tracking
        step_map: Dict[str, QuestStep] = {s.step_id: s for s in quest.steps}
        completed_steps: Dict[str, QuestStep] = {}
        failed_steps: Dict[str, QuestStep] = {}

        # 1. Crash recovery / State reconciliation (BLK-5 / AUDIT-06 / AUDIT-07)
        paused_for_reconciliation_step: Optional[QuestStep] = None
        for s in quest.steps:
            if s.status == StepStatus.COMPLETED:
                completed_steps[s.step_id] = s
            elif s.status == StepStatus.FAILED:
                failed_steps[s.step_id] = s
            elif s.status == StepStatus.AWAITING_RECONCILIATION:
                paused_for_reconciliation_step = s
            elif s.status == StepStatus.RUNNING:
                # Recovering from an interrupted run
                if s.action_class == ActionClass.READ_ONLY:
                    recovered = self.quest_engine.transition_step(quest_id, s.step_id, StepStatus.READY)
                    step_map[s.step_id] = recovered
                else:
                    # Check operation ledger
                    op_id = f"op_{quest_id}_{s.step_id}_{s.capability_id}"
                    op = self.operation_ledger.get_operation(op_id)
                    if op and op.state == MutationState.IN_PROGRESS:
                        self.operation_ledger.fail_operation(op_id, error="Interrupted by system crash", is_uncertain=True)
                    recovered = self.quest_engine.transition_step(
                        quest_id,
                        s.step_id,
                        StepStatus.AWAITING_RECONCILIATION,
                        error="Mutation interrupted by system crash; requires evidence reconciliation",
                    )
                    step_map[s.step_id] = recovered
                    paused_for_reconciliation_step = recovered

        if paused_for_reconciliation_step:
            self.quest_engine.transition_quest(
                quest_id,
                QuestStatus.PAUSED_FOR_RECONCILIATION,
                reason=f"Step '{paused_for_reconciliation_step.step_id}' requires evidence reconciliation",
            )
            return self._build_summary(
                quest_id,
                initial_status,
                QuestStatus.PAUSED_FOR_RECONCILIATION,
                len(step_map),
                completed_steps,
                failed_steps,
                start_time,
                paused_step_id=paused_for_reconciliation_step.step_id,
                error="Mutation interrupted by system crash; awaiting reconciliation",
            )

        # Worker pool for concurrent read-only steps
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel_workers) as executor:
            in_flight: Dict[concurrent.futures.Future, str] = {}

            while True:
                # AUDIT-15: Check plan timeout budget at top of coordinator loop
                elapsed = time.perf_counter() - start_time
                if elapsed > timeout_budget_s:
                    for fut in in_flight:
                        fut.cancel()
                    timeout_msg = f"Plan timeout budget exceeded: {elapsed:.2f}s > {timeout_budget_s:.2f}s"
                    self.quest_engine.transition_quest(
                        quest_id,
                        QuestStatus.FAILED,
                        reason=timeout_msg,
                    )
                    return self._build_summary(
                        quest_id,
                        initial_status,
                        QuestStatus.FAILED,
                        len(step_map),
                        completed_steps,
                        failed_steps,
                        start_time,
                        error=timeout_msg,
                    )

                # If any step is awaiting reconciliation, pause quest immediately
                reconcile_step = next((s for s in step_map.values() if s.status == StepStatus.AWAITING_RECONCILIATION), None)
                if reconcile_step:
                    self.quest_engine.transition_quest(
                        quest_id,
                        QuestStatus.PAUSED_FOR_RECONCILIATION,
                        reason=f"Step '{reconcile_step.step_id}' entered UNKNOWN_COMMIT: {reconcile_step.error}",
                    )
                    return self._build_summary(
                        quest_id,
                        initial_status,
                        QuestStatus.PAUSED_FOR_RECONCILIATION,
                        len(step_map),
                        completed_steps,
                        failed_steps,
                        start_time,
                        paused_step_id=reconcile_step.step_id,
                        error=reconcile_step.error,
                    )

                # If any step previously failed, halt quest
                if failed_steps:
                    first_failure = next(iter(failed_steps.values()))
                    self.quest_engine.transition_quest(
                        quest_id,
                        QuestStatus.FAILED,
                        reason=f"Step '{first_failure.step_id}' failed: {first_failure.error}",
                    )
                    return self._build_summary(
                        quest_id,
                        initial_status,
                        QuestStatus.FAILED,
                        len(step_map),
                        completed_steps,
                        failed_steps,
                        start_time,
                        error=first_failure.error,
                    )

                # Check if all steps completed -> Invariant 6: AWAITING_VERIFICATION
                if len(completed_steps) == len(step_map):
                    self.quest_engine.transition_quest(
                        quest_id,
                        QuestStatus.AWAITING_VERIFICATION,
                        reason="All DAG plan steps successfully executed",
                    )
                    return self._build_summary(
                        quest_id,
                        initial_status,
                        QuestStatus.AWAITING_VERIFICATION,
                        len(step_map),
                        completed_steps,
                        failed_steps,
                        start_time,
                    )

                # Find ready steps (in-degree == 0 among uncompleted/non-running steps)
                running_ids = set(in_flight.values())
                ready_steps: List[QuestStep] = []
                for step_id, step in step_map.items():
                    if step_id in completed_steps or step_id in running_ids:
                        continue
                    if step.status in (StepStatus.PENDING, StepStatus.READY, StepStatus.PAUSED):
                        # Verify all dependencies are completed
                        deps_satisfied = all(dep in completed_steps for dep in step.dependencies)
                        if deps_satisfied:
                            ready_steps.append(step)

                # If no steps ready and no work in flight -> deadlock/orphan failure
                if not ready_steps and not in_flight:
                    uncompleted = [sid for sid in step_map if sid not in completed_steps]
                    self.quest_engine.transition_quest(
                        quest_id,
                        QuestStatus.FAILED,
                        reason=f"DAG deadlock: uncompleted steps {uncompleted} have unsatisfied dependencies",
                    )
                    return self._build_summary(
                        quest_id,
                        initial_status,
                        QuestStatus.FAILED,
                        len(step_map),
                        completed_steps,
                        failed_steps,
                        start_time,
                        error=f"Unsatisfied dependencies for steps: {uncompleted}",
                    )

                # Separate ready steps into read-only vs mutations
                read_steps = [s for s in ready_steps if s.action_class == ActionClass.READ_ONLY]
                mutation_steps = [s for s in ready_steps if s.action_class != ActionClass.READ_ONLY]

                # Dispatch strategy:
                # Case A: If mutations are ready:
                # Enforce Strict Mutation Barrier (BLK-4)
                if mutation_steps:
                    # 1. Drain all active read workers first
                    if in_flight:
                        drained = self._drain_one_future(
                            in_flight,
                            step_map,
                            completed_steps,
                            failed_steps,
                            quest_id,
                        )
                        if drained and drained.status == StepStatus.PAUSED:
                            is_input_pause = "Missing required input" in (drained.error or "")
                            pause_status = QuestStatus.PAUSED_FOR_INPUT if is_input_pause else QuestStatus.PAUSED_FOR_CONFIRMATION
                            self.quest_engine.transition_quest(
                                quest_id,
                                pause_status,
                                reason=drained.error or "Awaiting user response",
                            )
                            return self._build_summary(
                                quest_id,
                                initial_status,
                                pause_status,
                                len(step_map),
                                completed_steps,
                                failed_steps,
                                start_time,
                                paused_step_id=drained.step_id,
                                confirmation_prompt=drained.error,
                            )
                        continue  # Keep draining until empty

                    # 2. All reads are drained: dispatch ONE mutation under _mutation_lock
                    next_mutation = mutation_steps[0]
                    is_confirmed = (next_mutation.step_id == confirmed_step_id)

                    with self._mutation_lock:
                        # Transition step to RUNNING
                        if next_mutation.status != StepStatus.RUNNING:
                            step_map[next_mutation.step_id] = self.quest_engine.transition_step(
                                quest_id, next_mutation.step_id, StepStatus.RUNNING
                            )

                        receipt = self._execute_step(
                            quest_id,
                            next_mutation,
                            effective_inputs,
                            completed_steps,
                            user_confirmed=is_confirmed,
                        )

                        # Handle pause / completion / failure
                        if receipt.status == StepStatus.PAUSED:
                            is_input_pause = "Missing required input" in (receipt.error or "")
                            pause_status = QuestStatus.PAUSED_FOR_INPUT if is_input_pause else QuestStatus.PAUSED_FOR_CONFIRMATION
                            self.quest_engine.transition_quest(
                                quest_id,
                                pause_status,
                                reason=receipt.error or "Awaiting user response",
                            )
                            return self._build_summary(
                                quest_id,
                                initial_status,
                                pause_status,
                                len(step_map),
                                completed_steps,
                                failed_steps,
                                start_time,
                                paused_step_id=next_mutation.step_id,
                                confirmation_prompt=receipt.error,
                            )
                        elif receipt.status == StepStatus.COMPLETED:
                            step_map[next_mutation.step_id] = self.quest_engine.transition_step(
                                quest_id,
                                next_mutation.step_id,
                                StepStatus.COMPLETED,
                                execution_receipt=receipt.tool_result.model_dump() if receipt.tool_result else None,
                            )
                            completed_steps[next_mutation.step_id] = step_map[next_mutation.step_id]
                        elif receipt.status == StepStatus.AWAITING_RECONCILIATION:
                            step_map[next_mutation.step_id] = self.quest_engine.transition_step(
                                quest_id,
                                next_mutation.step_id,
                                StepStatus.AWAITING_RECONCILIATION,
                                error=receipt.error,
                            )
                            self.quest_engine.transition_quest(
                                quest_id,
                                QuestStatus.PAUSED_FOR_RECONCILIATION,
                                reason=f"Step '{next_mutation.step_id}' entered UNKNOWN_COMMIT: {receipt.error}",
                            )
                            return self._build_summary(
                                quest_id,
                                initial_status,
                                QuestStatus.PAUSED_FOR_RECONCILIATION,
                                len(step_map),
                                completed_steps,
                                failed_steps,
                                start_time,
                                paused_step_id=next_mutation.step_id,
                                error=receipt.error,
                            )
                        else:
                            step_map[next_mutation.step_id] = self.quest_engine.transition_step(
                                quest_id,
                                next_mutation.step_id,
                                StepStatus.FAILED,
                                error=receipt.error,
                            )
                            failed_steps[next_mutation.step_id] = step_map[next_mutation.step_id]
                    continue

                # Case B: Dispatch concurrent read-only steps
                if read_steps:
                    for r_step in read_steps:
                        if len(in_flight) >= self.max_parallel_workers:
                            break  # Worker pool full

                        # Transition step to RUNNING
                        if r_step.status != StepStatus.RUNNING:
                            step_map[r_step.step_id] = self.quest_engine.transition_step(
                                quest_id, r_step.step_id, StepStatus.RUNNING
                            )

                        fut = executor.submit(
                            self._execute_step,
                            quest_id,
                            r_step,
                            effective_inputs,
                            completed_steps,
                            user_confirmed=False,
                        )
                        in_flight[fut] = r_step.step_id

                # If workers are running, wait for at least one to complete
                if in_flight:
                    drained = self._drain_one_future(
                        in_flight,
                        step_map,
                        completed_steps,
                        failed_steps,
                        quest_id,
                    )
                    if drained and drained.status == StepStatus.PAUSED:
                        is_input_pause = "Missing required input" in (drained.error or "")
                        pause_status = QuestStatus.PAUSED_FOR_INPUT if is_input_pause else QuestStatus.PAUSED_FOR_CONFIRMATION
                        self.quest_engine.transition_quest(
                            quest_id,
                            pause_status,
                            reason=drained.error or "Awaiting user response",
                        )
                        return self._build_summary(
                            quest_id,
                            initial_status,
                            pause_status,
                            len(step_map),
                            completed_steps,
                            failed_steps,
                            start_time,
                            paused_step_id=drained.step_id,
                            confirmation_prompt=drained.error,
                        )

    def _drain_one_future(
        self,
        in_flight: Dict[concurrent.futures.Future, str],
        step_map: Dict[str, QuestStep],
        completed_steps: Dict[str, QuestStep],
        failed_steps: Dict[str, QuestStep],
        quest_id: str,
    ) -> Optional[StepExecutionReceipt]:
        """Waits for the next future to complete and processes its receipt."""
        done, _ = concurrent.futures.wait(
            in_flight.keys(),
            return_when=concurrent.futures.FIRST_COMPLETED,
        )
        last_receipt: Optional[StepExecutionReceipt] = None
        for fut in done:
            step_id = in_flight.pop(fut)
            try:
                receipt: StepExecutionReceipt = fut.result()
                last_receipt = receipt
                if receipt.status == StepStatus.COMPLETED:
                    step_map[step_id] = self.quest_engine.transition_step(
                        quest_id,
                        step_id,
                        StepStatus.COMPLETED,
                        execution_receipt=receipt.tool_result.model_dump() if receipt.tool_result else None,
                    )
                    completed_steps[step_id] = step_map[step_id]
                elif receipt.status == StepStatus.PAUSED:
                    # Paused read step (e.g. input required)
                    step_map[step_id] = self.quest_engine.transition_step(
                        quest_id,
                        step_id,
                        StepStatus.PAUSED,
                        error=receipt.error,
                    )
                elif receipt.status == StepStatus.AWAITING_RECONCILIATION:
                    step_map[step_id] = self.quest_engine.transition_step(
                        quest_id,
                        step_id,
                        StepStatus.AWAITING_RECONCILIATION,
                        error=receipt.error,
                    )
                else:
                    step_map[step_id] = self.quest_engine.transition_step(
                        quest_id,
                        step_id,
                        StepStatus.FAILED,
                        error=receipt.error,
                    )
                    failed_steps[step_id] = step_map[step_id]
            except Exception as e:
                step_map[step_id] = self.quest_engine.transition_step(
                    quest_id,
                    step_id,
                    StepStatus.FAILED,
                    error=str(e),
                )
                failed_steps[step_id] = step_map[step_id]
        return last_receipt

    # =========================================================================
    # Step Execution Unit
    # =========================================================================

    def _execute_step(
        self,
        quest_id: str,
        step: QuestStep,
        quest_inputs: Dict[str, Any],
        completed_steps: Dict[str, QuestStep],
        user_confirmed: bool = False,
    ) -> StepExecutionReceipt:
        """Executes a single step adhering to dynamic resolution, policy gating, and ledger tracking."""
        t0 = time.perf_counter()

        # 1. Dynamic Argument Resolution (BLK-3 / AUDIT-12)
        try:
            resolved_args = DynamicResolver.resolve_arguments(
                step.arguments,
                quest_inputs=quest_inputs,
                completed_steps=completed_steps,
            )
        except MissingInputError as mie:
            self.quest_engine.transition_step(
                quest_id,
                step.step_id,
                StepStatus.PAUSED,
                error=f"Missing required input parameter: '{mie.input_key}'",
            )
            return StepExecutionReceipt(
                step_id=step.step_id,
                capability_id=step.capability_id,
                action_class=step.action_class,
                status=StepStatus.PAUSED,
                latency_ms=round((time.perf_counter() - t0) * 1000, 3),
                error=f"Missing required input parameter: '{mie.input_key}'",
            )
        except UnresolvedArgumentError as uae:
            return StepExecutionReceipt(
                step_id=step.step_id,
                capability_id=step.capability_id,
                action_class=step.action_class,
                status=StepStatus.FAILED,
                latency_ms=round((time.perf_counter() - t0) * 1000, 3),
                error=f"Argument resolution error: {uae}",
            )

        # 2. Look up CapabilitySpec
        spec = self.capability_registry.get_spec(step.capability_id)
        if not spec:
            return StepExecutionReceipt(
                step_id=step.step_id,
                capability_id=step.capability_id,
                action_class=step.action_class,
                status=StepStatus.FAILED,
                latency_ms=round((time.perf_counter() - t0) * 1000, 3),
                error=f"Capability '{step.capability_id}' not found in registry",
            )

        # 3. Policy Evaluation Gate
        quest = self.quest_engine.get_quest(quest_id)
        autonomy = quest.autonomy_profile if quest else AutonomyProfile.LOCAL_OPERATOR

        policy_decision = self.policy_engine.evaluate(
            capability=spec,
            arguments=resolved_args,
            autonomy_profile=autonomy,
            user_confirmed=user_confirmed,
        )

        if not policy_decision.allowed:
            if policy_decision.effect == PolicyEffect.REQUIRE_CONFIRMATION:
                # Transition step to PAUSED
                self.quest_engine.transition_step(quest_id, step.step_id, StepStatus.PAUSED)
                return StepExecutionReceipt(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    action_class=step.action_class,
                    status=StepStatus.PAUSED,
                    latency_ms=round((time.perf_counter() - t0) * 1000, 3),
                    error=policy_decision.confirmation_prompt or "Action requires confirmation",
                )
            else:
                return StepExecutionReceipt(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    action_class=step.action_class,
                    status=StepStatus.FAILED,
                    latency_ms=round((time.perf_counter() - t0) * 1000, 3),
                    error=f"Policy denied execution: {policy_decision.denial_reason}",
                )

        # 4. Execution Dispatch
        # Case A: Read-Only Actions (No mutation ledger required)
        if step.action_class == ActionClass.READ_ONLY:
            try:
                tool_res = self.capability_registry.invoke(step.capability_id, resolved_args)
                latency = round((time.perf_counter() - t0) * 1000, 3)
                if tool_res.success:
                    return StepExecutionReceipt(
                        step_id=step.step_id,
                        capability_id=step.capability_id,
                        action_class=step.action_class,
                        status=StepStatus.COMPLETED,
                        tool_result=tool_res,
                        latency_ms=latency,
                    )
                else:
                    err_msg = str(tool_res.error.message if tool_res.error else "Read tool failed")
                    return StepExecutionReceipt(
                        step_id=step.step_id,
                        capability_id=step.capability_id,
                        action_class=step.action_class,
                        status=StepStatus.FAILED,
                        tool_result=tool_res,
                        latency_ms=latency,
                        error=err_msg,
                    )
            except Exception as e:
                return StepExecutionReceipt(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    action_class=step.action_class,
                    status=StepStatus.FAILED,
                    latency_ms=round((time.perf_counter() - t0) * 1000, 3),
                    error=str(e),
                )

        # Case B: Mutating Actions -> Protected by Operation Ledger (ADR-014)
        op_id = f"op_{quest_id}_{step.step_id}_{step.capability_id}"
        op_rec, is_dedup = self.operation_ledger.register_mutation(
            operation_id=op_id,
            quest_id=quest_id,
            step_id=step.step_id,
            capability_id=step.capability_id,
            arguments=resolved_args,
            idempotency_class=spec.idempotency_class,
        )

        # If already committed, return cached receipt immediately!
        if is_dedup and op_rec.state == MutationState.COMMITTED:
            cached_data = op_rec.execution_receipt or {}
            cached_tool_result = ToolResult(
                capability_id=step.capability_id,
                success=True,
                data=cached_data,
            )
            return StepExecutionReceipt(
                step_id=step.step_id,
                capability_id=step.capability_id,
                action_class=step.action_class,
                status=StepStatus.COMPLETED,
                tool_result=cached_tool_result,
                is_deduplicated=True,
                latency_ms=round((time.perf_counter() - t0) * 1000, 3),
            )

        # Execute mutation with attempt recording
        try:
            self.operation_ledger.begin_attempt(op_id)
            tool_res = self.capability_registry.invoke(
                step.capability_id,
                resolved_args,
                operation_id=op_id,
                idempotency_key=op_rec.idempotency_key,
                quest_id=quest_id,
                step_id=step.step_id,
            )
            latency = round((time.perf_counter() - t0) * 1000, 3)

            if tool_res.success:
                receipt_dict = tool_res.model_dump()
                self.operation_ledger.commit_operation(op_id, execution_receipt=receipt_dict)
                return StepExecutionReceipt(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    action_class=step.action_class,
                    status=StepStatus.COMPLETED,
                    tool_result=tool_res,
                    latency_ms=latency,
                )
            else:
                err_msg = str(tool_res.error.message if tool_res.error else "Mutation execution failed")
                # AUDIT-01: Timeouts or network partitions during mutation mean execution outcome is UNCERTAIN (UNKNOWN_COMMIT)!
                is_timeout_or_uncertain = bool(
                    tool_res.error and tool_res.error.code in (ErrorCode.TIMEOUT, ErrorCode.NETWORK_ERROR)
                )
                self.operation_ledger.fail_operation(op_id, error=err_msg, is_uncertain=is_timeout_or_uncertain)
                step_status = StepStatus.AWAITING_RECONCILIATION if is_timeout_or_uncertain else StepStatus.FAILED
                return StepExecutionReceipt(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    action_class=step.action_class,
                    status=step_status,
                    tool_result=tool_res,
                    latency_ms=latency,
                    error=err_msg,
                )

        except Exception as e:
            latency = round((time.perf_counter() - t0) * 1000, 3)
            # Unhandled exceptions mark operation UNKNOWN_COMMIT to block blind retries
            self.operation_ledger.fail_operation(op_id, error=str(e), is_uncertain=True)
            return StepExecutionReceipt(
                step_id=step.step_id,
                capability_id=step.capability_id,
                action_class=step.action_class,
                status=StepStatus.AWAITING_RECONCILIATION,
                latency_ms=latency,
                error=f"Mutation failed with uncertain outcome: {e}",
            )

    # =========================================================================
    # Helpers & Lease Management
    # =========================================================================

    def _acquire_lease(self, quest_id: str) -> None:
        with self._lease_lock:
            if quest_id in self._active_leases:
                raise QuestAlreadyRunningError(
                    f"Execution lease for quest '{quest_id}' is already held by another runner."
                )
            self._active_leases.add(quest_id)

    def _release_lease(self, quest_id: str) -> None:
        with self._lease_lock:
            self._active_leases.discard(quest_id)

    def _reconstruct_plan(self, quest: Quest) -> Plan:
        """Reconstructs a Plan instance from an existing Quest and its steps."""
        plan_steps = []
        for s in quest.steps:
            spec = self.capability_registry.get_spec(s.capability_id)
            max_attempts = 3
            if spec and (spec.retry_policy == RetryPolicy.NEVER or spec.idempotency_class == IdempotencyClass.NON_IDEMPOTENT):
                max_attempts = 1
            if hasattr(s, "max_attempts") and s.max_attempts is not None:
                max_attempts = s.max_attempts
            timeout_s = getattr(s, "timeout_s", None) or (spec.timeout_seconds if spec else 30.0)
            plan_steps.append(
                PlanStep(
                    step_id=s.step_id,
                    capability_id=s.capability_id,
                    intent=s.intent,
                    arguments=s.arguments,
                    dependencies=s.dependencies,
                    max_attempts=max_attempts,
                    timeout_s=timeout_s,
                )
            )
        provenance = quest.metadata.get("plan_provenance", {})
        timeout_budget_s = provenance.get("timeout_budget_s") or quest.metadata.get("timeout_budget_s") or 3600.0
        return Plan(
            quest_id=quest.quest_id,
            goal=quest.goal,
            plan_type=PlanType.TEMPLATE_DERIVED,
            timeout_budget_s=timeout_budget_s,
            steps=plan_steps,
        )

    def _build_summary(
        self,
        quest_id: str,
        initial_status: QuestStatus,
        final_status: QuestStatus,
        total_steps: int,
        completed_steps: Dict[str, QuestStep],
        failed_steps: Dict[str, QuestStep],
        start_time: float,
        paused_step_id: Optional[str] = None,
        confirmation_prompt: Optional[str] = None,
        error: Optional[str] = None,
    ) -> QuestExecutionSummary:
        return QuestExecutionSummary(
            quest_id=quest_id,
            initial_status=initial_status,
            final_status=final_status,
            total_steps=total_steps,
            completed_steps=len(completed_steps),
            failed_steps=len(failed_steps),
            paused_step_id=paused_step_id,
            confirmation_prompt=confirmation_prompt,
            error=error,
            latency_ms=round((time.perf_counter() - start_time) * 1000, 3),
        )
