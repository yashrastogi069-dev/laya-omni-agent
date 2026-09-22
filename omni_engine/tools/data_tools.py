"""
Data Science, Database & Intelligence Reporting Toolset
- SQLite database query runner
- CSV & JSON data inspector
- Mathematical calculation engine
- Report & Dossier formatter
"""

import os
import json
import sqlite3
import math

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(WORKSPACE_ROOT, "omni_data.db")

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


def tool_safe_math(expression: str) -> str:
    """Evaluates mathematical, trigonometric, and arithmetic expressions safely."""
    clean = re.sub(r'^(calculate|math|what is|compute)\s+', '', expression.strip(), flags=re.IGNORECASE).strip()
    safe_dict = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
    safe_dict["abs"] = abs
    safe_dict["round"] = round
    try:
        # Check against dangerous tokens
        if any(b in clean for b in ["import", "open", "os", "sys", "exec", "eval", "__"]):
            return "Expression rejected for safety."
        val = eval(clean, {"__builtins__": {}}, safe_dict)
        return f"### Math Evaluation:\n`{clean}` = **{val}**"
    except Exception as e:
        return f"Math calculation error: {e}"
