#!/usr/bin/env python3
"""
LAYA Autonomous V2 Operator CLI
===============================
Deterministic runtime CLI for the LAYA Omni Agent.

Wires the complete autonomous execution stack:
ObjectiveDecomposer -> HierarchicalRouter -> ArgumentResolver -> StructuredDAGPlanner ->
DeterministicPlanValidator -> QuestEngine -> PolicyEngine -> OperationLedger ->
DeterministicDAGExecutor -> SessionManager

Adheres to Prime Directive & Repository Invariants:
1. Deterministic Control: Models propose plans; deterministic software decides and executes.
2. Invariant 5: Persisted SQLite Quest + Validated DAG Execution.
3. Invariant 6: Evidence-Based Execution Receipts.
4. Model Sovereignty: Strictly obeys USER_LOCKED, USER_PREFERRED, AUTO.
5. Zero modifications to legacy omni_agent.py.
"""

import argparse
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Optional dotenv loading with provenance logging (PRACT-019, PRACT-020)
def load_environment_keys() -> str:
    root_dir = Path(__file__).resolve().parent
    keys_file = root_dir / "keys.env"
    env_file = root_dir / ".env"

    loaded_source = "process_environment"
    try:
        from dotenv import load_dotenv
        if keys_file.exists():
            load_dotenv(dotenv_path=keys_file, override=False)
            loaded_source = "keys.env"
        elif env_file.exists():
            load_dotenv(dotenv_path=env_file, override=False)
            loaded_source = ".env"
    except ImportError:
        pass

    return loaded_source


from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    AUTONOMY_RANK,
)
from omni_engine.contracts.policy import OperatorPolicyPreferences
from omni_engine.contracts.quest import QuestStatus, StepStatus
from omni_engine.contracts.broker import ProviderSelectionMode
from omni_engine.capabilities.definitions import build_real_capability_registry
from omni_engine.skills.definitions import build_canonical_skill_registry
from omni_engine.routing.router import HierarchicalRouter
from omni_engine.arguments.resolver import ArgumentResolver
from omni_engine.planning.decomposer import ObjectiveDecomposer
from omni_engine.planning.validator import DeterministicPlanValidator
from omni_engine.planning.engine import StructuredDAGPlanner
from omni_engine.quest.store import QuestStore
from omni_engine.quest.engine import QuestEngine
from omni_engine.operations.store import OperationStore
from omni_engine.operations.ledger import OperationLedger
from omni_engine.policy.engine import PolicyEngine
from omni_engine.execution.executor import DeterministicDAGExecutor, ExecutionFirewallError
from omni_engine.session.manager import SessionManager


class LayaV2Runtime:
    """Encapsulates the assembled LAYA V2 runtime components."""

    def __init__(
        self,
        db_path: str = "laya_runtime.db",
        autonomy_profile: AutonomyProfile = AutonomyProfile.LOCAL_OPERATOR,
        sovereignty: ProviderSelectionMode = ProviderSelectionMode.AUTO,
        preferred_provider: Optional[str] = None,
        verbose: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.autonomy_profile = autonomy_profile
        self.sovereignty = sovereignty
        self.preferred_provider = preferred_provider
        self.verbose = verbose

        # 1. Capability & Skill Registries
        self.capability_registry = build_real_capability_registry()
        self.skill_registry = build_canonical_skill_registry(self.capability_registry)

        # 2. Decomposer, Router & Argument Resolver
        self.decomposer = ObjectiveDecomposer()
        self.router = HierarchicalRouter(
            registry=self.capability_registry,
            skill_registry=self.skill_registry,
        )
        self.argument_resolver = ArgumentResolver()

        # 3. Planning & Validation
        self.plan_validator = DeterministicPlanValidator(
            capability_registry=self.capability_registry,
        )
        self.planner = StructuredDAGPlanner(
            skill_registry=self.skill_registry,
            capability_registry=self.capability_registry,
        )

        # 4. Persistence & State Substrate
        self.quest_store = QuestStore(db_path=self.db_path)
        self.quest_engine = QuestEngine(store=self.quest_store)
        self.operation_store = OperationStore(db_path=self.db_path)
        self.operation_ledger = OperationLedger(store=self.operation_store)

        # 5. Policy Engine
        self.policy_engine = PolicyEngine(default_autonomy=self.autonomy_profile)

        # 6. Execution Runtime
        self.executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.capability_registry,
            policy_engine=self.policy_engine,
            operation_ledger=self.operation_ledger,
            plan_validator=self.plan_validator,
        )

        # 7. Interactive Session Manager
        self.session_manager = SessionManager(
            quest_engine=self.quest_engine,
            executor=self.executor,
        )

    def execute_prompt(
        self,
        prompt: str,
        session_id: str = "default_session",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Executes a single operator prompt through the complete V2 pipeline."""
        start_time = time.perf_counter()

        # Step 0: Session Continuation Check (PRACT-011)
        handled, resume_summary, msg = self.session_manager.handle_interactive_input(session_id, prompt)
        if handled and resume_summary:
            if self.verbose:
                print(f"[Session] {msg}")
            return {
                "quest_id": resume_summary.quest_id,
                "status": resume_summary.final_status.value,
                "summary": resume_summary,
                "is_resumed": True,
                "latency_ms": resume_summary.latency_ms,
            }

        # Step 1: Referent Resolution (PRACT-028)
        resolved_prompt, session_context = self.session_manager.resolve_referents(session_id, prompt)

        # Step 2: Objective Decomposition (Section 6 & 13)
        objective_spec = self.decomposer.decompose(resolved_prompt)

        # Step 3: Hierarchical Routing
        route_decision = self.router.route(resolved_prompt)

        # Step 4: Semantic Argument Resolution
        top_cap_id = route_decision.candidates[0].capability_id if route_decision.candidates else None
        top_spec = self.capability_registry.get_spec(top_cap_id) if top_cap_id else None
        resolved_args = {}
        # If a skill was selected, resolve skill-level arguments first (PRACT-029)
        if route_decision.selected_skill and self.skill_registry and self.skill_registry.has(route_decision.selected_skill):
            skill = self.skill_registry.get(route_decision.selected_skill)
            if skill:
                skill_envelope = self.argument_resolver.resolve(
                    capability=skill,
                    prompt=resolved_prompt,
                )
                resolved_args.update(skill_envelope.arguments)

        # Also extract arguments for top routed capability if not already resolved
        if top_spec:
            arg_envelope = self.argument_resolver.resolve(
                capability=top_spec,
                prompt=resolved_prompt,
            )
            for k, v in arg_envelope.arguments.items():
                if k not in resolved_args:
                    resolved_args[k] = v

        # Step 5: Structured DAG Planning (Template-as-Building-Block)
        quest = self.quest_engine.create_quest(
            title=resolved_prompt[:60],
            goal=resolved_prompt,
            autonomy_profile=self.autonomy_profile,
            metadata={"objective_spec": objective_spec.model_dump()},
        )
        self.session_manager.set_active_quest(session_id, quest.quest_id)

        plan = self.planner.create_plan(
            quest_id=quest.quest_id,
            goal=resolved_prompt,
            skill_id=route_decision.selected_skill,
            route_decision=route_decision,
            arguments=resolved_args,
        )

        # Step 6: Deterministic 10-Pass Plan Validation Firewall
        validation_report = self.plan_validator.validate(
            plan=plan,
            autonomy_profile=self.autonomy_profile,
        )
        if not validation_report.is_valid:
            self.quest_engine.transition_quest(
                quest.quest_id,
                QuestStatus.FAILED,
                reason="Plan validation rejected by deterministic firewall",
            )
            self.session_manager.clear_active_quest(session_id)
            return {
                "quest_id": quest.quest_id,
                "status": QuestStatus.FAILED.value,
                "errors": validation_report.errors,
                "validation_report": validation_report,
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 3),
            }

        if dry_run:
            return {
                "quest_id": quest.quest_id,
                "status": "PLAN_VALIDATED",
                "plan": plan.model_dump(),
                "validation_report": validation_report.model_dump(),
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 3),
            }

        # Step 7: Deterministic DAG Execution
        summary = self.executor.execute(
            quest_id=quest.quest_id,
            plan=plan,
            inputs=resolved_args,
        )

        # Step 8: Record Results in Session Manager
        if summary.final_status in (QuestStatus.COMPLETED, QuestStatus.AWAITING_VERIFICATION):
            last_step_out = None
            q_after = self.quest_engine.get_quest(quest.quest_id)
            if q_after and q_after.steps:
                last_step_out = q_after.steps[-1].execution_receipt
            self.session_manager.record_step_result(
                session_id=session_id,
                result=last_step_out,
                output_summary=str(last_step_out)[:300] if last_step_out else None,
            )
            self.session_manager.clear_active_quest(session_id, mark_completed=True)
        elif summary.final_status in (QuestStatus.FAILED, QuestStatus.CANCELLED):
            self.session_manager.clear_active_quest(session_id)

        return {
            "quest_id": quest.quest_id,
            "status": summary.final_status.value,
            "summary": summary,
            "plan": plan,
            "validation_report": validation_report,
            "latency_ms": round((time.perf_counter() - start_time) * 1000, 3),
        }


def format_summary_table(res: Dict[str, Any]) -> str:
    """Formats execution outcome for human console readability."""
    lines = []
    lines.append("=" * 72)
    lines.append(f"QUEST EXECUTION RECEIPT: {res.get('quest_id')}")
    lines.append("=" * 72)
    lines.append(f"Status       : {res.get('status')}")
    lines.append(f"Latency      : {res.get('latency_ms', 0)} ms")

    summary = res.get("summary")
    if summary:
        lines.append(f"Total Steps  : {summary.total_steps}")
        lines.append(f"Completed    : {summary.completed_steps}")
        lines.append(f"Failed       : {summary.failed_steps}")
        if summary.paused_step_id:
            lines.append(f"Paused Step  : {summary.paused_step_id}")
        if summary.confirmation_prompt:
            lines.append(f"Prompt       : {summary.confirmation_prompt}")
        if summary.error:
            lines.append(f"Error/Reason : {summary.error}")

    errors = res.get("errors")
    if errors:
        lines.append("Plan Validation Errors:")
        for err in errors:
            lines.append(f"  - {err}")

    plan = res.get("plan")
    if plan:
        steps = plan.get("steps") if isinstance(plan, dict) else getattr(plan, "steps", None)
        if steps:
            lines.append("-" * 72)
            lines.append("Planned DAG Steps:")
            for idx, s in enumerate(steps, 1):
                if isinstance(s, dict):
                    step_id = s.get("step_id")
                    cap_id = s.get("capability_id")
                    intent = s.get("intent")
                    raw_deps = s.get("dependencies", [])
                else:
                    step_id = getattr(s, "step_id", "")
                    cap_id = getattr(s, "capability_id", "")
                    intent = getattr(s, "intent", "")
                    raw_deps = getattr(s, "dependencies", [])
                deps = f" (deps: {', '.join(raw_deps)})" if raw_deps else ""
                lines.append(f"  {idx}. [{step_id}] {cap_id} -> {intent}{deps}")

    lines.append("=" * 72)
    return "\n".join(lines)


def run_repl(runtime: LayaV2Runtime, session_id: str = "default_session") -> None:
    """Runs interactive multi-turn REPL loop."""
    print("\n" + "=" * 72)
    print("LAYA OMNI AGENT — Interactive Operator Console (V2 Runtime)")
    print("Type your objective, 'status', 'cancel', or 'exit' to quit.")
    print("=" * 72 + "\n")

    while True:
        try:
            prompt = input("laya> ").strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit", "q"):
                print("Exiting LAYA operator console.")
                break
            if prompt.lower() == "status":
                sess = runtime.session_manager.get_or_create_session(session_id)
                print(f"Session ID : {sess.session_id}")
                print(f"Active Quest: {sess.active_quest_id or 'None'}")
                print(f"Last Output : {sess.last_output_summary or 'None'}")
                continue

            res = runtime.execute_prompt(prompt, session_id=session_id)
            print(format_summary_table(res))
            print()
        except KeyboardInterrupt:
            print("\nInterrupt received. Use 'exit' to quit.")
        except Exception as e:
            print(f"[Error] {type(e).__name__}: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="LAYA Autonomous V2 Operator CLI")
    parser.add_argument("-p", "--prompt", type=str, help="Objective or prompt to execute directly")
    parser.add_argument("-a", "--autonomy", type=str, default="local_operator",
                        choices=["advisor", "safe_assistant", "local_operator", "trusted_operator", "workflow_authorized"],
                        help="Autonomy profile (default: local_operator)")
    parser.add_argument("--sovereignty", type=str, default="auto", choices=["locked", "preferred", "auto"],
                        help="Model sovereignty policy (default: auto)")
    parser.add_argument("--provider", type=str, default=None, choices=["laya", "jev", "openrouter"],
                        help="Preferred model provider")
    parser.add_argument("--dry-run", action="store_true", help="Synthesize and validate plan without execution")
    parser.add_argument("--db", type=str, default="laya_runtime.db", help="SQLite database path")
    parser.add_argument("--verbose", action="store_true", help="Print verbose step and validation logs")

    args = parser.parse_args()

    # Load keys with provenance logging
    source = load_environment_keys()
    if args.verbose:
        print(f"[Config] Loaded environment variables from: {source}")

    autonomy_map = {
        "advisor": AutonomyProfile.ADVISOR,
        "safe_assistant": AutonomyProfile.SAFE_ASSISTANT,
        "local_operator": AutonomyProfile.LOCAL_OPERATOR,
        "trusted_operator": AutonomyProfile.TRUSTED_OPERATOR,
        "workflow_authorized": AutonomyProfile.WORKFLOW_AUTHORIZED,
    }
    sovereignty_map = {
        "locked": ProviderSelectionMode.USER_LOCKED,
        "preferred": ProviderSelectionMode.USER_PREFERRED,
        "auto": ProviderSelectionMode.AUTO,
    }

    runtime = LayaV2Runtime(
        db_path=args.db,
        autonomy_profile=autonomy_map.get(args.autonomy.lower(), AutonomyProfile.LOCAL_OPERATOR),
        sovereignty=sovereignty_map.get(args.sovereignty.lower(), ProviderSelectionMode.AUTO),
        preferred_provider=args.provider,
        verbose=args.verbose,
    )

    if args.prompt:
        res = runtime.execute_prompt(args.prompt, dry_run=args.dry_run)
        print(format_summary_table(res))
        status = res.get("status")
        if status in ("COMPLETED", "AWAITING_VERIFICATION", "PLAN_VALIDATED"):
            return 0
        elif status in ("PAUSED_FOR_CONFIRMATION", "PAUSED_FOR_INPUT"):
            return 0
        return 1
    else:
        run_repl(runtime)
        return 0


if __name__ == "__main__":
    sys.exit(main())
