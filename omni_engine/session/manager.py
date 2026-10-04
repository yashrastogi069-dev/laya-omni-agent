"""
omni_engine.session.manager
===========================
Interactive session manager tracking active quests, referent bindings,
and multi-turn continuation for the LAYA Autonomous V2 runtime.

Adheres to:
- PRACT-011: Missing-input clarification continues existing Quest.
- PRACT-028: Multi-turn conversational referent resolution ("this", "the results", etc.).
- Invariant 1: Deterministic Control — Models propose, runtime manages session state.
"""

import os
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from omni_engine.contracts.execution import QuestExecutionSummary
from omni_engine.contracts.quest import QuestStatus, StepStatus


class SessionState(BaseModel):
    """Encapsulates persisted interactive session state across operator turns."""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(description="Unique session identifier")
    active_quest_id: Optional[str] = Field(default=None, description="Currently executing or paused quest ID")
    last_completed_quest_id: Optional[str] = Field(default=None, description="Last completed quest ID")
    last_tool_result: Optional[Dict[str, Any]] = Field(default=None, description="Output envelope of last tool/step execution")
    last_output_summary: Optional[str] = Field(default=None, description="Textual summary of last execution output")
    last_target_path: Optional[str] = Field(default=None, description="Last targeted file or directory path")
    last_target_url: Optional[str] = Field(default=None, description="Last targeted browser/web URL")
    conversation_turn: int = Field(default=0, description="Sequential interaction turn count")
    context_history: List[Dict[str, Any]] = Field(default_factory=list, description="Recent conversation turns")
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class SessionManager:
    """Thread-safe session state and referent resolution engine."""

    REFERENT_PATTERNS = [
        re.compile(r"\b(?:save|write|export|send|use)\s+(?:this|it|the\s+results?|the\s+findings?|the\s+output|them)\b", re.IGNORECASE),
        re.compile(r"\b(?:what\s+about|show|display|inspect)\s+(?:this|it|the\s+results?)\b", re.IGNORECASE),
    ]

    CONFIRMATION_AFFIRMATIVE = {
        "yes", "y", "confirm", "proceed", "approve", "ok", "okay", "sure", "allow", "execute", "go"
    }
    CONFIRMATION_NEGATIVE = {
        "no", "n", "cancel", "deny", "reject", "abort", "stop", "never", "disallow"
    }

    def __init__(
        self,
        quest_engine: Optional[Any] = None,
        executor: Optional[Any] = None,
    ) -> None:
        self.quest_engine = quest_engine
        self.executor = executor
        self._sessions: Dict[str, SessionState] = {}
        self._lock = threading.RLock()

    def get_or_create_session(self, session_id: Optional[str] = None) -> SessionState:
        """Retrieves existing session or initializes a new SessionState."""
        with self._lock:
            sid = session_id or "default_session"
            if sid not in self._sessions:
                self._sessions[sid] = SessionState(session_id=sid)
            return self._sessions[sid]

    def set_active_quest(self, session_id: str, quest_id: str) -> None:
        """Sets the active quest ID for the given session."""
        with self._lock:
            session = self.get_or_create_session(session_id)
            session.active_quest_id = quest_id
            session.updated_at = time.time()

    def clear_active_quest(self, session_id: str, mark_completed: bool = False) -> None:
        """Clears active quest pointer upon completion or termination."""
        with self._lock:
            session = self.get_or_create_session(session_id)
            if mark_completed and session.active_quest_id:
                session.last_completed_quest_id = session.active_quest_id
            session.active_quest_id = None
            session.updated_at = time.time()

    def record_step_result(
        self,
        session_id: str,
        result: Any,
        output_summary: Optional[str] = None,
        target_path: Optional[str] = None,
        target_url: Optional[str] = None,
    ) -> None:
        """Records execution result to support referent resolution in future turns (PRACT-028)."""
        with self._lock:
            session = self.get_or_create_session(session_id)
            if hasattr(result, "model_dump"):
                session.last_tool_result = result.model_dump()
            elif isinstance(result, dict):
                session.last_tool_result = dict(result)
            elif result is not None:
                session.last_tool_result = {"output": str(result)}

            if output_summary:
                session.last_output_summary = output_summary
            elif session.last_tool_result:
                out = session.last_tool_result.get("output")
                if out:
                    session.last_output_summary = str(out)[:500]

            if target_path:
                session.last_target_path = target_path
            if target_url:
                session.last_target_url = target_url

            session.conversation_turn += 1
            session.updated_at = time.time()

    def resolve_referents(
        self,
        session_id: str,
        user_prompt: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """Detects referents ('this', 'the results') and binds prior turn context."""
        with self._lock:
            session = self.get_or_create_session(session_id)
            bound_context: Dict[str, Any] = {}

            has_referent = any(pat.search(user_prompt) for pat in self.REFERENT_PATTERNS)
            if has_referent and session.last_tool_result:
                bound_context["last_tool_result"] = session.last_tool_result
                bound_context["last_output_summary"] = session.last_output_summary
                if session.last_target_path:
                    bound_context["last_target_path"] = session.last_target_path
                if session.last_target_url:
                    bound_context["last_target_url"] = session.last_target_url

            return user_prompt, bound_context

    def is_confirmation_response(self, text: str) -> Optional[bool]:
        """Classifies affirmative vs negative confirmation answers."""
        cleaned = text.strip().lower()
        if cleaned in self.CONFIRMATION_AFFIRMATIVE:
            return True
        if cleaned in self.CONFIRMATION_NEGATIVE:
            return False
        return None

    def handle_interactive_input(
        self,
        session_id: str,
        user_input: str,
    ) -> Tuple[bool, Optional[QuestExecutionSummary], Optional[str]]:
        """Handles operator input in the context of an active paused Quest.
        
        Returns:
            Tuple of (handled_by_active_quest: bool, execution_summary: Optional, message: Optional[str]).
        """
        with self._lock:
            session = self.get_or_create_session(session_id)
            if not session.active_quest_id or not self.quest_engine or not self.executor:
                return False, None, None

            quest = self.quest_engine.get_quest(session.active_quest_id)
            if not quest:
                session.active_quest_id = None
                return False, None, None

            # Case 1: Paused for Confirmation
            if quest.status == QuestStatus.PAUSED_FOR_CONFIRMATION:
                conf = self.is_confirmation_response(user_input)
                if conf is not None:
                    summary = self.executor.resume(quest.quest_id, user_confirmation=conf)
                    if summary.final_status in (QuestStatus.COMPLETED, QuestStatus.FAILED, QuestStatus.CANCELLED):
                        self.clear_active_quest(session_id, mark_completed=(summary.final_status == QuestStatus.COMPLETED))
                    return True, summary, f"Resumed quest '{quest.quest_id}' with confirmation={conf}"

            # Case 2: Paused for Missing Input (PRACT-011)
            elif quest.status == QuestStatus.PAUSED_FOR_INPUT:
                # Discover the missing input parameter name
                missing_param = None
                for step in quest.steps:
                    if step.status == StepStatus.PAUSED and step.error:
                        match = re.search(r"Missing required input parameter '(\w+)'", step.error)
                        if match:
                            missing_param = match.group(1)
                            break
                        match_slot = re.search(r"parameter '(\w+)'", step.error)
                        if match_slot:
                            missing_param = match_slot.group(1)
                            break

                inputs = {missing_param: user_input.strip()} if missing_param else {"user_input": user_input.strip()}
                summary = self.executor.resume(quest.quest_id, user_inputs=inputs)
                if summary.final_status in (QuestStatus.COMPLETED, QuestStatus.FAILED, QuestStatus.CANCELLED):
                    self.clear_active_quest(session_id, mark_completed=(summary.final_status == QuestStatus.COMPLETED))
                return True, summary, f"Resumed quest '{quest.quest_id}' with input parameter: {inputs}"

            return False, None, None
