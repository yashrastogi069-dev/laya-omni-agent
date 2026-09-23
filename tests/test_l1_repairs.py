"""
L1 Reliability Repairs & Regression Test Suite
==============================================
Validates:
1. tool_safe_math AST evaluation, operator coverage, and security/exhaustion protections.
2. OmniMemory schema migration, atomic file writes, crash recovery, and verified success tracking.
3. Package-level import sanity and smoke tests.
"""

import os
import sys
import json
import tempfile
import unittest

# Ensure root directory is on path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from omni_engine.tools.data_tools import tool_safe_math
from omni_engine.memory import OmniMemory


class TestL1SafeMathRepairs(unittest.TestCase):
    def test_basic_arithmetic(self):
        """Validates fundamental arithmetic operations."""
        self.assertIn("= **4**", tool_safe_math("2 + 2"))
        self.assertIn("= **6**", tool_safe_math("calculate 10 - 4"))
        self.assertIn("= **21**", tool_safe_math("what is 3 * 7"))
        self.assertIn("= **5**", tool_safe_math("compute 15 / 3"))
        self.assertIn("= **20**", tool_safe_math("(2 + 3) * 4"))

    def test_floating_point_and_modulo(self):
        """Validates floating point, integer division, and modulo."""
        self.assertIn("= **5.25**", tool_safe_math("10.5 / 2"))
        self.assertIn("= **3**", tool_safe_math("10 // 3"))
        self.assertIn("= **1**", tool_safe_math("10 % 3"))

    def test_standard_math_functions(self):
        """Validates whitelisted math library functions."""
        self.assertIn("= **4**", tool_safe_math("sqrt(16)"))
        self.assertIn("= **10**", tool_safe_math("abs(-10)"))
        self.assertIn("= **3.14**", tool_safe_math("round(3.14159, 2)"))
        self.assertIn("= **0**", tool_safe_math("sin(0)"))

    def test_math_constants(self):
        """Validates constants like pi and e."""
        res_pi = tool_safe_math("pi")
        self.assertIn("3.1415", res_pi)
        res_e = tool_safe_math("e * 2")
        self.assertIn("5.436", res_e)

    def test_computational_exhaustion_protection(self):
        """Defends against massive exponents that could lock the GIL."""
        res = tool_safe_math("9**9**9**9")
        self.assertIn("Exponent too large", res)

        res_large_exp = tool_safe_math("2**1000")
        self.assertIn("Exponent too large", res_large_exp)

    def test_security_and_sandbox_rejection(self):
        """Rejects dangerous statements, imports, and attribute access."""
        res_import = tool_safe_math("__import__('os').system('dir')")
        self.assertIn("Unauthorized", res_import)

        res_open = tool_safe_math("open('README.md')")
        self.assertIn("Unauthorized", res_open)

        res_attr = tool_safe_math("''.__class__")
        self.assertIn("Unauthorized", res_attr)

    def test_division_by_zero(self):
        """Gracefully handles division by zero without unhandled exceptions."""
        res = tool_safe_math("10 / 0")
        self.assertIn("Division by zero", res)


class TestL1MemoryRepairs(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.mem_file = os.path.join(self.test_dir.name, "test_memory.json")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_legacy_schema_migration(self):
        """Migrates legacy keys (tool_effectiveness, learned_facts) automatically."""
        legacy_data = {
            "version": "2.0",
            "total_missions": 2,
            "missions": [],
            "tool_effectiveness": {"web_search": 5, "file_read": 3},
            "learned_facts": {"python": "interpreted language"}
        }
        with open(self.mem_file, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f)

        mem = OmniMemory(filepath=self.mem_file)
        self.assertIn("tool_success_counts", mem.data)
        self.assertEqual(mem.data["tool_success_counts"]["web_search"], 5)
        self.assertEqual(mem.data["tool_success_counts"]["file_read"], 3)
        self.assertIn("learned_insights", mem.data)
        self.assertEqual(mem.data["learned_insights"]["python"], "interpreted language")

    def test_atomic_persistence(self):
        """Verifies atomic write leaves no stray .tmp files and produces valid JSON."""
        mem = OmniMemory(filepath=self.mem_file)
        mem.record_mission("test query", "web_search", "test summary", verified_success=True)

        self.assertTrue(os.path.exists(self.mem_file))
        self.assertFalse(os.path.exists(self.mem_file + ".tmp"))

        with open(self.mem_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["total_missions"], 1)
        self.assertEqual(saved["tool_success_counts"]["web_search"], 1)

    def test_distinguish_execution_from_verified_success(self):
        """Execution count increments always; success count increments only when verified."""
        mem = OmniMemory(filepath=self.mem_file)
        # Succeeded run
        mem.record_mission("query 1", "file_read", "ok", verified_success=True)
        # Failed run
        mem.record_mission("query 2", "file_read", "error: not found", verified_success=False)

        self.assertEqual(mem.data["tool_invocations"]["file_read"], 2)
        self.assertEqual(mem.data["tool_success_counts"]["file_read"], 1)

    def test_corrupted_file_recovery(self):
        """Recovers cleanly from empty or malformed JSON without raising unhandled errors."""
        with open(self.mem_file, "w", encoding="utf-8") as f:
            f.write("{invalid_json_content,,")

        mem = OmniMemory(filepath=self.mem_file)
        self.assertIsInstance(mem.data, dict)
        self.assertEqual(mem.data["total_missions"], 0)


class TestL1PackageSmoke(unittest.TestCase):
    def test_omni_engine_imports(self):
        """Verifies clean imports of all engine modules."""
        import omni_engine
        from omni_engine import System1Router, System2Engine, OmniMemory, AutonomousPlanner, OMNI_TOOL_REGISTRY
        self.assertIsNotNone(System1Router)
        self.assertIsNotNone(System2Engine)
        self.assertIsNotNone(OmniMemory)
        self.assertIsNotNone(AutonomousPlanner)
        self.assertEqual(len(OMNI_TOOL_REGISTRY), 23)


if __name__ == "__main__":
    unittest.main()
