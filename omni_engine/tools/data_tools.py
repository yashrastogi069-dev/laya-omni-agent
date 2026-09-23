"""
Data Science, Database & Intelligence Reporting Toolset
- SQLite database query runner
- CSV & JSON data inspector
- Mathematical calculation engine (AST-based safe evaluation)
- Report & Dossier formatter
"""

import os
import json
import sqlite3
import math
import re
import ast

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(WORKSPACE_ROOT, "omni_data.db")

# Whitelisted mathematical operations and functions for safe AST evaluation
SAFE_OPERATORS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: +a,
}

def _safe_factorial(n):
    """Bounds factorial computation to prevent CPU exhaustion."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError("Factorial argument must be an integer.")
    if not (0 <= n <= 100):
        raise ValueError(f"Factorial argument out of bounds: {n} (allowed: 0 <= n <= 100).")
    return math.factorial(n)

SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "abs": abs,
    "round": round,
    "radians": math.radians,
    "degrees": math.degrees,
    "factorial": _safe_factorial,
}

SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}


def _evaluate_ast_node(node, depth: int = 0):
    """Recursively evaluates a whitelisted math AST node."""
    if depth > 40:
        raise ValueError("Expression too complex (exceeded maximum AST depth).")

    if isinstance(node, ast.Expression):
        return _evaluate_ast_node(node.body, depth + 1)

    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            if abs(node.value) > 1e100:
                raise ValueError("Numeric literal magnitude exceeds maximum allowed limit (1e100).")
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    elif isinstance(node, ast.Name):
        if node.id in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[node.id]
        raise ValueError(f"Unauthorized variable or constant: '{node.id}'")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")

        left = _evaluate_ast_node(node.left, depth + 1)
        right = _evaluate_ast_node(node.right, depth + 1)

        # Defense against computational exhaustion (e.g. 9**9**9**9 or large base/exp)
        if op_type is ast.Pow:
            if isinstance(right, (int, float)) and abs(right) > 100:
                raise ValueError("Exponent magnitude too large (maximum exponent is 100).")
            if isinstance(left, (int, float)) and abs(left) > 1e6 and abs(right) > 10:
                raise ValueError("Base too large for power operation.")

        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Division by zero.")

        return SAFE_OPERATORS[op_type](left, right)

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _evaluate_ast_node(node.operand, depth + 1)
        return SAFE_OPERATORS[op_type](operand)

    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError(f"Unauthorized indirect function call: {type(node.func).__name__}")
        func_name = node.func.id
        if func_name not in SAFE_FUNCTIONS:
            raise ValueError(f"Unauthorized function: '{func_name}'")

        args = [_evaluate_ast_node(arg, depth + 1) for arg in node.args]
        return SAFE_FUNCTIONS[func_name](*args)

    else:
        raise ValueError(f"Unauthorized syntax construct: {type(node).__name__}")


def tool_safe_math(expression: str) -> str:
    """Evaluates mathematical, trigonometric, and arithmetic expressions safely using AST analysis."""
    clean = re.sub(r'^(calculate|math|what is|compute)\s+', '', expression.strip(), flags=re.IGNORECASE).strip()
    if not clean:
        return "Please provide a mathematical expression to evaluate."
    if len(clean) > 256:
        return "Math calculation error: Expression length exceeds maximum allowed limit of 256 characters."

    try:
        parsed = ast.parse(clean, mode='eval')
        node_count = sum(1 for _ in ast.walk(parsed))
        if node_count > 40:
            return f"Math calculation error: Expression complexity exceeded (AST node count {node_count} > 40)."
        val = _evaluate_ast_node(parsed)
        if isinstance(val, float) and val.is_integer():
            val = int(val)
        return f"### Math Evaluation:\n`{clean}` = **{val}**"
    except ZeroDivisionError:
        return f"Math calculation error: Division by zero in `{clean}`"
    except Exception as e:
        return f"Math calculation error: {e}"


def tool_sqlite_exec(sql_query: str) -> str:
    """Executes a SQL query on local SQLite database (omni_data.db)."""
    clean_sql = sql_query.strip()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(clean_sql)
        if clean_sql.lower().startswith("select"):
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description] if cursor.description else []
            conn.close()
            if not rows:
                return "Query returned 0 rows."
            table = f"### Query Result ({len(rows)} rows):\n\n| " + " | ".join(cols) + " |\n| " + " | ".join(["---"]*len(cols)) + " |\n"
            for r in rows[:15]:
                table += "| " + " | ".join(str(val) for val in r) + " |\n"
            return table
        else:
            conn.commit()
            changes = conn.total_changes
            conn.close()
            return f"✅ SQL statement executed successfully ({changes} changes)."
    except Exception as e:
        return f"SQLite error: {e}"


def tool_inspect_data(file_path: str) -> str:
    """Inspects a CSV or JSON file, calculating row counts, columns, and data preview."""
    target = os.path.join(WORKSPACE_ROOT, file_path.strip()) if not os.path.isabs(file_path) else file_path
    if not os.path.exists(target):
        return f"File '{file_path}' does not exist."

    try:
        if target.endswith(".json"):
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return f"### JSON Array ({len(data)} items)\nFirst item preview:\n```json\n{json.dumps(data[0] if data else {}, indent=2)[:800]}\n```"
            else:
                return f"### JSON Object ({len(data.keys())} keys)\nKeys: {list(data.keys())[:20]}\nPreview:\n```json\n{json.dumps(data, indent=2)[:800]}\n```"
        elif target.endswith(".csv"):
            with open(target, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            headers = lines[0].split(",") if lines else []
            return f"### CSV Dataset ({len(lines)-1} rows, {len(headers)} columns)\nColumns: `{', '.join(headers)}`\nPreview (first 3 rows):\n" + "\n".join(f"- {l}" for l in lines[1:4])
        return "Unsupported format for inspector (use .csv or .json)."
    except Exception as e:
        return f"Data inspection error: {e}"
