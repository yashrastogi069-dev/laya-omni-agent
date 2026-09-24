"""
omni_engine.providers.system1
=============================
System 1 Decision Engine Providers: Laya (Local ModernBERT) and Jev (TypeSafe Cloud).

Adheres to Prime Directive & Repository Invariants:
- High-frequency bounded decisions (<35ms budget on GPU, CPU-bounded throughput)
- Strict Two-Level Hierarchical Locking:
    Level 1 (Outer): _MODEL_LIFECYCLE_LOCK (RLock) protecting model instantiation, swaps, and residency
    Level 2 (Inner): _INFERENCE_SEMAPHORE (Semaphore) controlling concurrent forward passes
    Hard Rule: No thread holding _INFERENCE_SEMAPHORE may ever acquire _MODEL_LIFECYCLE_LOCK.
- Strict English-Only Scope: Only "english" and "typed-decisions" checkpoints permitted.
- Host RAM Protection: Debounced memory pressure checks and exclusive permit drain on swaps.
- Bounded numerical sanitization (clamping [0.0, 1.0], NaN replacement).
- Explicit provenance, latency, and queue wait tracking.
- Graceful non-crashing unconfigured state for optional Jev provider.
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

# Allowed model families strictly scoped to English
VALID_LOCAL_MODELS: Tuple[str, ...] = ("english", "typed-decisions")

# Level 1 Lock: Protects model lifecycle (creation, preloading, eviction, residency metadata)
_MODEL_LIFECYCLE_LOCK = threading.RLock()
# Backward-compatibility alias
_ROUTER_LOCK = _MODEL_LIFECYCLE_LOCK

# Level 2 Lock: Controls maximum concurrent forward passes
_LOCAL_LAYA_MAX_CONCURRENCY = int(os.environ.get("LOCAL_LAYA_MAX_CONCURRENCY", "1"))
_INFERENCE_SEMAPHORE = threading.Semaphore(_LOCAL_LAYA_MAX_CONCURRENCY)

_SHARED_ROUTER = None

# Timestamp history of memory threshold breaches for debouncing
_RAM_BREACH_TIMESTAMPS: List[float] = []
_RAM_LOCK = threading.Lock()


def get_laya_concurrency() -> int:
    """Returns the current maximum allowed local inference concurrency."""
    return _LOCAL_LAYA_MAX_CONCURRENCY


def set_laya_concurrency(concurrency: int) -> None:
    """Dynamically updates the local inference concurrency semaphore."""
    global _LOCAL_LAYA_MAX_CONCURRENCY, _INFERENCE_SEMAPHORE
    if concurrency < 1:
        raise ValueError("Concurrency must be at least 1")
    with _MODEL_LIFECYCLE_LOCK:
        # Drain existing permits before replacing semaphore
        _drain_inference_permits()
        _LOCAL_LAYA_MAX_CONCURRENCY = concurrency
        _INFERENCE_SEMAPHORE = threading.Semaphore(concurrency)


def _drain_inference_permits(timeout: float = 10.0) -> int:
    """Drains all semaphore permits to ensure zero active inferences during model swap/eviction."""
    acquired = 0
    t0 = time.perf_counter()
    for _ in range(_LOCAL_LAYA_MAX_CONCURRENCY):
        remaining = max(0.1, timeout - (time.perf_counter() - t0))
        if _INFERENCE_SEMAPHORE.acquire(timeout=remaining):
            acquired += 1
        else:
            # Rollback any acquired permits if timeout hit
            for _ in range(acquired):
                _INFERENCE_SEMAPHORE.release()
            raise TimeoutError(f"Failed to drain all {_LOCAL_LAYA_MAX_CONCURRENCY} inference permits within {timeout}s")
    return acquired


def _restore_inference_permits(count: int) -> None:
    """Restores previously drained inference semaphore permits."""
    for _ in range(count):
        _INFERENCE_SEMAPHORE.release()


def get_available_ram_mb() -> float:
    """Inspects available host RAM in megabytes using psutil with Windows API fallback."""
    # Try psutil first
    try:
        import psutil
        return float(psutil.virtual_memory().available) / (1024 * 1024)
    except Exception:
        pass

    # Fallback to Windows GlobalMemoryStatusEx via ctypes
    try:
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return float(stat.ullAvailPhys) / (1024 * 1024)
    except Exception:
        pass

    # Safe fallback if both telemetry sources fail: never evict on telemetry failure
    return float("inf")


def is_ram_pressure_critical(
    threshold_mb: float = 500.0,
    required_consecutive_breaches: int = 3,
    min_duration_seconds: float = 5.0,
) -> bool:
    """Debounced memory pressure check requiring consecutive breaches over time to prevent thrashing."""
    current_free_mb = get_available_ram_mb()
    now = time.perf_counter()

    with _RAM_LOCK:
        if current_free_mb < threshold_mb:
            _RAM_BREACH_TIMESTAMPS.append(now)
            # Prune breaches older than 30 seconds
            cutoff = now - 30.0
            while _RAM_BREACH_TIMESTAMPS and _RAM_BREACH_TIMESTAMPS[0] < cutoff:
                _RAM_BREACH_TIMESTAMPS.pop(0)

            if len(_RAM_BREACH_TIMESTAMPS) >= required_consecutive_breaches:
                span = _RAM_BREACH_TIMESTAMPS[-1] - _RAM_BREACH_TIMESTAMPS[0]
                if span >= min_duration_seconds:
                    return True
        else:
            # Reset on healthy sample
            _RAM_BREACH_TIMESTAMPS.clear()

        return False


def evict_laya_model_if_idle(reason: str = "ram_pressure") -> bool:
    """Evicts resident ModernBERT model only if zero inferences are running."""
    global _SHARED_ROUTER
    with _MODEL_LIFECYCLE_LOCK:
        if _SHARED_ROUTER is None or not _SHARED_ROUTER.loaded:
            return False

        # Attempt non-blocking permit drain to verify system is completely idle
        drained = 0
        try:
            for _ in range(_LOCAL_LAYA_MAX_CONCURRENCY):
                if _INFERENCE_SEMAPHORE.acquire(blocking=False):
                    drained += 1
                else:
                    return False  # Active inference in flight; do not evict

            # System is completely idle; safe to evict
            _SHARED_ROUTER.unload()
            gc.collect()
            return True
        finally:
            _restore_inference_permits(drained)


def get_shared_laya_router(model_name: str = "english", preload: bool = False):
    """Retrieves or initializes the shared laya.Router instance with strict RAM protection and English-only scoping."""
    global _SHARED_ROUTER
    if model_name not in VALID_LOCAL_MODELS:
        raise ValueError(
            f"Model '{model_name}' forbidden. Strict English-only invariant enforced. Allowed: {VALID_LOCAL_MODELS}"
        )

    with _MODEL_LIFECYCLE_LOCK:
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
            # Model swap with exclusive inference drain
            if model_name not in _SHARED_ROUTER.loaded and _SHARED_ROUTER.loaded:
                permits = _drain_inference_permits(timeout=10.0)
                try:
                    _SHARED_ROUTER.unload()
                    gc.collect()
                    if preload:
                        _SHARED_ROUTER.preload(names=[model_name])
                finally:
                    _restore_inference_permits(permits)
            elif preload and model_name not in _SHARED_ROUTER.loaded:
                permits = _drain_inference_permits(timeout=10.0)
                try:
                    _SHARED_ROUTER.preload(names=[model_name])
                finally:
                    _restore_inference_permits(permits)

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

    def __init__(
        self,
        model_name: str = "english",
        preload: bool = False,
        queue_timeout_seconds: float = 5.0,
    ) -> None:
        if model_name not in VALID_LOCAL_MODELS:
            raise ValueError(
                f"Model '{model_name}' forbidden. Strict English-only invariant enforced. Allowed: {VALID_LOCAL_MODELS}"
            )
        self.model_name = model_name
        self.provider_id = "laya"
        self.model_id = "ModernBERT-large" if model_name == "english" else f"ModernBERT-{model_name}"
        self.is_configured = True
        self.queue_timeout_seconds = queue_timeout_seconds
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

        # Level 1 check: Pre-validate model residency before entering inference semaphore
        if self.model_name not in self._router.loaded:
            with _MODEL_LIFECYCLE_LOCK:
                if self.model_name not in self._router.loaded:
                    permits = _drain_inference_permits(timeout=10.0)
                    try:
                        if self._router.loaded:
                            self._router.unload()
                            gc.collect()
                        self._router.preload(names=[self.model_name])
                    finally:
                        _restore_inference_permits(permits)

        # Level 2 check: Acquire inference semaphore with bounded queue timeout
        wait_t0 = time.perf_counter()
        acquired = _INFERENCE_SEMAPHORE.acquire(timeout=self.queue_timeout_seconds)
        wait_t1 = time.perf_counter()
        queue_wait_ms = round((wait_t1 - wait_t0) * 1000, 3)

        if not acquired:
            raise ProviderError(
                code=ErrorCode.TIMEOUT,
                message=f"Laya inference queue timeout ({self.queue_timeout_seconds}s) exceeded under concurrency={_LOCAL_LAYA_MAX_CONCURRENCY}",
                details={"context": context, "queue_wait_ms": queue_wait_ms},
                provider_id=self.provider_id,
                model_id=self.model_id,
            )

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
            # Fallback to english if non-default specialized model fails
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
                        message=f"Laya forward pass failed (fallback to english failed: {inner_e}): {e}",
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
        finally:
            _INFERENCE_SEMAPHORE.release()

        t1 = time.perf_counter()
        latency_ms = round((t1 - t0) * 1000, 3)
        was_cold = self.cold_start
        self.cold_start = False

        answers = (
            raw_res.answers
            if hasattr(raw_res, "answers")
            else (raw_res.get("answers", {}) if isinstance(raw_res, dict) else {})
        )
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
                metadata={
                    "cold_start": was_cold,
                    "question_name": q_name,
                    "queue_wait_ms": queue_wait_ms,
                },
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
                message="JevProvider is unconfigured. Set TYPESAFE_API_KEY.",
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
