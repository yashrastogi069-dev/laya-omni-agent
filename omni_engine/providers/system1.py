"""
omni_engine.providers.system1
=============================
System 1 Decision Engine Providers: Laya (Local ModernBERT) and Jev (TypeSafe Cloud).

Adheres to Prime Directive & Invariants:
- High-frequency bounded decisions (<35ms budget via batched forward pass)
- RAM-safe shared singleton for ModernBERT weights
- Bounded numerical sanitization (clamping [0.0, 1.0], NaN replacement)
- Explicit provenance and latency tracking
- Graceful non-crashing unconfigured state for optional Jev provider
"""

import gc
import math
import os
import threading
import time
import warnings
from typing import Any, Dict, List, Optional, Tuple

from omni_engine.contracts.enums import DecisionSignalType, ErrorCode
from omni_engine.contracts.decision import DecisionSignal
from .base import ProviderError, ProviderHealth, SystemOneProvider

# Global singleton lock and instance for local ModernBERT router to protect host RAM
_ROUTER_LOCK = threading.RLock()
_SHARED_ROUTER = None


def get_shared_laya_router(model_name: str = "english", preload: bool = False):
    """Retrieves or initializes the shared laya.Router instance with strict RAM protection."""
    global _SHARED_ROUTER
    with _ROUTER_LOCK:
        if _SHARED_ROUTER is None:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning, module=r".*laya.*")
                warnings.filterwarnings("ignore", message=r".*checkpoint ships temperatures outside.*")
                import laya
                _SHARED_ROUTER = laya.Router(max_loaded=1)
                if preload:
                    try:
                        _SHARED_ROUTER.preload(names=[model_name])
                    except Exception:
                        pass
        else:
            # Pre-eviction memory guard: if switching to an unloaded checkpoint, evict resident model
            if model_name not in _SHARED_ROUTER.loaded and _SHARED_ROUTER.loaded:
                _SHARED_ROUTER.unload()
                gc.collect()
            if preload and model_name not in _SHARED_ROUTER.loaded:
                try:
                    _SHARED_ROUTER.preload(names=[model_name])
                except Exception:
                    pass
    return _SHARED_ROUTER


def sanitize_float(val: Any) -> float:
    """Clamps float value to [0.0, 1.0] and replaces NaN/Inf with 0.0."""
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return max(0.0, min(1.0, f))
    except (ValueError, TypeError):
        return 0.0


def sanitize_probabilities(probs: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Sanitizes probability distribution dictionary ensuring all values in [0.0, 1.0]."""
    if not isinstance(probs, dict):
        return {}
    return {str(k): sanitize_float(v) for k, v in probs.items()}


def _extract_decision_data(ans: Any) -> Tuple[str, float, Dict[str, float]]:
    """Defensively extracts choice, confidence, and probabilities from polymorphic answer payloads."""
    if isinstance(ans, dict):
        choice = ans.get("choice")
        confidence = ans.get("confidence")
        probs = ans.get("probabilities") or ans.get("probs") or {}
    else:
        choice = getattr(ans, "choice", None)
        confidence = getattr(ans, "confidence", None)
        probs = getattr(ans, "probs", None) or getattr(ans, "probabilities", None) or {}

    choice_str = str(choice) if choice is not None else ""
    return choice_str, sanitize_float(confidence), sanitize_probabilities(probs)


class LayaProvider(SystemOneProvider):
    """Primary high-frequency System 1 decision provider using local ModernBERT-large."""

    def __init__(self, model_name: str = "english", preload: bool = False) -> None:
        valid_models = ["english", "multilingual", "typed-decisions"]
        if model_name not in valid_models:
            raise ValueError(f"Unknown Laya model '{model_name}'. Must be one of {valid_models}.")
        self.model_name = model_name
        self.provider_id = "laya"
        self.model_id = "ModernBERT-large" if model_name == "english" else f"ModernBERT-{model_name}"
        self.is_configured = True
        self._router = get_shared_laya_router(model_name=model_name, preload=preload)
        self.cold_start = True

    def predict_signals(
        self,
        context: Dict[str, Any],
        questions: Dict[str, Any],
    ) -> Dict[str, DecisionSignal]:
        """Dispatches multiple decision questions simultaneously in a single forward pass."""
        t0 = time.perf_counter()
        
        # Format questions for laya.Router if raw criteria dictionaries were passed
        formatted_q = {}
        for q_name, q_val in questions.items():
            if isinstance(q_val, dict) and "type" not in q_val and "criteria" in q_val:
                formatted_q[q_name] = {
                    "type": "choice",
                    "instructions": q_val.get("instructions", f"Classify {q_name}:"),
                    "criteria": q_val["criteria"],
                }
            else:
                formatted_q[q_name] = q_val

        # Process-wide lock protects host RAM and CPU scheduler against multi-thread thrashing
        with _ROUTER_LOCK:
            # Pre-eviction memory guard: Ensure victim model is unloaded before loading target
            if self.model_name not in self._router.loaded and self._router.loaded:
                self._router.unload()
                gc.collect()

            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=RuntimeWarning, module=r".*laya.*")
                    warnings.filterwarnings("ignore", message=r".*checkpoint ships temperatures outside.*")
                    raw_res = self._router.predict(
                        state=context,
                        questions=formatted_q,
                        model=self.model_name,
                    )
            except Exception as e:
                # If non-default model failed (e.g. offline download), attempt graceful fallback to english
                if self.model_name != "english":
                    try:
                        raw_res = self._router.predict(
                            state=context,
                            questions=formatted_q,
                            model="english",
                        )
                    except Exception as inner_e:
                        raise ProviderError(
                            code=ErrorCode.PROCESS_FAILED,
                            message=f"Laya forward pass failed (and fallback to english failed: {inner_e}): {e}",
                            details={"context": context, "questions": questions},
                            provider_id=self.provider_id,
                            model_id=self.model_id,
                        )
                else:
                    raise ProviderError(
                        code=ErrorCode.PROCESS_FAILED,
                        message=f"Laya forward pass failed: {e}",
                        details={"context": context, "questions": questions},
                        provider_id=self.provider_id,
                        model_id=self.model_id,
                    )

        t1 = time.perf_counter()
        latency_ms = round((t1 - t0) * 1000, 3)
        was_cold = self.cold_start
        self.cold_start = False

        answers = raw_res.answers if hasattr(raw_res, "answers") else (raw_res.get("answers", {}) if isinstance(raw_res, dict) else {})
        signals: Dict[str, DecisionSignal] = {}

        for q_name, decision in answers.items():
            sig_type_enum = DecisionSignalType.INTENT
            try:
                sig_type_enum = DecisionSignalType(q_name.upper())
            except ValueError:
                sig_type_enum = DecisionSignalType.INTENT

            choice_val, conf_val, probs_val = _extract_decision_data(decision)

            signal = DecisionSignal(
                signal_type=sig_type_enum,
                value=choice_val,
                confidence=conf_val,
                probabilities=probs_val,
                provider_id=self.provider_id,
                model_id=self.model_id,
                decision_schema_version="1.0.0",
                calibration_version="modernbert-large-temp-scaled-v1",
                latency_ms=latency_ms,
                metadata={"cold_start": was_cold, "question_name": q_name},
            )
            signals[q_name] = signal

        return signals

    def classify(
        self,
        prompt: str,
        criteria: Dict[str, str],
        instructions: str = "Classify target category:",
    ) -> DecisionSignal:
        """Classifies a prompt into one of the provided criteria keys."""
        questions = {
            "classification": {
                "type": "choice",
                "instructions": instructions,
                "criteria": criteria,
            }
        }
        res = self.predict_signals(context={"prompt": prompt}, questions=questions)
        return res["classification"]

    def score(
        self,
        prompt: str,
        criteria: str,
    ) -> float:
        """Evaluates relevance or probability score in [0.0, 1.0] for a single criterion."""
        res = self.classify(
            prompt=prompt,
            criteria={"match": criteria, "no_match": f"not {criteria}"},
            instructions="Determine whether prompt matches criteria:",
        )
        if res.probabilities and "match" in res.probabilities:
            return res.probabilities["match"]
        return res.confidence if res.value == "match" else max(0.0, 1.0 - res.confidence)

    def health_check(self) -> ProviderHealth:
        """Probes local ModernBERT engine health and measures ping latency."""
        t0 = time.perf_counter()
        try:
            test_res = self.classify(
                prompt="Health probe",
                criteria={"ok": "System healthy", "fail": "System failing"},
                instructions="Assess health status:",
            )
            t1 = time.perf_counter()
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=True,
                status_code=ErrorCode.UNKNOWN,
                latency_ms=round((t1 - t0) * 1000, 3),
                message="Local ModernBERT engine operational and responsive.",
                details={"probe_choice": test_res.value, "confidence": test_res.confidence},
            )
        except Exception as e:
            t1 = time.perf_counter()
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=False,
                status_code=ErrorCode.PROCESS_FAILED,
                latency_ms=round((t1 - t0) * 1000, 3),
                message=f"Local ModernBERT probe failed: {e}",
                details={"error": str(e)},
            )


class JevProvider(SystemOneProvider):
    """Optional System 1 provider using TypeSafe Cloud API (fallback/benchmark).
    
    Guarantees:
    - Never raises in __init__ if unconfigured.
    - Gracefully reports unconfigured state without crashing caller.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.provider_id = "jev"
        self.model_id = "jev-cloud-api"
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        self.is_configured = bool(self.api_key)
        self._client = None

        if self.is_configured:
            try:
                from typesafe_sdk import TypeSafeClient
                self._client = TypeSafeClient(api_key=self.api_key)
            except ImportError:
                self.is_configured = False
            except Exception:
                self.is_configured = False

    def predict_signals(
        self,
        context: Dict[str, Any],
        questions: Dict[str, Any],
    ) -> Dict[str, DecisionSignal]:
        """Dispatches to TypeSafe Jev Cloud API if configured."""
        if not self.is_configured or self._client is None:
            raise ProviderError(
                code=ErrorCode.UNCONFIGURED,
                message="TypeSafe Jev API key is not configured (TYPESAFE_API_KEY).",
                provider_id=self.provider_id,
                model_id=self.model_id,
            )

        t0 = time.perf_counter()
        try:
            from typesafe_sdk import Choice
            q_formatted = {}
            for q_name, q_val in questions.items():
                crit = q_val.get("criteria", {}) if isinstance(q_val, dict) else {}
                instr = q_val.get("instructions", "Classify:") if isinstance(q_val, dict) else "Classify:"
                q_formatted[q_name] = Choice(instructions=instr, criteria=crit)

            res = self._client.system_one(state=context, questions=q_formatted)
            t1 = time.perf_counter()
            latency_ms = round((t1 - t0) * 1000, 3)

            signals = {}
            for q_name, ans in res.answers.items():
                signals[q_name] = DecisionSignal(
                    signal_type=DecisionSignalType.INTENT,
                    value=str(ans.choice),
                    confidence=sanitize_float(getattr(ans, "confidence", 1.0)),
                    probabilities=sanitize_probabilities(getattr(ans, "probabilities", {})),
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                    decision_schema_version="1.0.0",
                    calibration_version="typesafe-cloud-v1",
                    latency_ms=latency_ms,
                )
            return signals

        except Exception as e:
            err_code = ErrorCode.NETWORK_ERROR
            msg = str(e)
            if "auth" in msg.lower() or "unauthorized" in msg.lower():
                err_code = ErrorCode.AUTH_REQUIRED
            elif "timeout" in msg.lower():
                err_code = ErrorCode.TIMEOUT
            elif "rate" in msg.lower():
                err_code = ErrorCode.RATE_LIMITED

            raise ProviderError(
                code=err_code,
                message=f"Jev API call failed: {e}",
                provider_id=self.provider_id,
                model_id=self.model_id,
            )

    def classify(
        self,
        prompt: str,
        criteria: Dict[str, str],
        instructions: str = "Classify target category:",
    ) -> DecisionSignal:
        questions = {"classification": {"criteria": criteria, "instructions": instructions}}
        res = self.predict_signals(context={"prompt": prompt}, questions=questions)
        return res["classification"]

    def score(
        self,
        prompt: str,
        criteria: str,
    ) -> float:
        """Raises ProviderError if unconfigured or evaluates score via Jev."""
        if not self.is_configured:
            raise ProviderError(
                code=ErrorCode.UNCONFIGURED,
                message="JevProvider is unconfigured. Set JEV_API_KEY.",
                provider_id=self.provider_id,
                model_id=self.model_id,
            )
        res = self.classify(prompt=prompt, criteria={"match": criteria, "no_match": f"not {criteria}"})
        return res.confidence if res.value == "match" else max(0.0, 1.0 - res.confidence)

    def health_check(self) -> ProviderHealth:
        if not self.is_configured:
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=False,
                status_code=ErrorCode.UNCONFIGURED,
                latency_ms=0.0,
                message="TypeSafe Jev Cloud API is unconfigured (TYPESAFE_API_KEY missing).",
            )
        try:
            t0 = time.perf_counter()
            test_res = self.classify("Health probe", {"ok": "Healthy", "fail": "Failing"})
            t1 = time.perf_counter()
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=True,
                status_code=ErrorCode.UNKNOWN,
                latency_ms=round((t1 - t0) * 1000, 3),
                message="TypeSafe Jev Cloud API is operational.",
                details={"choice": test_res.value},
            )
        except Exception as e:
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=False,
                status_code=ErrorCode.NETWORK_ERROR,
                latency_ms=0.0,
                message=f"TypeSafe Jev health probe failed: {e}",
            )
