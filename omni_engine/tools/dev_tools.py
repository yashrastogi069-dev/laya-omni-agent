"""
Developer, Workspace & Code Toolset
- File read, write, append, and patch
- Workspace file search & grep
- Directory tree visualizer
- Dynamic Python execution engine
- Git version control operations
- Environment variable viewer
"""

import os
import re
import sys
import subprocess

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def tool_file_read(filepath: str) -> str:
    """Reads content from any local file."""
    path = filepath.strip().strip('"').strip("'")
    if not os.path.isabs(path):
        path = os.path.join(WORKSPACE_ROOT, path)
    if not os.path.exists(path):
        return f"❌ File not found: {path}"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return f"### File: `{os.path.basename(path)}` ({len(content.splitlines())} lines):\n```\n{content[:3500]}\n```"
    except Exception as e:
        return f"Error reading file: {e}"


def tool_file_write(payload: str) -> str:
    """Creates or overwrites a file. Format: 'filename.ext ::: content'"""
    parts = payload.split(":::", 1)
    if len(parts) == 2:
        fpath, content = parts[0].strip(), parts[1].strip()
    else:
        lines = payload.strip().split("\n", 1)
        fpath = lines[0].strip()
        content = lines[1] if len(lines) > 1 else ""

    if not os.path.isabs(fpath):
        fpath = os.path.join(WORKSPACE_ROOT, fpath)
    os.makedirs(os.path.dirname(fpath), exist_ok=True)

    try:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Written to `{os.path.relpath(fpath, WORKSPACE_ROOT)}` ({len(content)} chars)."
    except Exception as e:
        return f"Write error: {e}"


def tool_search_code(query: str) -> str:
    """Searches workspace files by filename or text inside code files."""
    q = query.strip().lower()
    matches = []
    for root, _, files in os.walk(WORKSPACE_ROOT):
        if any(ignored in root for ignored in [".git", "__pycache__", "venv", ".idea"]):
            continue
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), WORKSPACE_ROOT)
            if q in f.lower():
                matches.append(f"📁 [Filename match] `{rel}`")
            elif f.endswith(('.py', '.js', '.json', '.md', '.txt', '.bat')):
                try:
                    with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as fp:
                        for lno, line in enumerate(fp, 1):
                            if q in line.lower():
                                matches.append(f"📄 `{rel}:{lno}`: {line.strip()[:80]}")
                                if len(matches) > 15:
                                    break
                except Exception:
                    pass
        if len(matches) > 15:
            break

    if not matches:
        return f"No code or files matching '{query}' found."
    return f"### Search Results for '{query}':\n" + "\n".join(matches[:15])


def tool_directory_tree(folder: str = "") -> str:
    """Generates a hierarchical directory tree of the workspace."""
    target = os.path.join(WORKSPACE_ROOT, folder.strip()) if folder else WORKSPACE_ROOT
    tree_lines = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", ".system_generated"]]
        level = root.replace(target, '').count(os.sep)
        indent = ' ' * 4 * level
        tree_lines.append(f"{indent}📂 {os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files[:8]:
            tree_lines.append(f"{subindent}📄 {f}")
        if len(files) > 8:
            tree_lines.append(f"{subindent}... ({len(files)-8} more files)")
        if len(tree_lines) > 40:
            tree_lines.append("... (truncated)")
            break
    return f"### Directory Structure:\n```\n" + "\n".join(tree_lines) + "\n```"


def tool_run_python(code_snippet: str) -> str:
    """Dynamically executes a Python snippet and returns output."""
    clean_code = re.sub(r'^```python|^```|```$', '', code_snippet.strip(), flags=re.MULTILINE).strip()
    tmp_path = os.path.join(WORKSPACE_ROOT, "_sandbox_exec.py")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(clean_code)
        res = subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, timeout=10)
        out = res.stdout.strip() or res.stderr.strip()
        return f"### Python Sandbox Output:\n```\n{out}\n```"
    except Exception as e:
        return f"Python execution error: {e}"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def tool_git_status(_: str = "") -> str:
    """Checks git repository status and branch."""
    try:
        res = subprocess.run(["git", "status", "-s"], cwd=WORKSPACE_ROOT, capture_output=True, text=True, timeout=5)
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=WORKSPACE_ROOT, capture_output=True, text=True, timeout=5)
        return f"### Git Status (Branch: `{branch.stdout.strip()}`):\n```\n{res.stdout.strip() or 'Working tree clean'}\n```"
    except Exception as e:
        return f"Git error: {e}"
