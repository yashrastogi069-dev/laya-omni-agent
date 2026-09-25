"""Quest State Machine & Execution Coordinator.

Implements deterministic state machine validation, event emission,
and optimistic concurrency control for durable Quests (Checkpoint L10).
"""

import time
import uuid
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from ..contracts.enums import ActionClass, AutonomyProfile
from ..contracts.quest import (
    InvalidStateTransitionError,
    OptimisticLockError,
    Quest,
    QuestError,
    QuestEvent,
    QuestEventEnum,
    QuestNotFoundError,
    QuestStatus,
    QuestStep,
    StepNotFoundError,
    StepStatus,
    TERMINAL_QUEST_STATES,
    TERMINAL_STEP_STATES,
    VALID_QUEST_TRANSITIONS,
    VALID_STEP_TRANSITIONS,
)
from .store import QuestStore


class QuestEngine:
    """State machine controller and lifecycle coordinator for Quests.
    
    Guarantees:
    1. Deterministic Control: No state transition can occur without validating against the transition matrix.
    2. Evidence-Based Completion: Quests cannot jump directly from RUNNING to COMPLETED; must pass through AWAITING_VERIFICATION.
    3. Terminal Invariant: Terminal states (COMPLETED, FAILED, CANCELLED) are strictly absorbing.
    4. Comprehensive Audit Trail: Every state transition emits an immutable QuestEvent.
    """

    def __init__(self, store: Optional[QuestStore] = None, db_path: Union[str, Path] = ":memory:"):
        """Initialize the Quest Engine.
        
        Args:
            store: Pre-configured QuestStore instance. If None, instantiates a new one with db_path.
            db_path: Path to database file if store is None.
        """
        self.store = store if store is not None else QuestStore(db_path)

    # =========================================================================
    # Quest Lifecycle Management
    # =========================================================================

    def create_quest(
        self,
        title: str,
        goal: str,
        autonomy_profile: AutonomyProfile = AutonomyProfile.LOCAL_OPERATOR,
        metadata: Optional[Dict[str, Any]] = None,
        initial_steps: Optional[List[QuestStep]] = None,
        quest_id: Optional[str] = None,
    ) -> Quest:
        """Creates and persists a new Quest in CREATED (or PLANNED) state.
        
        Args:
            title: Human-readable quest title.
            goal: Formal objective of the quest.
            autonomy_profile: Maximum autonomy permitted for this quest.
            metadata: Arbitrary metadata dictionary.
            initial_steps: Optional pre-planned steps.
            quest_id: Optional custom quest ID. If None, generates qst_<uuid>.
            
        Returns:
            The created and persisted Quest.
        """
        q_id = quest_id or f"qst_{uuid.uuid4().hex[:12]}"
        now = time.time()
        initial_status = QuestStatus.PLANNED if initial_steps else QuestStatus.CREATED

        quest = Quest(
            quest_id=q_id,
            title=title,
            goal=goal,
            status=initial_status,
            version=1,
            autonomy_profile=autonomy_profile,
            current_step_id=None,
            steps=initial_steps or [],
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        persisted = self.store.create_quest(quest)

        # Emit audit event
        self.store.record_event(
            QuestEvent(
                quest_id=q_id,
                event_type=QuestEventEnum.QUEST_CREATED,
                payload={
                    "title": title,
                    "goal": goal,
                    "autonomy_profile": autonomy_profile.value,
                    "initial_status": initial_status.value,
                    "steps_count": len(initial_steps or []),
                },
                timestamp=now,
            )
        )

        if initial_steps:
            self.store.record_event(
                QuestEvent(
                    quest_id=q_id,
                    event_type=QuestEventEnum.PLAN_ATTACHED,
                    payload={"step_ids": [s.step_id for s in initial_steps]},
                    timestamp=now,
                )
            )

        return persisted

    def attach_plan(
        self,
        quest_id: str,
        steps: List[QuestStep],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Quest:
        """Attaches a planned step sequence to a CREATED quest, moving it to PLANNED.
        
        Args:
            quest_id: Target quest ID.
            steps: List of QuestStep objects to attach.
            metadata: Optional additional metadata (e.g. plan provenance) to merge into the Quest.
            
        Returns:
            Updated Quest in PLANNED status.
            
        Raises:
            QuestNotFoundError: If quest does not exist.
            InvalidStateTransitionError: If quest is not in CREATED status.
        """
        quest = self.store.get_quest(quest_id)
        if not quest:
            raise QuestNotFoundError(f"Quest {quest_id} not found")

        self._validate_quest_transition(quest.status, QuestStatus.PLANNED)

        # Atomically save steps, update quest, and record event in a single transaction (AUDIT-05)
        new_metadata = dict(quest.metadata or {})
        if metadata:
            new_metadata.update(metadata)

        updated_quest = quest.model_copy(
            update={
                "status": QuestStatus.PLANNED,
                "steps": steps,
                "metadata": new_metadata,
            }
        )
        event_payload: Dict[str, Any] = {"step_ids": [s.step_id for s in steps]}
        if metadata:
            event_payload["metadata"] = metadata

        event = QuestEvent(
            quest_id=quest_id,
            event_type=QuestEventEnum.PLAN_ATTACHED,
            payload=event_payload,
        )
        return self.store.attach_plan_atomic(updated_quest, steps, event)

    def transition_quest(
        self,
        quest_id: str,
        target_status: QuestStatus,
        reason: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Quest:
        """Transitions a Quest to a new status according to the strict state machine.
        
        Atomically updates the Quest status and records the audit event in a single transaction (AUDIT-05).
        
        Args:
            quest_id: Target quest ID.
            target_status: The destination QuestStatus.
            reason: Optional justification or context for the transition.
            payload: Additional event payload data.
            
        Returns:
            The updated Quest.
            
        Raises:
            QuestNotFoundError: If quest does not exist.
            InvalidStateTransitionError: If the transition is prohibited.
            OptimisticLockError: If a concurrent modification occurred.
        """
        quest = self.store.get_quest(quest_id)
        if not quest:
            raise QuestNotFoundError(f"Quest {quest_id} not found")

        self._validate_quest_transition(quest.status, target_status)

        # Map target status to audit event
        event_type = self._map_quest_status_to_event(target_status, quest.status)
        evt_payload = dict(payload or {})
        if reason:
            evt_payload["reason"] = reason
        evt_payload["from_status"] = quest.status.value
        evt_payload["to_status"] = target_status.value

        event = QuestEvent(
            quest_id=quest_id,
            event_type=event_type,
            payload=evt_payload,
        )

        updated_quest = quest.model_copy(update={"status": target_status})
        return self.store.transition_quest_atomic(updated_quest, event)

    # =========================================================================
    # Step Lifecycle Management
    # =========================================================================

    def transition_step(
        self,
        quest_id: str,
        step_id: str,
        target_status: StepStatus,
        execution_receipt: Optional[Dict[str, Any]] = None,
        verification_receipt: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> QuestStep:
        """Transitions an individual step to a new execution state.
        
        Atomically updates the step state and records the audit event in a single transaction (AUDIT-05).
        
        Args:
            quest_id: Parent quest ID.
            step_id: Target step ID.
            target_status: The destination StepStatus.
            execution_receipt: Optional tool execution results.
            verification_receipt: Optional independent verification outcome.
            error: Optional error description if step failed.
            
        Returns:
            The updated QuestStep.
            
        Raises:
            StepNotFoundError: If the step does not exist.
            InvalidStateTransitionError: If transition is prohibited.
        """
        step = self.store.get_step(quest_id, step_id)
        if not step:
            raise StepNotFoundError(f"Step {step_id} in Quest {quest_id} not found")

        self._validate_step_transition(step.status, target_status)

        updates: Dict[str, Any] = {"status": target_status}
        if execution_receipt is not None:
            updates["execution_receipt"] = execution_receipt
        if verification_receipt is not None:
            updates["verification_receipt"] = verification_receipt
        if error is not None:
            updates["error"] = error

        updated_step = step.model_copy(update=updates)

        # Update quest current_step_id if running (safe against concurrent worker OCC collisions)
        if target_status == StepStatus.RUNNING:
            quest = self.store.get_quest(quest_id)
            if quest and quest.current_step_id != step_id:
                quest_update = quest.model_copy(update={"current_step_id": step_id})
                try:
                    self.store.update_quest(quest_update)
                except OptimisticLockError:
                    pass

        # Record step audit event atomically with the step update
        step_event_type = self._map_step_status_to_event(target_status)
        evt_payload: Dict[str, Any] = {
            "from_status": step.status.value,
            "to_status": target_status.value,
        }
        if error:
            evt_payload["error"] = error

        event = QuestEvent(
            quest_id=quest_id,
            step_id=step_id,
            event_type=step_event_type,
            payload=evt_payload,
        )

        return self.store.transition_step_atomic(updated_step, event)

    # =========================================================================
    # Queries & Helpers
    # =========================================================================

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Retrieves a Quest and its steps."""
        return self.store.get_quest(quest_id)

    def get_step(self, quest_id: str, step_id: str) -> Optional[QuestStep]:
        """Retrieves a single step."""
        return self.store.get_step(quest_id, step_id)

    def get_events(self, quest_id: str) -> List[QuestEvent]:
        """Retrieves chronological events for a Quest."""
        return self.store.get_events(quest_id)

    def list_active_quests(self) -> List[Quest]:
        """Lists all quests currently in a non-terminal state."""
        return self.store.list_active_quests()

    def recover_active_quests(self) -> List[Quest]:
        """Reconstructs state on startup or recovery.
        
        Returns all quests in non-terminal states.
        """
        return self.store.list_active_quests()

    def close(self) -> None:
        """Closes store connections."""
        self.store.close()

    # =========================================================================
    # Transition Validation Logic
    # =========================================================================

    @staticmethod
    def _validate_quest_transition(current: QuestStatus, target: QuestStatus) -> None:
        """Validates that a Quest state transition is permitted."""
        if current in TERMINAL_QUEST_STATES:
            raise InvalidStateTransitionError(
                f"Quest is in terminal state '{current.value}' and cannot transition to '{target.value}'."
            )

        allowed = VALID_QUEST_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal Quest state transition from '{current.value}' to '{target.value}'. "
                f"Allowed destination states: {[s.value for s in allowed]}."
            )

    @staticmethod
    def _validate_step_transition(current: StepStatus, target: StepStatus) -> None:
        """Validates that a Step state transition is permitted."""
        if current in TERMINAL_STEP_STATES:
            raise InvalidStateTransitionError(
                f"Step is in terminal state '{current.value}' and cannot transition to '{target.value}'."
            )

        allowed = VALID_STEP_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal Step state transition from '{current.value}' to '{target.value}'. "
                f"Allowed destination states: {[s.value for s in allowed]}."
            )

    @staticmethod
    def _map_quest_status_to_event(target: QuestStatus, current: QuestStatus) -> QuestEventEnum:
        """Maps a target quest status to the corresponding audit event type."""
        mapping = {
            QuestStatus.PLANNED: QuestEventEnum.PLAN_ATTACHED,
            QuestStatus.RUNNING: (
                QuestEventEnum.QUEST_RESUMED
                if current in (QuestStatus.PAUSED_FOR_CONFIRMATION, QuestStatus.PAUSED_FOR_INPUT, QuestStatus.PAUSED_FOR_RECONCILIATION)
                else QuestEventEnum.STEP_STARTED
            ),
            QuestStatus.PAUSED_FOR_CONFIRMATION: QuestEventEnum.QUEST_PAUSED,
            QuestStatus.PAUSED_FOR_INPUT: QuestEventEnum.QUEST_PAUSED,
            QuestStatus.PAUSED_FOR_RECONCILIATION: QuestEventEnum.QUEST_PAUSED_FOR_RECONCILIATION,
            QuestStatus.AWAITING_VERIFICATION: QuestEventEnum.QUEST_AWAITING_VERIFICATION,
            QuestStatus.COMPLETED: QuestEventEnum.QUEST_COMPLETED,
            QuestStatus.FAILED: QuestEventEnum.QUEST_FAILED,
            QuestStatus.CANCELLED: QuestEventEnum.QUEST_CANCELLED,
        }
        return mapping.get(target, QuestEventEnum.QUEST_PAUSED)

    @staticmethod
    def _map_step_status_to_event(target: StepStatus) -> QuestEventEnum:
        """Maps a step status to the corresponding audit event type."""
        mapping = {
            StepStatus.READY: QuestEventEnum.STEP_RESUMED,
            StepStatus.RUNNING: QuestEventEnum.STEP_STARTED,
            StepStatus.PAUSED: QuestEventEnum.STEP_PAUSED,
            StepStatus.AWAITING_RECONCILIATION: QuestEventEnum.STEP_AWAITING_RECONCILIATION,
            StepStatus.COMPLETED: QuestEventEnum.STEP_COMPLETED,
            StepStatus.FAILED: QuestEventEnum.STEP_FAILED,
            StepStatus.CANCELLED: QuestEventEnum.STEP_FAILED,
            StepStatus.SKIPPED: QuestEventEnum.STEP_COMPLETED,
            StepStatus.AWAITING_VERIFICATION: QuestEventEnum.STEP_COMPLETED,
        }
        return mapping.get(target, QuestEventEnum.STEP_STARTED)
