#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webui.py - Browser health dashboard for COMAC AgentOS
Stdlib only. http.server + ThreadingHTTPServer. Single HTML page with
5s auto-refresh. Port: 8080 (override via WEBUI_PORT env var).
"""
import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROV_FILE = SCRIPT_DIR / "providers.json"
PORT = int(os.environ.get("WEBUI_PORT", "8080"))


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>COMAC AgentOS - Dashboard</title>
<meta http-equiv="refresh" content="5">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #0e1117; color: #e6edf3; padding: 24px; }
h1 { font-size: 22px; margin-bottom: 4px; color: #58a6ff; }
.subtitle { color: #8b949e; font-size: 13px; margin-bottom: 20px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
.card h2 { font-size: 13px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; font-weight: 600; }
.row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #21262d; font-size: 14px; align-items: center; }
.row:last-child { border-bottom: none; }
.label { color: #8b949e; }
.value { color: #e6edf3; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; }
.tag { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.03em; }
.tag-on { background: #0e4429; color: #3fb950; }
.tag-off { background: #4a0e1a; color: #f85149; }
.tag-dis { background: #21262d; color: #8b949e; }
.metric { font-size: 24px; font-weight: 700; color: #58a6ff; margin: 4px 0; }
.metric-label { font-size: 12px; color: #8b949e; }
footer { margin-top: 20px; text-align: center; color: #6e7681; font-size: 11px; }
</style>
</head>
<body>
<h1>COMAC AgentOS - Dashboard</h1>
<div class="subtitle">__TIMESTAMP__ &middot; auto-refresh 5s</div>
<div class="grid">
__PROV_CARD__
__SYS_CARD__
__WD_CARD__
</div>
<footer>Port __PORT__ &middot; stdlib only &middot; no JS framework</footer>
</body>
</html>
"""


def get_providers():
    if not PROV_FILE.exists():
        return []
    try:
        cfg = json.loads(PROV_FILE.read_text(encoding="utf-8"))
        return cfg.get("providers", [])
    except Exception:
        return []


def check_port(host, port, timeout=1.5):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, int(port)))
            return True
    except Exception:
        return False


def check_disk():
    try:
        total, used, free = shutil.disk_usage(SCRIPT_DIR)
        return free / (1024 ** 3), total / (1024 ** 3), (used / total * 100) if total else 0
    except Exception:
        return 0, 0, 0


def check_watchdog():
    if sys.platform != "win32":
        return None, "non-Windows"
    try:
        out = subprocess.run(
            ["tasklist", "/fi", "WINDOWTITLE eq COMAC-Watchdog"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=3,
        ).stdout or ""
        if "cmd.exe" in out:
            return True, "running"
        return False, "not running"
    except Exception as e:
        return None, str(e)


def build_providers_card():
    providers = get_providers()
    if not providers:
        return '<div class="card"><h2>Providers</h2><div class="row"><span class="value err">No providers configured</span></div></div>'
    rows = []
    for p in providers:
        pid = p.get("id", "?")
        ptype = p.get("type", "?")
        display = p.get("display", pid)
        enabled = p.get("enabled", True)
        host = p.get("host", "127.0.0.1")
        port = p.get("port")

        if not enabled:
            tag = '<span class="tag tag-dis">DISABLED</span>'
        elif port:
            online = check_port(host, port)
            tag = '<span class="tag tag-on">ONLINE</span>' if online else '<span class="tag tag-off">OFFLINE</span>'
        else:
            tag = '<span class="tag tag-dis">ENABLED</span>'

        rows.append(
            f'<div class="row"><span class="label">{display} <span style="color:#6e7681">({ptype})</span></span>{tag}</div>'
        )
    return '<div class="card"><h2>Providers</h2>' + "\n".join(rows) + '</div>'


def build_system_card():
    free, total, used = check_disk()
    return f"""<div class="card">
<h2>System</h2>
<div class="row"><span class="label">Python</span><span class="value">{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}</span></div>
<div class="row"><span class="label">Platform</span><span class="value">{sys.platform}</span></div>
<div class="row"><span class="label">Disk Free</span><span class="value">{free:.1f} GB</span></div>
<div class="row"><span class="label">Disk Used</span><span class="value">{used:.1f}% of {total:.1f} GB</span></div>
</div>"""


def build_watchdog_card():
    ok_flag, detail = check_watchdog()
    if ok_flag is True:
        status = '<span style="color:#3fb950">RUNNING</span>'
    elif ok_flag is False:
        status = '<span style="color:#f85149">STOPPED</span>'
    else:
        status = '<span style="color:#d29922">N/A</span>'
    return f"""<div class="card">
<h2>Watchdog</h2>
<div class="metric">{status}</div>
<div class="metric-label">{detail}</div>
<div class="row" style="margin-top:12px"><span class="label">Interval</span><span class="value">30s</span></div>
</div>"""


def build_html():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = HTML_PAGE
    html = html.replace("__TIMESTAMP__", ts)
    html = html.replace("__PORT__", str(PORT))
    html = html.replace("__PROV_CARD__", build_providers_card())
    html = html.replace("__SYS_CARD__", build_system_card())
    html = html.replace("__WD_CARD__", build_watchdog_card())
    return html


def collect_status():
    free, total, used = check_disk()
    wd_ok, _ = check_watchdog()
    providers = []
    for p in get_providers():
        pid = p.get("id", "?")
        port = p.get("port")
        host = p.get("host", "127.0.0.1")
        online = None
        if p.get("enabled", True) and port:
            online = check_port(host, port)
        providers.append({
            "id": pid,
            "display": p.get("display", pid),
            "type": p.get("type"),
            "enabled": p.get("enabled", True),
            "online": online,
        })
    return {
        "ts": datetime.now().isoformat(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "disk_free_gb": round(free, 2),
        "disk_used_pct": round(used, 1),
        "watchdog": wd_ok,
        "providers": providers,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # quiet

    def do_GET(self):
        if self.path.startswith("/api/status"):
            payload = json.dumps(collect_status(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
        else:
            body = build_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)


def main():
    print(f"[INFO] COMAC AgentOS - WebUI starting on port {PORT}")
    print(f"[INFO] Open http://127.0.0.1:{PORT} in your browser")
    print(f"[INFO] Press Ctrl+C to stop")
    print()
    try:
        srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    except OSError as e:
        print(f"[FATAL] Cannot bind port {PORT}: {e}")
        print(f"[INFO] Try: set WEBUI_PORT=8090 && webui.bat")
        return 1
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
