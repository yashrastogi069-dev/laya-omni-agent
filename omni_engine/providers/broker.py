"""
omni_engine.providers.broker
============================
SystemOneBroker: Fast Decision Nervous System Provider Broker with
Ironclad User Model Sovereignty, Strict Allowlist Governance, and
Evidence-Based Precedence Routing.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): User policy, provider allowlists, and
  privacy constraints are binding rules evaluated before model selection.
- Fast Decision Nervous System (Invariant 2): Sub-millisecond broker evaluation (<1ms).
- Strongly Typed Contracts (Invariant 4): Standardized BrokerDecision envelopes.
- Signals are First-Class (Invariant 7): Fallback reasons, latencies, and provider
  provenance are explicitly tracked in all outgoing DecisionSignals.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from omni_engine.contracts.enums import DecisionSignalType, ErrorCode
from omni_engine.contracts.decision import DecisionSignal
from omni_engine.contracts.broker import (
    BrokerDecision,
    BrokerRoutingOutcome,
    FallbackReason,
    ProviderPolicyConfig,
    ProviderSelectionMode,
    TaskProviderOverride,
)
from .base import ProviderError, ProviderHealth, SystemOneProvider
from .system1 import LayaProvider, JevProvider, is_ram_pressure_critical


class SystemOneBroker(SystemOneProvider):
    """Orchestrates System 1 provider selection within strict user policy boundaries.

    Implements SystemOneProvider so downstream components (DecisionFabric, HierarchicalRouter)
    can consume the broker transparently.
    """

    def __init__(
        self,
        policy_config: Optional[ProviderPolicyConfig] = None,
        custom_providers: Optional[Dict[str, SystemOneProvider]] = None,
    ) -> None:
        self.policy_config = policy_config or ProviderPolicyConfig()
        self.provider_id = "system_one_broker"
        self.model_id = "broker-v1"
        self.is_configured = True

        # Initialize canonical providers or accept injected mocks for testing
        if custom_providers is not None:
            self._providers = dict(custom_providers)
        else:
            self._providers = {
                "laya_english": LayaProvider(model_name="english", preload=False),
                "laya_typed_decisions": LayaProvider(model_name="typed-decisions", preload=False),
                "jev": JevProvider(),
            }

    def register_provider(self, name: str, provider: SystemOneProvider) -> None:
        """Registers or replaces a named provider in the broker registry."""
        self._providers[name.strip().lower()] = provider

    def get_provider(self, name: str) -> Optional[SystemOneProvider]:
        """Retrieves a provider by name from the broker registry."""
        return self._providers.get(name.strip().lower())

    def resolve_provider(
        self,
        task_override: Optional[TaskProviderOverride] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[SystemOneProvider, BrokerDecision]:
        """Resolves the active provider under user policy precedence:

        SESSION USER POLICY -> ALLOWLIST FILTER -> PRIVACY/OFFLINE CONSTRAINTS
        -> TASK OVERRIDE -> QUALITY FLOOR -> HEALTH -> RESOURCE PRESSURE -> COST
        """
        t0 = time.perf_counter()
        mode = self.policy_config.mode
        allowed = [p.lower() for p in self.policy_config.allowed_providers]
        default_pref = self.policy_config.preferred_provider.lower()

        # Step 1: Determine initial target provider
        target_provider_name = default_pref
        task_prov = task_override.target_provider.lower() if task_override and task_override.target_provider else None
        privacy_local_only = task_override.privacy_local_only if task_override else False
        latency_priority = task_override.latency_priority if task_override else False

        # -------------------------------------------------------------------
        # Precedence Rule 1: USER_LOCKED is Absolute
        # -------------------------------------------------------------------
        if mode == ProviderSelectionMode.USER_LOCKED:
            # Validate locked provider is allowed
            if target_provider_name not in allowed:
                raise ProviderError(
                    code=ErrorCode.UNAUTHORIZED_ACTION,
                    message=f"Locked provider '{target_provider_name}' is not in allowed_providers: {allowed}",
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                )

            # Task override cannot violate USER_LOCKED
            if task_prov and task_prov != target_provider_name:
                raise ProviderError(
                    code=ErrorCode.UNAUTHORIZED_ACTION,
                    message=f"Task override '{task_prov}' rejected: Session mode is USER_LOCKED to '{target_provider_name}'",
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                )

            # Privacy constraint conflict with locked remote provider
            is_target_remote = target_provider_name == "jev"
            if privacy_local_only and is_target_remote:
                raise ProviderError(
                    code=ErrorCode.UNAUTHORIZED_ACTION,
                    message=f"Task privacy constraint (local-only) conflicts with USER_LOCKED remote provider '{target_provider_name}'",
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                )

            # Probe locked provider; FAIL CLEANLY if not operational (no silent fallback!)
            prov_obj = self.get_provider(target_provider_name)
            if prov_obj is None:
                raise ProviderError(
                    code=ErrorCode.UNCONFIGURED,
                    message=f"Locked provider '{target_provider_name}' is not registered in broker",
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                )

            health = prov_obj.health_check()
            if not health.healthy:
                raise ProviderError(
                    code=health.status_code if health.status_code != ErrorCode.UNKNOWN else ErrorCode.SERVICE_UNAVAILABLE,
                    message=f"Locked provider '{target_provider_name}' is unhealthy ({health.message}). Silent fallback prohibited under USER_LOCKED.",
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                )

            t1 = time.perf_counter()
            outcome = self._map_outcome(target_provider_name)
            decision = BrokerDecision(
                selected_provider=target_provider_name,
                target_provider=target_provider_name,
                outcome=outcome,
                selection_mode=mode,
                fallback_occurred=False,
                fallback_reason=FallbackReason.NONE,
                broker_latency_ms=round((t1 - t0) * 1000, 3),
                is_local=not is_target_remote,
            )
            return prov_obj, decision

        # -------------------------------------------------------------------
        # Precedence Rule 2: USER_PREFERRED with Measurable Fallback
        # -------------------------------------------------------------------
        if mode == ProviderSelectionMode.USER_PREFERRED:
            # Task override can adjust preference if within allowlist
            if task_prov:
                if task_prov in allowed:
                    target_provider_name = task_prov
                else:
                    raise ProviderError(
                        code=ErrorCode.UNAUTHORIZED_ACTION,
                        message=f"Task override '{task_prov}' rejected: Provider is not in allowed_providers: {allowed}",
                        provider_id=self.provider_id,
                        model_id=self.model_id,
                    )

            target_obj = self.get_provider(target_provider_name)
            fallback_needed = False
            fallback_reason = FallbackReason.NONE
            fallback_details = None

            # Check A: Privacy / Offline constraint
            if privacy_local_only and target_provider_name == "jev":
                fallback_needed = True
                fallback_reason = FallbackReason.PRIVACY_RESTRICTION
                fallback_details = "Remote provider disallowed due to task privacy constraint"

            # Check B: Local RAM pressure
            elif not fallback_needed and target_provider_name.startswith("laya"):
                if is_ram_pressure_critical(threshold_mb=self.policy_config.ram_headroom_mb):
                    if "jev" in allowed:
                        jev_prov = self.get_provider("jev")
                        if jev_prov and jev_prov.is_configured:
                            fallback_needed = True
                            fallback_reason = FallbackReason.RAM_PRESSURE
                            fallback_details = f"System RAM below {self.policy_config.ram_headroom_mb}MB headroom"

            # Check C: Target provider health & configuration
            if not fallback_needed:
                if target_obj is None or not target_obj.is_configured:
                    fallback_needed = True
                    fallback_reason = FallbackReason.PROVIDER_UNCONFIGURED
                    fallback_details = f"Target provider '{target_provider_name}' is not configured"
                else:
                    health = target_obj.health_check()
                    if not health.healthy:
                        fallback_needed = True
                        fallback_reason = FallbackReason.PROVIDER_UNHEALTHY
                        fallback_details = f"Target provider '{target_provider_name}' health check failed: {health.message}"

            # If target is healthy and valid, use it directly
            if not fallback_needed and target_obj is not None:
                t1 = time.perf_counter()
                outcome = self._map_outcome(target_provider_name)
                decision = BrokerDecision(
                    selected_provider=target_provider_name,
                    target_provider=target_provider_name,
                    outcome=outcome,
                    selection_mode=mode,
                    fallback_occurred=False,
                    fallback_reason=FallbackReason.NONE,
                    broker_latency_ms=round((t1 - t0) * 1000, 3),
                    is_local=target_provider_name != "jev",
                )
                return target_obj, decision

            # Fallback path: search allowed alternatives
            candidate_names = [p for p in allowed if p != target_provider_name]
            if privacy_local_only:
                candidate_names = [p for p in candidate_names if p != "jev"]

            for alt_name in candidate_names:
                alt_obj = self.get_provider(alt_name)
                if alt_obj and alt_obj.is_configured:
                    alt_health = alt_obj.health_check()
                    if alt_health.healthy:
                        t1 = time.perf_counter()
                        outcome = self._map_outcome(alt_name)
                        decision = BrokerDecision(
                            selected_provider=alt_name,
                            target_provider=target_provider_name,
                            outcome=outcome,
                            selection_mode=mode,
                            fallback_occurred=True,
                            fallback_reason=fallback_reason,
                            fallback_details=fallback_details,
                            broker_latency_ms=round((t1 - t0) * 1000, 3),
                            is_local=alt_name != "jev",
                        )
                        return alt_obj, decision

            # If all allowed alternatives exhausted, fail
            raise ProviderError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Target provider '{target_provider_name}' failed ({fallback_reason}) and all allowed alternatives ({allowed}) are unavailable",
                provider_id=self.provider_id,
                model_id=self.model_id,
            )

        # -------------------------------------------------------------------
        # Precedence Rule 3: AUTO Mode (Optimizer inside Allowlist)
        # -------------------------------------------------------------------
        candidates = list(allowed)
        if privacy_local_only:
            candidates = [p for p in candidates if p != "jev"]

        # Filter by health & configuration
        viable_candidates = []
        for c_name in candidates:
            c_obj = self.get_provider(c_name)
            if c_obj and c_obj.is_configured:
                h = c_obj.health_check()
                if h.healthy:
                    viable_candidates.append((c_name, c_obj, h))

        if not viable_candidates:
            raise ProviderError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"AUTO provider selection failed: No healthy providers found among allowed: {candidates}",
                provider_id=self.provider_id,
                model_id=self.model_id,
            )

        # Selection heuristics:
        # If latency priority: pick fastest healthy provider
        # If RAM pressure critical: prefer remote healthy Jev if available
        # Default: default preference if healthy, otherwise top viable candidate
        selected_name = None
        selected_obj = None

        if is_ram_pressure_critical(threshold_mb=self.policy_config.ram_headroom_mb):
            for name, obj, _ in viable_candidates:
                if name == "jev":
                    selected_name = name
                    selected_obj = obj
                    break

        if selected_name is None and latency_priority:
            # Sort by latency ascending
            viable_candidates.sort(key=lambda item: item[2].latency_ms)
            selected_name, selected_obj, _ = viable_candidates[0]

        if selected_name is None:
            # Pick preferred if viable, else first viable
            for name, obj, _ in viable_candidates:
                if name == default_pref:
                    selected_name = name
                    selected_obj = obj
                    break
            if selected_name is None:
                selected_name, selected_obj, _ = viable_candidates[0]

        t1 = time.perf_counter()
        outcome = self._map_outcome(selected_name)
        fallback_occurred = selected_name != default_pref
        fallback_reason = FallbackReason.QUALITY_FLOOR_BREACH if fallback_occurred else FallbackReason.NONE

        decision = BrokerDecision(
            selected_provider=selected_name,
            target_provider=default_pref,
            outcome=outcome,
            selection_mode=mode,
            fallback_occurred=fallback_occurred,
            fallback_reason=fallback_reason,
            fallback_details="AUTO selection based on health, latency, and resource constraints",
            broker_latency_ms=round((t1 - t0) * 1000, 3),
            is_local=selected_name != "jev",
        )
        return selected_obj, decision

    def predict_signals(
        self,
        context: Dict[str, Any],
        questions: Dict[str, Any],
        task_override: Optional[TaskProviderOverride] = None,
    ) -> Dict[str, DecisionSignal]:
        """Dispatches to the active provider selected by policy and enriches signals with broker telemetry."""
        active_provider, decision = self.resolve_provider(task_override=task_override, context=context)
        signals = active_provider.predict_signals(context=context, questions=questions)

        # Inject broker telemetry into each decision signal metadata
        for sig in signals.values():
            sig.metadata["broker_decision"] = decision.model_dump()

        return signals

    def classify(
        self,
        prompt: str,
        criteria: Dict[str, str],
        instructions: str = "Classify target category:",
        task_override: Optional[TaskProviderOverride] = None,
    ) -> DecisionSignal:
        """Classifies a prompt using the policy-selected active provider."""
        questions = {
            "classification": {
                "type": "choice",
                "instructions": instructions,
                "criteria": criteria,
            }
        }
        res = self.predict_signals(
            context={"prompt": prompt},
            questions=questions,
            task_override=task_override,
        )
        return res["classification"]

    def score(
        self,
        prompt: str,
        criteria: str,
        task_override: Optional[TaskProviderOverride] = None,
    ) -> float:
        """Evaluates score using the policy-selected active provider."""
        res = self.classify(
            prompt=prompt,
            criteria={"match": criteria, "no_match": f"not {criteria}"},
            instructions="Determine whether prompt matches criteria:",
            task_override=task_override,
        )
        if res.probabilities and "match" in res.probabilities:
            return res.probabilities["match"]
        return res.confidence if res.value == "match" else max(0.0, 1.0 - res.confidence)

    def health_check(self) -> ProviderHealth:
        """Evaluates health across all allowed providers."""
        t0 = time.perf_counter()
        healthy_count = 0
        details = {}
        for p_name in self.policy_config.allowed_providers:
            prov = self.get_provider(p_name)
            if prov:
                h = prov.health_check()
                details[p_name] = {"healthy": h.healthy, "latency_ms": h.latency_ms, "message": h.message}
                if h.healthy:
                    healthy_count += 1
            else:
                details[p_name] = {"healthy": False, "message": "Not registered"}

        t1 = time.perf_counter()
        is_healthy = healthy_count > 0
        return ProviderHealth(
            provider_id=self.provider_id,
            model_id=self.model_id,
            healthy=is_healthy,
            status_code=ErrorCode.UNKNOWN if is_healthy else ErrorCode.SERVICE_UNAVAILABLE,
            latency_ms=round((t1 - t0) * 1000, 3),
            message=f"Broker healthy: {healthy_count}/{len(self.policy_config.allowed_providers)} providers operational",
            details=details,
        )

    def _map_outcome(self, provider_name: str) -> BrokerRoutingOutcome:
        """Maps provider identifier to categorical BrokerRoutingOutcome."""
        mapping = {
            "laya_english": BrokerRoutingOutcome.LAYA_ENGLISH,
            "laya_typed_decisions": BrokerRoutingOutcome.LAYA_TYPED_DECISIONS,
            "jev": BrokerRoutingOutcome.JEV,
        }
        return mapping.get(provider_name, BrokerRoutingOutcome.LAYA_ENGLISH)
