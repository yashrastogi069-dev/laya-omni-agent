"""
Windows OS & Desktop Automation Toolset
- Hardware & resource monitoring (CPU, RAM, Disk, Uptime)
- Process inspector & task manager
- Native Windows App Launcher
- Clipboard management & full-screen desktop capture
- PowerShell & CMD command execution
- Network ping & diagnostics
"""

import os
import re
import time
import subprocess
import psutil
import pyperclip
from PIL import ImageGrab

def tool_system_diagnostics(_: str = "") -> str:
    """Reads real-time hardware status: CPU, RAM, Disk, Network, and Uptime."""
    cpu = psutil.cpu_percent(interval=0.4)
    cores = psutil.cpu_count(logical=True)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    net = psutil.net_io_counters()
    boot_time = psutil.boot_time()
    uptime_hours = (time.time() - boot_time) / 3600

    report = (
        f"### Windows System Diagnostics\n"
        f"- **CPU Load**: {cpu}% ({cores} logical cores)\n"
        f"- **Memory Usage**: {mem.percent}% ({mem.used / (1024**3):.1f} GB used / {mem.total / (1024**3):.1f} GB total)\n"
        f"- **Available RAM**: {mem.available / (1024**3):.1f} GB free\n"
        f"- **C: Drive Disk Usage**: {disk.percent}% used ({disk.free / (1024**3):.1f} GB free / {disk.total / (1024**3):.1f} GB total)\n"
        f"- **Network Activity**: Sent: {net.bytes_sent / (1024**2):.1f} MB | Received: {net.bytes_recv / (1024**2):.1f} MB\n"
        f"- **System Uptime**: {uptime_hours:.1f} hours\n"
    )
    return report


def tool_list_processes(filter_query: str = "") -> str:
    """Lists running Windows processes sorted by memory usage, with optional search filter."""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
        try:
            info = p.info
            if filter_query and filter_query.lower() not in (info['name'] or "").lower():
                continue
            procs.append(info)
        except Exception:
            pass

    procs.sort(key=lambda x: x.get('memory_percent') or 0, reverse=True)
    top = procs[:10]

    if not top:
        return f"No active processes found matching '{filter_query}'."

    table = "### Top Windows Processes:\n\n| PID | Process Name | RAM % |\n| --- | --- | --- |\n"
    for item in top:
        table += f"| {item['pid']} | {item['name']} | {item['memory_percent']:.2f}% |\n"
    return table


def tool_kill_process(pid_or_name: str) -> str:
    """Terminates a process by PID or executable name."""
    target = pid_or_name.strip()
    try:
        if target.isdigit():
            p = psutil.Process(int(target))
            name = p.name()
            p.terminate()
            return f"✅ Terminated process {name} (PID: {target})."
        else:
            killed = 0
            for p in psutil.process_iter(['pid', 'name']):
                if target.lower() in (p.info['name'] or "").lower():
                    p.terminate()
                    killed += 1
            return f"✅ Terminated {killed} process(es) matching '{target}'."
    except Exception as e:
        return f"Failed to terminate process: {e}"


def tool_launch_app(app_name: str) -> str:
    """Launches desktop software on Windows (Notepad, Calculator, VS Code, Spotify, Edge, etc.)."""
    clean = app_name.lower().strip()
    if "calc" in clean:
        subprocess.Popen(["calc.exe"])
        return "✅ Windows Calculator launched."
    elif "notepad" in clean:
        subprocess.Popen(["notepad.exe"])
        return "✅ Windows Notepad launched."
    elif "code" in clean or "vs code" in clean or "vscode" in clean:
        subprocess.Popen(["cmd.exe", "/c", "code", "."], shell=True)
        return "✅ Visual Studio Code launched in current directory."
    elif "spotify" in clean:
        subprocess.Popen(["cmd.exe", "/c", "start", "spotify:"], shell=True)
        return "✅ Spotify launched."
    elif "explorer" in clean or "files" in clean:
        subprocess.Popen(["explorer.exe"])
        return "✅ Windows File Explorer opened."
    elif "terminal" in clean or "powershell" in clean:
        subprocess.Popen(["powershell.exe"])
        return "✅ PowerShell Terminal launched."
    elif "setting" in clean:
        subprocess.Popen(["cmd.exe", "/c", "start", "ms-settings:"], shell=True)
        return "✅ Windows Settings opened."
    else:
        target = re.sub(r'^(open|launch|start|run)\s+', '', clean).strip()
        subprocess.Popen(["cmd.exe", "/c", "start", "", target], shell=True)
        return f"✅ Launched '{target}' via Windows Shell."


def tool_desktop_screenshot(filename: str = "") -> str:
    """Captures a full desktop screenshot and saves to file."""
    fname = filename.strip() or f"screenshot_{int(time.time())}.png"
    if not fname.endswith(".png"):
        fname += ".png"
    dest = os.path.join(os.getcwd(), fname)

    try:
        img = ImageGrab.grab(all_screens=True)
        img.save(dest)
        return f"✅ Full desktop screenshot saved: `{dest}` ({img.width}x{img.height} px)"
    except Exception as e:
        return f"⚠️ Desktop grab unavailable in current display context: {e}"


def tool_clipboard(action_text: str = "") -> str:
    """Reads or copies text to the Windows Clipboard."""
    if action_text.lower().startswith("copy "):
        payload = action_text[5:].strip()
        pyperclip.copy(payload)
        return f"✅ Copied to Windows Clipboard: \"{payload}\""
    else:
        text = pyperclip.paste()
        return f"📋 Windows Clipboard Content:\n\"{text}\""


def tool_powershell(command: str) -> str:
    """Executes a PowerShell command with timeout and captures stdout/stderr."""
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, timeout=12)
        out = res.stdout.strip() or res.stderr.strip()
        return f"### PowerShell Output:\n```powershell\n{out[:2500]}\n```"
    except Exception as e:
        return f"PowerShell error: {e}"


def tool_ping_test(host: str = "google.com") -> str:
    """Tests network latency and connectivity to a remote host."""
    target = host.strip().split()[-1] if host else "8.8.8.8"
    try:
        res = subprocess.run(["ping", "-n", "3", target], capture_output=True, text=True, timeout=8)
        return f"### Ping Results for `{target}`:\n```\n{res.stdout.strip()}\n```"
    except Exception as e:
        return f"Ping test error: {e}"
