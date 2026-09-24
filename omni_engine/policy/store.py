"""
omni_engine.policy.store
========================
Thread-safe, crash-resilient persistent storage for user-defined policy rules
and custom constraints.

Adheres to Prime Directive & Repository Invariants:
- Invariant 1: Deterministic Control — Persistent constraints survive process restarts.
- Reliability: Atomic file replacement (os.replace) and corruption quarantining.
- Thread Safety: Guarded with threading.RLock().
"""

import json
import os
import pathlib
import threading
import time
from typing import Dict, List, Optional

from omni_engine.contracts.enums import ActionClass
from omni_engine.contracts.policy import PolicyEffect, PolicyRule
from .rules import canonicalize_path


DEFAULT_POLICY_DIR = os.path.expanduser("~/.laya")
DEFAULT_POLICY_FILE = os.path.join(DEFAULT_POLICY_DIR, "user_policy.json")


class PolicyStore:
    """Manages persistent custom user-defined policy rules and resource constraints."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self.storage_path = storage_path or DEFAULT_POLICY_FILE
        self._lock = threading.RLock()
        self._rules: Dict[str, PolicyRule] = {}
        self._load()

    def _load(self) -> None:
        """Loads rules from storage with crash recovery and corruption quarantine."""
        with self._lock:
            if not os.path.exists(self.storage_path):
                self._rules = {}
                return

            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, list):
                    for item in data:
                        rule = PolicyRule.model_validate(item)
                        self._rules[rule.rule_id] = rule
                elif isinstance(data, dict) and "rules" in data:
                    for item in data["rules"]:
                        rule = PolicyRule.model_validate(item)
                        self._rules[rule.rule_id] = rule
                else:
                    self._rules = {}
            except Exception as e:
                # Quarantine corrupted file
                corrupt_path = f"{self.storage_path}.corrupt.{int(time.time())}"
                try:
                    os.replace(self.storage_path, corrupt_path)
                except Exception:
                    pass
                self._rules = {}

    def _persist(self) -> None:
        """Atomically persists active rules to disk via temporary file swap."""
        with self._lock:
            target_dir = os.path.dirname(os.path.abspath(self.storage_path))
            os.makedirs(target_dir, exist_ok=True)

            tmp_path = f"{self.storage_path}.tmp.{os.getpid()}"
            payload = [rule.model_dump() for rule in self._rules.values()]

            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())

                os.replace(tmp_path, self.storage_path)
            except Exception:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                raise

    def add_rule(self, rule: PolicyRule) -> None:
        """Adds or updates a custom policy rule and persists it."""
        with self._lock:
            self._rules[rule.rule_id] = rule
            self._persist()

    def remove_rule(self, rule_id: str) -> bool:
        """Removes a custom rule by rule_id. Returns True if removed."""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                self._persist()
                return True
            return False

    def get_rule(self, rule_id: str) -> Optional[PolicyRule]:
        """Retrieves a rule by ID."""
        with self._lock:
            return self._rules.get(rule_id)

    def get_active_rules(self) -> List[PolicyRule]:
        """Returns all currently active rules sorted by priority (lowest first)."""
        with self._lock:
            active = [r for r in self._rules.values() if r.is_active]
            return sorted(active, key=lambda r: r.priority)

    def clear_custom_rules(self) -> None:
        """Removes all custom rules and updates persistent storage."""
        with self._lock:
            self._rules.clear()
            self._persist()

    def block_domain(self, domain: str, reason: str = "") -> PolicyRule:
        """Helper to create a persistent domain-blocking rule."""
        domain_clean = domain.strip().lower()
        rule_id = f"block_domain_{domain_clean.replace('.', '_')}"
        rule = PolicyRule(
            rule_id=rule_id,
            name=f"Block domain: {domain_clean}",
            description=reason or f"User blocked network requests to {domain_clean}",
            effect=PolicyEffect.DENY,
            action_classes=[ActionClass.READ_ONLY, ActionClass.EXTERNAL_CREATE, ActionClass.SYSTEM_ACTION],
            target_domains=[domain_clean],
            priority=50,
            is_active=True,
        )
        self.add_rule(rule)
        return rule

    def unblock_domain(self, domain: str) -> bool:
        """Helper to remove a domain-blocking rule."""
        domain_clean = domain.strip().lower()
        rule_id = f"block_domain_{domain_clean.replace('.', '_')}"
        return self.remove_rule(rule_id)

    def block_path(self, path: str, reason: str = "") -> PolicyRule:
        """Helper to create a persistent path-blocking rule."""
        canon = canonicalize_path(path)
        path_slug = canon.replace("\\", "_").replace(":", "_").replace("/", "_").strip("_")
        rule_id = f"block_path_{path_slug}"
        rule = PolicyRule(
            rule_id=rule_id,
            name=f"Block path: {path}",
            description=reason or f"User blocked file operations targeting {path}",
            effect=PolicyEffect.DENY,
            action_classes=[
                ActionClass.READ_ONLY,
                ActionClass.LOCAL_CREATE,
                ActionClass.LOCAL_UPDATE,
                ActionClass.LOCAL_DELETE,
                ActionClass.SYSTEM_ACTION,
            ],
            target_paths=[canon],
            priority=50,
            is_active=True,
        )
        self.add_rule(rule)
        return rule

    def unblock_path(self, path: str) -> bool:
        """Helper to remove a path-blocking rule."""
        canon = canonicalize_path(path)
        path_slug = canon.replace("\\", "_").replace(":", "_").replace("/", "_").strip("_")
        rule_id = f"block_path_{path_slug}"
        return self.remove_rule(rule_id)
