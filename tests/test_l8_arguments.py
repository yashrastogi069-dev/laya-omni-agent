"""
tests.test_l8_arguments
=======================
Comprehensive test suite for Checkpoint L8:
Typed Argument Resolution & Extraction Engine.

Validates:
1. High-precision deterministic regex & syntactic extractors.
2. Schema-aware argument resolution across canonical capabilities.
3. Schema default population and context inheritance.
4. Missing required slot clarification gating (zero hallucination).
5. ArgumentResolutionEnvelope contract integrity and telemetry.
6. Generative fallback synthesis behavior when enabled.
"""

import unittest
from typing import Any, Dict, Optional

from omni_engine.contracts.arguments import (
    ArgumentExtractionSource,
    ArgumentResolutionEnvelope,
    ArgumentSlot,
)
from omni_engine.contracts.capability import CapabilitySpec
from omni_engine.capabilities.definitions import build_canonical_registry
from omni_engine.arguments.extractors import (
    extract_app_name,
    extract_clipboard_data,
    extract_file_path,
    extract_math_expression,
    extract_pid,
    extract_ping_host,
    extract_powershell_script,
    extract_process_name,
    extract_python_code,
    extract_search_query,
    extract_sql_query,
    extract_url,
)
from omni_engine.arguments.resolver import ArgumentResolver, CLARIFICATION_PROMPTS
from omni_engine.providers.base import GenerativeProvider, GenerationResult, ProviderHealth
import json


class MockGenerativeProvider(GenerativeProvider):
    """Mock generative provider for testing argument synthesis fallback."""

    def __init__(self, mock_return: Optional[Dict[str, Any]] = None):
        self.provider_id = "mock_generative"
        self.model_id = "mock-model"
        self.is_configured = True
        self.mock_return = mock_return or {}

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 2000) -> GenerationResult:
        return GenerationResult(
            text=f"```json\n{json.dumps(self.mock_return)}\n```",
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.2,
        )

    def generate_structured(self, prompt: str, response_model: Any, system_prompt: Optional[str] = None, temperature: float = 0.2, max_tokens: int = 2000) -> Any:
        return response_model.model_validate(self.mock_return)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            model_id=self.model_id,
            healthy=True,
            latency_ms=1.0,
        )


class TestDeterministicExtractors(unittest.TestCase):
    """Unit tests for standalone high-precision extractors."""

    def test_extract_file_path(self):
        # Quoted path
        self.assertEqual(extract_file_path("Please inspect 'data/config.json' file"), "data/config.json")
        self.assertEqual(extract_file_path('read file "C:\\Users\\test\\doc.txt"'), "C:\\Users\\test\\doc.txt")
        # Windows drive path unquoted
        self.assertEqual(extract_file_path("open C:\\project\\main.py now"), "C:\\project\\main.py")
        # Relative unix-like path
        self.assertEqual(extract_file_path("check src/utils/helpers.py for errors"), "src/utils/helpers.py")
        # Local filename with known extension
        self.assertEqual(extract_file_path("look at summary.csv"), "summary.csv")
        # Keyword based
        self.assertEqual(extract_file_path("read file report.pdf"), "report.pdf")
        # None cases
        self.assertIsNone(extract_file_path("hello world how are you"))
        self.assertIsNone(extract_file_path(""))

    def test_extract_url(self):
        # Standard HTTP/HTTPS
        self.assertEqual(extract_url("Check out https://github.com/trending today"), "https://github.com/trending")
        self.assertEqual(extract_url("Scrape http://news.ycombinator.com/item?id=123."), "http://news.ycombinator.com/item?id=123")
        # Localhost with port (e.g. n8n local instance)
        self.assertEqual(extract_url("Connect to localhost:5678 webhooks"), "http://localhost:5678")
        # None cases
        self.assertIsNone(extract_url("just a normal text"))
        self.assertIsNone(extract_url(""))

    def test_extract_pid(self):
        # Explicit PID
        self.assertEqual(extract_pid("kill process with pid: 4892"), 4892)
        self.assertEqual(extract_pid("process id = 1042"), 1042)
        # Kill command pattern
        self.assertEqual(extract_pid("terminate 9912 immediately"), 9912)
        self.assertEqual(extract_pid("stop process 1234"), 1234)
        # None cases
        self.assertIsNone(extract_pid("kill the rogue process"))
        self.assertIsNone(extract_pid(""))

    def test_extract_process_name(self):
        # Process with .exe
        self.assertEqual(extract_process_name("find rogue_app.exe in tasks"), "rogue_app.exe")
        # Known process names
        self.assertEqual(extract_process_name("is node running right now?"), "node")
        self.assertEqual(extract_process_name("check python processes"), "python")
        self.assertEqual(extract_process_name("look for n8n server"), "n8n")
        # None cases
        self.assertIsNone(extract_process_name("hello world"))

    def test_extract_app_name(self):
        # Launch patterns
        self.assertEqual(extract_app_name("launch calc"), "calc")
        self.assertEqual(extract_app_name("open notepad please"), "notepad")
        self.assertEqual(extract_app_name("start service n8n"), "n8n")
        self.assertEqual(extract_app_name("run app powershell"), "powershell")
        # None cases
        self.assertIsNone(extract_app_name("read the file"))

    def test_extract_sql_query(self):
        # Quoted SQL
        self.assertEqual(
            extract_sql_query('run SQL "SELECT id, name FROM users WHERE active = 1"'),
            "SELECT id, name FROM users WHERE active = 1",
        )
        # Unquoted SQL
        sql = extract_sql_query("execute SELECT count(*) FROM orders;")
        self.assertTrue(sql.startswith("SELECT count(*) FROM orders"))
        self.assertIsNone(extract_sql_query("do something else"))

    def test_extract_math_expression(self):
        # Compute/calculate prefix
        self.assertEqual(extract_math_expression("calculate 2 ** 10 + 1024"), "2 ** 10 + 1024")
        self.assertEqual(extract_math_expression("compute: (50 * 4) / 2"), "(50 * 4) / 2")
        # Bare math
        self.assertIsNotNone(extract_math_expression("what is 128 * 256?"))
        self.assertIsNone(extract_math_expression("hello math world"))

    def test_extract_powershell_script(self):
        # Quoted powershell command
        self.assertEqual(
            extract_powershell_script("powershell 'Get-Process | Where-Object CPU -gt 10'"),
            "Get-Process | Where-Object CPU -gt 10",
        )
        # Unquoted powershell command
        self.assertEqual(
            extract_powershell_script("powershell Get-Service -Name wuauserv"),
            "Get-Service -Name wuauserv",
        )
        self.assertIsNone(extract_powershell_script("just a sentence"))

    def test_extract_python_code(self):
        # Fenced markdown code
        code_fence = "```python\nimport sys\nprint(sys.version)\n```"
        self.assertEqual(extract_python_code(code_fence), "import sys\nprint(sys.version)")
        # Inline print
        self.assertEqual(extract_python_code("execute print('hello from laya')"), "print('hello from laya')")
        self.assertIsNone(extract_python_code("not python code"))

    def test_extract_search_query(self):
        # Quoted search query
        self.assertEqual(extract_search_query('search for "ModernBERT large weights"'), "ModernBERT large weights")
        # Pattern search
        self.assertEqual(extract_search_query("search the web for fast semantic routers"), "fast semantic routers")
        self.assertIsNone(extract_search_query("hi"))

    def test_extract_ping_host(self):
        # IP address
        self.assertEqual(extract_ping_host("ping test to 192.168.1.1"), "192.168.1.1")
        # Domain name
        self.assertEqual(extract_ping_host("ping google.com now"), "google.com")
        self.assertIsNone(extract_ping_host("ping"))

    def test_extract_clipboard_data(self):
        # Read action
        action, text = extract_clipboard_data("paste clipboard contents")
        self.assertEqual(action, "read")
        self.assertIsNone(text)
        # Write action
        action, text = extract_clipboard_data("copy 'Hello World' to clipboard")
        self.assertEqual(action, "write")
        self.assertEqual(text, "Hello World")


class TestArgumentResolverCanonicalCapabilities(unittest.TestCase):
    """Tests ArgumentResolver against canonical CapabilitySpecs."""

    def setUp(self):
        self.registry = build_canonical_registry()
        self.resolver = ArgumentResolver()

    def test_file_read_resolution_success(self):
        spec = self.registry.get("file_read")
        envelope = self.resolver.resolve(spec, "Please read the contents of 'src/config.json'")
        self.assertTrue(envelope.is_valid)
        self.assertFalse(envelope.clarification_needed)
        self.assertEqual(envelope.arguments["filepath"], "src/config.json")
        self.assertEqual(envelope.resolved_slots["filepath"].source, ArgumentExtractionSource.DETERMINISTIC_REGEX)

    def test_file_read_missing_triggers_clarification(self):
        spec = self.registry.get("file_read")
        envelope = self.resolver.resolve(spec, "please read the file")
        self.assertFalse(envelope.is_valid)
        self.assertTrue(envelope.clarification_needed)
        self.assertIn("filepath", envelope.missing_slots)
        self.assertEqual(envelope.clarification_prompt, CLARIFICATION_PROMPTS["file_read"])

    def test_file_write_resolution(self):
        spec = self.registry.get("file_write")
        prompt = 'write to "output.log" with content: "execution completed successfully"'
        envelope = self.resolver.resolve(spec, prompt)
        self.assertTrue(envelope.is_valid)
        self.assertEqual(envelope.arguments["filepath"], "output.log")
        self.assertEqual(envelope.arguments["content"], "execution completed successfully")

    def test_kill_process_resolution(self):
        spec = self.registry.get("kill_process")
        # Valid PID
        envelope = self.resolver.resolve(spec, "kill process with pid 8129")
        self.assertTrue(envelope.is_valid)
        self.assertEqual(envelope.arguments["target"], "8129")

        # Missing PID
        envelope_missing = self.resolver.resolve(spec, "kill the rogue process")
        self.assertFalse(envelope_missing.is_valid)
        self.assertTrue(envelope_missing.clarification_needed)
        self.assertIn("target", envelope_missing.missing_slots)
        self.assertEqual(envelope_missing.clarification_prompt, CLARIFICATION_PROMPTS["kill_process"])

    def test_launch_app_resolution(self):
        spec = self.registry.get("launch_app")
        envelope = self.resolver.resolve(spec, "please start n8n")
        self.assertTrue(envelope.is_valid)
        self.assertEqual(envelope.arguments["app_name"], "n8n")

    def test_sqlite_exec_resolution(self):
        spec = self.registry.get("sqlite_exec")
        prompt = 'run SQL "SELECT * FROM users" on db "app.db"'
        envelope = self.resolver.resolve(spec, prompt)
        self.assertTrue(envelope.is_valid)
        self.assertEqual(envelope.arguments["query"], "SELECT * FROM users")
        self.assertEqual(envelope.arguments["db_path"], "app.db")

    def test_safe_math_resolution(self):
        spec = self.registry.get("safe_math")
        envelope = self.resolver.resolve(spec, "calculate 1024 * 768")
        self.assertTrue(envelope.is_valid)
        self.assertEqual(envelope.arguments["expression"], "1024 * 768")

    def test_web_search_resolution(self):
        spec = self.registry.get("web_search")
        envelope = self.resolver.resolve(spec, "search the web for modernbert architecture")
        self.assertTrue(envelope.is_valid)
        self.assertEqual(envelope.arguments["query"], "modernbert architecture")
        self.assertEqual(envelope.arguments["max_results"], 6)  # Schema default

    def test_scrape_url_resolution(self):
        spec = self.registry.get("scrape_url")
        envelope = self.resolver.resolve(spec, "scrape https://news.ycombinator.com")
        self.assertTrue(envelope.is_valid)
        self.assertEqual(envelope.arguments["url"], "https://news.ycombinator.com")

    def test_powershell_resolution(self):
        spec = self.registry.get("powershell")
        envelope = self.resolver.resolve(spec, "powershell 'Get-Date'")
        self.assertTrue(envelope.is_valid)
        self.assertEqual(envelope.arguments["command"], "Get-Date")

    def test_directory_tree_schema_default(self):
        spec = self.registry.get("directory_tree")
        envelope = self.resolver.resolve(spec, "show me the directory tree")
        self.assertTrue(envelope.is_valid)
        self.assertEqual(envelope.arguments["path"], ".")
        self.assertEqual(envelope.arguments["max_depth"], 3)


class TestArgumentResolverContextAndGenerative(unittest.TestCase):
    """Tests context inheritance and generative fallback synthesis."""

    def setUp(self):
        self.registry = build_canonical_registry()

    def test_context_inheritance(self):
        resolver = ArgumentResolver()
        spec = self.registry.get("file_read")
        # Missing in prompt, but provided in explicit context using alias "file_path"
        context = {"file_path": "inherited/path/notes.md"}
        envelope = resolver.resolve(spec, "please read the file", context=context)
        self.assertTrue(envelope.is_valid)
        self.assertEqual(envelope.arguments["filepath"], "inherited/path/notes.md")
        self.assertEqual(
            envelope.resolved_slots["filepath"].source,
            ArgumentExtractionSource.CONTEXT_INHERITED,
        )

    def test_generative_fallback_synthesis(self):
        # Mock generative provider that synthesizes complex/unusual prompt
        mock_prov = MockGenerativeProvider(mock_return={"filepath": "synthesized/target.txt"})
        resolver = ArgumentResolver(generative_provider=mock_prov)
        spec = self.registry.get("file_read")
        
        # Obscure prompt with no regex match
        envelope = resolver.resolve(spec, "extract the designated target document")
        self.assertTrue(envelope.is_valid)
        self.assertEqual(envelope.arguments["filepath"], "synthesized/target.txt")
        self.assertEqual(
            envelope.resolved_slots["filepath"].source,
            ArgumentExtractionSource.GENERATIVE_SYNTHESIS,
        )

    def test_resolution_latency_telemetry(self):
        resolver = ArgumentResolver()
        spec = self.registry.get("file_read")
        envelope = resolver.resolve(spec, "read 'test.py'")
        self.assertGreaterEqual(envelope.latency_ms, 0.0)
        self.assertIn("deterministic_path", envelope.metadata)
        self.assertTrue(envelope.metadata["deterministic_path"])


if __name__ == "__main__":
    unittest.main()
