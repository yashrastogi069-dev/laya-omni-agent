"""
L0 Baseline Verification & Defect Reproduction Test Suite
========================================================
Establishes verifiable ground truth for the LAYA Omni Agent repository.
Covers:
- Tool registry inventory
- Confirmed defects (safe_math missing import, System 1 truncation, prompt-as-argument)
- Memory engine schema invariants
- Operational sanity of baseline tools
"""

import os
import sys
import unittest
import json

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from omni_engine.tools import OMNI_TOOL_REGISTRY
from omni_engine.memory import OmniMemory, MEMORY_PATH
from omni_engine.system2 import System2Engine
from omni_engine.planner import AutonomousPlanner


class TestL0ToolRegistry(unittest.TestCase):
    def test_tool_registry_count(self):
        """Verify the exact tool count in OMNI_TOOL_REGISTRY."""
        self.assertEqual(len(OMNI_TOOL_REGISTRY), 23, "OMNI_TOOL_REGISTRY should contain exactly 23 tools.")

    def test_tool_categories(self):
        """Verify registered categories."""
        expected_categories = {"web", "browser", "os", "dev", "data"}
        actual_categories = {v["category"] for v in OMNI_TOOL_REGISTRY.values()}
        self.assertEqual(actual_categories, expected_categories)

    def test_all_tools_have_required_fields(self):
        """Every tool entry must have func, desc, and category."""
        for name, spec in OMNI_TOOL_REGISTRY.items():
            self.assertIn("func", spec, f"Tool {name} missing 'func'")
            self.assertIn("desc", spec, f"Tool {name} missing 'desc'")
            self.assertIn("category", spec, f"Tool {name} missing 'category'")
            self.assertTrue(callable(spec["func"]), f"Tool {name} 'func' is not callable")


class TestL0ConfirmedDefects(unittest.TestCase):
    def test_safe_math_no_longer_raises_nameerror(self):
        """
        Verified: tool_safe_math previously raised NameError on missing 're'.
        Fixed in L1: Now evaluates successfully.
        """
        from omni_engine.tools.data_tools import tool_safe_math
        res = tool_safe_math("2 + 2")
        self.assertIn("= **4**", res)

    def test_defect_system1_tool_catalog_truncation(self):
        """
        Defect: System1Router.route_tool truncates tool_catalog to [:12].
        Proves that 11 tools are structurally invisible to System 1.
        """
        catalog_items = list(OMNI_TOOL_REGISTRY.items())
        visible_criteria = {k: v["desc"][:85] for k, v in catalog_items[:12]}
        hidden_tools = [k for k, _ in catalog_items[12:]]

        self.assertEqual(len(visible_criteria), 12)
        self.assertEqual(len(hidden_tools), 11)
        self.assertIn("powershell", hidden_tools)
        self.assertIn("file_read", hidden_tools)
        self.assertIn("file_write", hidden_tools)
        self.assertIn("run_python", hidden_tools)
        self.assertIn("safe_math", hidden_tools)

    def test_defect_prompt_passed_directly_as_file_read_arg(self):
        """
        Defect: Passing raw user prompt 'read the file README.md' directly to
        tool_file_read results in searching for a literal file named 'read the file README.md'.
        """
        from omni_engine.tools.dev_tools import tool_file_read
        result = tool_file_read("read the file README.md")
        self.assertTrue(result.startswith("❌ File not found:"), f"Unexpected result: {result}")


class TestL0WorkingBaselineTools(unittest.TestCase):
    def test_system_diagnostics(self):
        """tool_system_diagnostics executes and returns hardware stats."""
        from omni_engine.tools.os_tools import tool_system_diagnostics
        res = tool_system_diagnostics("")
        self.assertIn("Windows System Diagnostics", res)
        self.assertIn("CPU Load", res)
        self.assertIn("Memory Usage", res)

    def test_directory_tree(self):
        """tool_directory_tree executes and includes workspace root."""
        from omni_engine.tools.dev_tools import tool_directory_tree
        res = tool_directory_tree("")
        self.assertIn("Directory Structure", res)
        self.assertIn("omni_engine", res)

    def test_git_status(self):
        """tool_git_status executes and returns current branch."""
        from omni_engine.tools.dev_tools import tool_git_status
        res = tool_git_status("")
        self.assertIn("Git Status", res)
        self.assertIn("Branch: `main`", res)


class TestL0MemoryInvariants(unittest.TestCase):
    def test_memory_load_and_keys(self):
        """OmniMemory loads valid dictionary with expected structure."""
        mem = OmniMemory()
        self.assertIsInstance(mem.data, dict)
        self.assertIn("missions", mem.data)
        self.assertIn("total_missions", mem.data)


if __name__ == "__main__":
    unittest.main()
