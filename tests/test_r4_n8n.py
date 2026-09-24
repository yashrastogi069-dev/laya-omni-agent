"""Comprehensive Unit & Integration Test Suite for Phase R4: n8n Automation Engine.

Tests:
1. Typed Contracts & Schemas (Invariant 4)
2. Secret Scrubber & Credential Isolation (REQ-BLOCK-3)
3. Graph Validation, Cycles & In-Degree Invariants (REQ-BLOCK-2)
4. Draft-Test-Validate Lifecycle & Gate Triad (REQ-BLOCK-1)
5. Bounded Polling, Backoff & 'Waiting' State Detection (REQ-BLOCK-4)
6. PolicyEngine RCE Defense & Stage 0 Forbidden Commands (REQ-BLOCK-5)
7. Substrate Integration & Capability Registry Invariant (REQ-BLOCK-6)
8. 100% Offline Test Isolation via MockN8nTransport (REQ-BLOCK-7)
"""

import unittest
from pydantic import ValidationError

from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    VerificationStatus,
)
from omni_engine.contracts.policy import PolicyEffect
from omni_engine.contracts.n8n import (
    N8nTriggerType,
    N8nCredentialReference,
    N8nNode,
    N8nWorkflowSummary,
    N8nWorkflowDetail,
    N8nWorkflowValidationResult,
    N8nExecutionReceipt,
    N8nActionResult,
)
from omni_engine.automation.scrubber import SecretScrubber
from omni_engine.automation.validator import N8nWorkflowValidator
from omni_engine.automation.transport import MockN8nTransport
from omni_engine.automation.client import N8nClient
from omni_engine.automation.engine import N8nAutomationEngine
from omni_engine.policy.engine import PolicyEngine
from omni_engine.arguments.resolver import ArgumentResolver
from omni_engine.capabilities.definitions import (
    CANONICAL_SPECS,
    N8N_LIST_WORKFLOWS_SPEC,
    N8N_GET_WORKFLOW_SPEC,
    N8N_VALIDATE_WORKFLOW_SPEC,
    N8N_CREATE_WORKFLOW_SPEC,
    N8N_ACTIVATE_WORKFLOW_SPEC,
    N8N_TRIGGER_WORKFLOW_SPEC,
    N8N_GET_EXECUTION_STATUS_SPEC,
    build_canonical_registry,
    build_real_capability_registry,
)


class TestR4N8nContracts(unittest.TestCase):
    """Verifies strongly typed contracts and schema boundaries."""

    def test_credential_reference_forbids_extra_plaintext_keys(self):
        """REQ-BLOCK-3: Opaque credential references forbid inline secret tokens."""
        valid_ref = N8nCredentialReference(id="cred_openai_123", name="My OpenAI Vault")
        self.assertEqual(valid_ref.id, "cred_openai_123")

        with self.assertRaises(ValidationError):
            N8nCredentialReference(id="cred_1", apiKey="sk-123456789012345678901234")  # type: ignore

    def test_workflow_detail_deterministic_hash(self):
        """Workflow hash is invariant to node order but sensitive to topology/parameters."""
        n1 = N8nNode(id="1", name="Webhook", type="n8n-nodes-base.webhook")
        n2 = N8nNode(id="2", name="Code", type="n8n-nodes-base.code")
        conns = {"Webhook": {"main": [[{"node": "Code", "type": "main", "index": 0}]]}}

        wf_a = N8nWorkflowDetail(workflow_id="wf_1", name="Test Flow", nodes=[n1, n2], connections=conns)
        wf_b = N8nWorkflowDetail(workflow_id="wf_1", name="Test Flow", nodes=[n2, n1], connections=conns)

        self.assertEqual(wf_a.compute_hash(), wf_b.compute_hash())

        # Mutating a parameter changes the hash
        n2_mutated = N8nNode(id="2", name="Code", type="n8n-nodes-base.code", parameters={"jsCode": "return [];"})
        wf_c = N8nWorkflowDetail(workflow_id="wf_1", name="Test Flow", nodes=[n1, n2_mutated], connections=conns)
        self.assertNotEqual(wf_a.compute_hash(), wf_c.compute_hash())


class TestR4SecretScrubber(unittest.TestCase):
    """Verifies regex pattern detection, header scrubbing, and expression preservation."""

    def test_scrub_standard_tokens(self):
        sample = "Here is my OpenAI key sk-proj-1234567890abcdef12345678 and GitHub ghp_1234567890abcdef1234567890abcdef1234."
        scrubbed = SecretScrubber.scrub_text(sample)
        self.assertNotIn("sk-proj-", scrubbed)
        self.assertNotIn("ghp_", scrubbed)
        self.assertIn("[REDACTED_SECRET]", scrubbed)

    def test_scrub_headers(self):
        headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz",
            "X-N8N-API-KEY": "n8n_sec_1234567890123456",
            "User-Agent": "LAYA-Agent",
        }
        sanitized = SecretScrubber.scrub_headers(headers)
        self.assertEqual(sanitized["Authorization"], "[REDACTED_HEADER]")
        self.assertEqual(sanitized["X-N8N-API-KEY"], "[REDACTED_HEADER]")
        self.assertEqual(sanitized["User-Agent"], "LAYA-Agent")

    def test_preserve_n8n_expressions(self):
        """n8n expressions accessing $json.token should not be mutilated."""
        expr = "={{ $json.token }}"
        scrubbed = SecretScrubber.scrub_text(expr)
        self.assertEqual(scrubbed, expr)

    def test_contains_secret_detection(self):
        self.assertTrue(SecretScrubber.contains_secret({"auth": "Bearer secret_token_1234567"}))
        self.assertTrue(SecretScrubber.contains_secret("My token is ghp_1234567890abcdef1234567890abcdef1234"))
        self.assertFalse(SecretScrubber.contains_secret({"name": "Standard Node", "count": 42}))


class TestR4WorkflowValidator(unittest.TestCase):
    """Verifies graph validation, cycle detection, in-degree constraints, and security scans."""

    def test_valid_dag_passes(self):
        wf = N8nWorkflowDetail(
            workflow_id="wf_clean",
            name="Clean Workflow",
            nodes=[
                N8nNode(id="n1", name="Webhook", type="n8n-nodes-base.webhook"),
                N8nNode(id="n2", name="Transform", type="n8n-nodes-base.set"),
                N8nNode(id="n3", name="Output", type="n8n-nodes-base.httpRequest"),
            ],
            connections={
                "Webhook": {"main": [[{"node": "Transform", "type": "main", "index": 0}]]},
                "Transform": {"main": [[{"node": "Output", "type": "main", "index": 0}]]},
            },
        )
        res = N8nWorkflowValidator.validate(wf)
        self.assertTrue(res.is_valid)
        self.assertFalse(res.has_cycles)
        self.assertEqual(len(res.errors), 0)
        self.assertEqual(res.trigger_nodes, ["Webhook"])

    def test_self_loop_rejected(self):
        wf = N8nWorkflowDetail(
            workflow_id="wf_loop",
            name="Self Loop",
            nodes=[
                N8nNode(id="n1", name="Webhook", type="n8n-nodes-base.webhook"),
            ],
            connections={
                "Webhook": {"main": [[{"node": "Webhook", "type": "main", "index": 0}]]},
            },
        )
        res = N8nWorkflowValidator.validate(wf)
        self.assertFalse(res.is_valid)
        self.assertTrue(res.has_cycles)
        self.assertTrue(any("Self-loop" in e for e in res.errors))

    def test_multi_node_cycle_rejected(self):
        wf = N8nWorkflowDetail(
            workflow_id="wf_cycle",
            name="Cycle Flow",
            nodes=[
                N8nNode(id="n1", name="Webhook", type="n8n-nodes-base.webhook"),
                N8nNode(id="n2", name="NodeA", type="n8n-nodes-base.set"),
                N8nNode(id="n3", name="NodeB", type="n8n-nodes-base.set"),
            ],
            connections={
                "Webhook": {"main": [[{"node": "NodeA", "type": "main", "index": 0}]]},
                "NodeA": {"main": [[{"node": "NodeB", "type": "main", "index": 0}]]},
                "NodeB": {"main": [[{"node": "NodeA", "type": "main", "index": 0}]]},
            },
        )
        res = N8nWorkflowValidator.validate(wf)
        self.assertFalse(res.is_valid)
        self.assertTrue(res.has_cycles)
        self.assertTrue(any("Circular dependency" in e for e in res.errors))

    def test_dangling_connection_rejected(self):
        wf = N8nWorkflowDetail(
            workflow_id="wf_dangling",
            name="Dangling Node",
            nodes=[
                N8nNode(id="n1", name="Webhook", type="n8n-nodes-base.webhook"),
            ],
            connections={
                "Webhook": {"main": [[{"node": "NonExistentNode", "type": "main", "index": 0}]]},
            },
        )
        res = N8nWorkflowValidator.validate(wf)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Dangling connection" in e for e in res.errors))

    def test_trigger_in_degree_violation_rejected(self):
        """Trigger node cannot have incoming edges."""
        wf = N8nWorkflowDetail(
            workflow_id="wf_trig_in",
            name="Trigger In Degree",
            nodes=[
                N8nNode(id="n1", name="Webhook", type="n8n-nodes-base.webhook"),
                N8nNode(id="n2", name="SetNode", type="n8n-nodes-base.set"),
            ],
            connections={
                "SetNode": {"main": [[{"node": "Webhook", "type": "main", "index": 0}]]},
            },
        )
        res = N8nWorkflowValidator.validate(wf)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Trigger node 'Webhook' has incoming connections" in e for e in res.errors))

    def test_zero_trigger_nodes_rejected(self):
        wf = N8nWorkflowDetail(
            workflow_id="wf_no_trig",
            name="No Triggers",
            nodes=[
                N8nNode(id="n1", name="SetNode", type="n8n-nodes-base.set"),
            ],
            connections={},
        )
        res = N8nWorkflowValidator.validate(wf)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("contains no trigger" in e for e in res.errors))

    def test_plaintext_secret_in_parameters_rejected(self):
        wf = N8nWorkflowDetail(
            workflow_id="wf_sec",
            name="Secret Flow",
            nodes=[
                N8nNode(id="n1", name="Webhook", type="n8n-nodes-base.webhook"),
                N8nNode(
                    id="n2",
                    name="HttpReq",
                    type="n8n-nodes-base.httpRequest",
                    parameters={"authHeader": "Bearer sk-proj-123456789012345678901234"},
                ),
            ],
            connections={
                "Webhook": {"main": [[{"node": "HttpReq", "type": "main", "index": 0}]]},
            },
        )
        res = N8nWorkflowValidator.validate(wf)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("contains plaintext secrets" in e for e in res.errors))


class TestR4LifecycleAndGateTriad(unittest.TestCase):
    """Verifies Draft -> Validate -> Test -> Activate lifecycle and Gate Triad."""

    def setUp(self):
        self.transport = MockN8nTransport()
        self.client = N8nClient(self.transport)
        # Set zero sleep for test speed
        self.engine = N8nAutomationEngine(self.client, poll_interval=0.0001, sleep_fn=lambda s: None)

    def test_create_workflow_strictly_draft_mode(self):
        """REQ-BLOCK-1: Created workflows are always inactive (active=False)."""
        nodes = [
            {"id": "n1", "name": "Webhook", "type": "n8n-nodes-base.webhook"},
            {"id": "n2", "name": "SetNode", "type": "n8n-nodes-base.set"},
        ]
        connections = {"Webhook": {"main": [[{"node": "SetNode", "type": "main", "index": 0}]]}}

        res = self.engine.create_workflow(name="New Draft", nodes=nodes, connections=connections)
        self.assertTrue(res.success)
        self.assertFalse(res.data["workflow"]["active"])
        self.assertEqual(res.data["active"], False)

    def test_activation_blocked_by_gate_1_if_invalid_dag(self):
        """Gate 1: Structural validation failure blocks activation."""
        wf_id = self.transport.add_mock_workflow({
            "name": "Invalid Flow",
            "active": False,
            "nodes": [{"id": "n1", "name": "SetNode", "type": "n8n-nodes-base.set"}],
            "connections": {},
        })
        res = self.engine.activate_workflow(wf_id)
        self.assertFalse(res.success)
        self.assertIn("Gate 1 (Structural Validation)", res.error)

    def test_activation_blocked_by_gate_2_if_not_tested(self):
        """Gate 2: Workflow cannot be activated without a verified test run receipt."""
        wf_id = self.transport.add_mock_workflow({
            "name": "Untested Flow",
            "active": False,
            "nodes": [
                {"id": "n1", "name": "Webhook", "type": "n8n-nodes-base.webhook"},
                {"id": "n2", "name": "SetNode", "type": "n8n-nodes-base.set"},
            ],
            "connections": {"Webhook": {"main": [[{"node": "SetNode", "type": "main", "index": 0}]]}},
        })
        res = self.engine.activate_workflow(wf_id)
        self.assertFalse(res.success)
        self.assertIn("Gate 2 (Test Execution)", res.error)

    def test_full_successful_draft_test_activate_lifecycle(self):
        """Full lifecycle: create draft -> test workflow -> activate under Gate Triad."""
        # 1. Create draft
        nodes = [
            {"id": "n1", "name": "Webhook", "type": "n8n-nodes-base.webhook"},
            {"id": "n2", "name": "Output", "type": "n8n-nodes-base.set"},
        ]
        connections = {"Webhook": {"main": [[{"node": "Output", "type": "main", "index": 0}]]}}
        create_res = self.engine.create_workflow(name="Production Flow", nodes=nodes, connections=connections)
        self.assertTrue(create_res.success)
        wf_id = create_res.workflow_id

        # 2. Test workflow
        test_res = self.engine.test_workflow(wf_id, test_payload={"msg": "hello"})
        self.assertTrue(test_res.success)
        self.assertEqual(test_res.verification_status, VerificationStatus.VERIFIED_SUCCESS)
        self.assertTrue(test_res.data.get("passed_test_gate"))

        # 3. Activate workflow (Gate Triad passes)
        act_res = self.engine.activate_workflow(wf_id)
        self.assertTrue(act_res.success)
        self.assertEqual(act_res.verification_status, VerificationStatus.VERIFIED_SUCCESS)
        self.assertTrue(act_res.data["active"])

        # Check server state
        self.assertTrue(self.transport.workflows[wf_id]["active"])


class TestR4ExecutionPolling(unittest.TestCase):
    """Verifies polling transitions, waiting state breakouts, and timeouts."""

    def setUp(self):
        self.transport = MockN8nTransport()
        self.client = N8nClient(self.transport)
        self.engine = N8nAutomationEngine(self.client, poll_interval=0.0001, sleep_fn=lambda s: None)

    def test_polling_state_transition_to_success(self):
        wf_id = self.transport.add_mock_workflow({"name": "Flow", "active": True, "nodes": [], "connections": {}})
        # Simulate state transition: running -> running -> success
        self.transport.execution_state_sequence["exec_100"] = ["running", "running", "success"]

        receipt = self.engine.trigger_and_wait(wf_id)
        self.assertEqual(receipt.status, "success")
        self.assertEqual(receipt.verification_status, VerificationStatus.VERIFIED_SUCCESS)
        self.assertIsNotNone(receipt.duration_ms)

    def test_waiting_state_breakout_aborts_wait_stall(self):
        """REQ-BLOCK-4: 'waiting' status aborts polling immediately to prevent freezing."""
        wf_id = self.transport.add_mock_workflow({"name": "Flow", "active": True, "nodes": [], "connections": {}})
        self.transport.execution_state_sequence["exec_100"] = ["waiting"]

        receipt = self.engine.trigger_and_wait(wf_id)
        self.assertEqual(receipt.status, "waiting")
        self.assertIn("waiting state", receipt.error_message)

    def test_polling_timeout_bounded(self):
        wf_id = self.transport.add_mock_workflow({"name": "Flow", "active": True, "nodes": [], "connections": {}})
        # Never completes
        self.transport.execution_state_sequence["exec_100"] = ["running"] * 50

        # Execute with tiny timeout
        receipt = self.engine.trigger_and_wait(wf_id, timeout_seconds=0.01)
        self.assertEqual(receipt.status, "timeout")
        self.assertIn("timed out", receipt.error_message)


class TestR4PolicyRceDefense(unittest.TestCase):
    """Verifies PolicyEngine Stage 0 and risk assessment on high-risk n8n nodes."""

    def setUp(self):
        self.policy = PolicyEngine()

    def test_stage_0_blocks_execute_command_with_forbidden_git_wipe(self):
        """REQ-BLOCK-5: n8n executeCommand with 'git reset --hard' is unconditionally denied."""
        nodes = [
            {
                "id": "1",
                "name": "BadShellNode",
                "type": "n8n-nodes-base.executeCommand",
                "parameters": {"command": "git reset --hard HEAD~1"},
            }
        ]
        decision = self.policy.evaluate(
            capability=N8N_CREATE_WORKFLOW_SPEC,
            arguments={"name": "Malicious Flow", "nodes": nodes, "connections": {}},
            user_confirmed=True,  # Invariant: user_confirmed is strictly ignored for Rule-0!
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.effect, PolicyEffect.DENY)
        self.assertIn("RULE_0_FORBIDDEN_OPERATIONS", decision.matched_rules)

    def test_high_risk_node_escalates_risk_and_blast_radius(self):
        """n8n nodes executing code or shell commands are classified as LOCAL_SYSTEM or SECURITY_CRITICAL."""
        nodes = [
            {
                "id": "1",
                "name": "CustomCode",
                "type": "n8n-nodes-base.code",
                "parameters": {"jsCode": "console.log('hello');"},
            }
        ]
        assessment = self.policy.assess_action(
            spec=N8N_CREATE_WORKFLOW_SPEC,
            arguments={"name": "Script Flow", "nodes": nodes, "connections": {}},
        )
        self.assertIn(assessment.blast_radius, ("LOCAL_SYSTEM", "SECURITY_CRITICAL"))
        self.assertIn("n8n:n8n-nodes-base.code", assessment.sensitive_targets)
        self.assertGreaterEqual(assessment.risk_score, 0.70)


class TestR4SubstrateIntegration(unittest.TestCase):
    """Verifies capability registration, argument extraction, and canonical registry invariants."""

    def setUp(self):
        self.resolver = ArgumentResolver()

    def test_canonical_registry_invariant_preserved(self):
        """Invariant: Canonical registry strictly retains exactly 23 source tools."""
        can_reg = build_canonical_registry()
        self.assertEqual(can_reg.count(), 23)
        self.assertEqual(len(CANONICAL_SPECS), 23)

    def test_real_registry_includes_all_n8n_capabilities(self):
        """Real registry registers all n8n capabilities and dotless aliases."""
        real_reg = build_real_capability_registry()
        all_ids = set(real_reg.list_all())

        expected_n8n = [
            "n8n.list_workflows",
            "n8n_list_workflows",
            "n8n.get_workflow",
            "n8n_get_workflow",
            "n8n.validate_workflow",
            "n8n_validate_workflow",
            "n8n.create_workflow",
            "n8n_create_workflow",
            "n8n.activate_workflow",
            "n8n_activate_workflow",
            "n8n.trigger_workflow",
            "n8n_trigger_workflow",
            "n8n.get_execution_status",
            "n8n_get_execution_status",
        ]
        for cap_id in expected_n8n:
            self.assertIn(cap_id, all_ids)

    def test_argument_resolver_extracts_n8n_slots(self):
        """ArgumentResolver correctly extracts workflow_id, execution_id, and workflow names."""
        # 1. trigger workflow with wf_ ID
        env1 = self.resolver.resolve(N8N_TRIGGER_WORKFLOW_SPEC, "trigger workflow wf_999")
        self.assertEqual(env1.arguments.get("workflow_id"), "wf_999")

        # 2. get workflow with quoted ID
        env2 = self.resolver.resolve(N8N_GET_WORKFLOW_SPEC, "get workflow 'my_custom_flow'")
        self.assertEqual(env2.arguments.get("workflow_id"), "my_custom_flow")

        # 3. get execution status
        env3 = self.resolver.resolve(N8N_GET_EXECUTION_STATUS_SPEC, "check execution exec_42 status")
        self.assertEqual(env3.arguments.get("execution_id"), "exec_42")

        # 4. create workflow name
        env4 = self.resolver.resolve(N8N_CREATE_WORKFLOW_SPEC, "create workflow called 'Order Processor'")
        self.assertEqual(env4.arguments.get("name"), "Order Processor")


if __name__ == "__main__":
    unittest.main()
