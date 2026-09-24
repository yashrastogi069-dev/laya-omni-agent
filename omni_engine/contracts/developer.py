"""Strongly typed developer and code supervision contracts.

Adheres strictly to AGENTS.md Prime Directive:
- Invariant 1: Deterministic Control, Probabilistic Reasoning
- Invariant 4: Strongly Typed Capability Contracts (BaseContractModel, extra="forbid")
- Invariant 6: Evidence-Based Completion (deterministic AST parsing, physical test exit codes)
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field
from omni_engine.contracts.base import BaseContractModel
from omni_engine.contracts.enums import VerificationStatus


class ConvergenceStatus(str, Enum):
    """Lifecycle convergence state of a supervised developer task."""
    CONVERGED = "converged"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    THRASHING_DETECTED = "thrashing_detected"
    TEST_TAMPERING_DETECTED = "test_tampering_detected"
    SYNTAX_ERROR = "syntax_error"
    TIMEOUT = "timeout"
    RULE_0_VIOLATION = "rule_0_violation"
    UNVERIFIED = "unverified"


class DevTaskSpec(BaseContractModel):
    """Specification of a software engineering task supervised by LAYA."""
    task_id: str = Field(..., description="Unique identifier for the developer task")
    repo_path: str = Field(..., description="Absolute or normalized path to the target git repository")
    task_prompt: str = Field(..., description="Instructions or bug description to resolve")
    target_files: List[str] = Field(default_factory=list, description="Explicit target source files if known")
    test_commands: List[str] = Field(default_factory=list, description="Test commands to execute for verification")
    allow_test_edits: bool = Field(default=False, description="Whether test files are allowed to be modified")
    max_iterations: int = Field(default=3, ge=1, le=5, description="Maximum edit-verify retry iterations")
    timeout_seconds: float = Field(default=120.0, ge=5.0, description="Overall wall-clock timeout budget")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary task context metadata")


class CodeVerificationReceipt(BaseContractModel):
    """Deterministic evidence receipt capturing code syntax, lint, and test execution."""
    syntax_valid: bool = Field(..., description="Whether all modified Python files passed AST parsing")
    syntax_errors: List[str] = Field(default_factory=list, description="Captured syntax error details if any")
    lint_passed: Optional[bool] = Field(default=None, description="Whether linters passed (None if unconfigured)")
    tests_passed: bool = Field(..., description="Whether verification tests exited with code 0")
    test_exit_code: int = Field(default=0, description="Process exit code of test runner")
    test_output: str = Field(default="", description="Captured stdout/stderr from test runner (truncated)")
    test_duration_ms: float = Field(default=0.0, description="Execution time of the test run in milliseconds")
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Physical verification status"
    )


class DevExecutionReceipt(BaseContractModel):
    """Top-level physical execution receipt for an autonomous developer task."""
    task_id: str = Field(..., description="ID of the completed task")
    repo_path: str = Field(..., description="Root repository path where task executed")
    exit_code: int = Field(default=0, description="Terminal exit code (0 = success)")
    modified_files: List[str] = Field(default_factory=list, description="Files modified during the task")
    git_diff: str = Field(default="", description="Captured git diff of all changes")
    git_head_before: Optional[str] = Field(default=None, description="Git commit hash prior to execution")
    iterations_count: int = Field(default=0, description="Number of edit-verify iterations executed")
    convergence_status: ConvergenceStatus = Field(
        default=ConvergenceStatus.UNVERIFIED,
        description="Terminal convergence state"
    )
    verification: CodeVerificationReceipt = Field(
        ...,
        description="Evidence-based code verification results"
    )
    duration_ms: float = Field(default=0.0, description="Total execution duration in milliseconds")
    status: str = Field(default="success", description="Overall execution status: success, failure, timeout")
    error: Optional[str] = Field(default=None, description="Human-readable error diagnostic if failed")


class DevActionResult(BaseContractModel):
    """Standard tool execution result envelope for developer capabilities."""
    action: str = Field(..., description="Executed developer action")
    task_id: Optional[str] = Field(default=None, description="Associated task ID")
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    receipt: Optional[DevExecutionReceipt] = Field(default=None, description="Detailed execution receipt")
    data: Dict[str, Any] = Field(default_factory=dict, description="Associated output payload")
    error: Optional[str] = Field(default=None, description="Error message if failed")
