#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import select
import socket
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


HOST = os.environ.get("TTYD_MOBILE_HOST", "127.0.0.1")
PORT = int(os.environ.get("TTYD_MOBILE_PORT", "7681"))
TTYD_BACKEND_HOST = os.environ.get("TTYD_BACKEND_HOST", "127.0.0.1")
TTYD_PORT = os.environ.get("TTYD_PORT", "7682")
TMUX_TARGET = os.environ.get("TTYD_TMUX_TARGET") or os.environ.get(
    "TTYD_TMUX_SESSION", "remote"
)
TMUX_BIN = os.environ.get("TMUX_BIN", "tmux")


HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, user-scalable=no">
<title>tmux</title>
<style>
html, body {{
  height: 100%;
  margin: 0;
  overflow: hidden;
  background: #000;
  color: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif;
}}
iframe {{
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
  background: #000;
}}
.rail {{
  position: fixed;
  top: env(safe-area-inset-top, 0);
  right: 0;
  bottom: env(safe-area-inset-bottom, 0);
  width: 34px;
  z-index: 10;
  touch-action: none;
}}
.panel {{
  position: fixed;
  right: 38px;
  bottom: calc(env(safe-area-inset-bottom, 0) + 10px);
  z-index: 11;
  display: grid;
  grid-template-columns: repeat(3, 44px);
  gap: 6px;
}}
button {{
  width: 44px;
  height: 36px;
  border: 1px solid rgba(255,255,255,.28);
  border-radius: 7px;
  background: rgba(20,20,20,.72);
  color: #fff;
  font: 600 11px -apple-system, BlinkMacSystemFont, sans-serif;
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
}}
button:active {{
  background: rgba(80,80,80,.82);
}}
</style>
</head>
<body>
<iframe src="/ttyd/"></iframe>
<div class="rail" id="rail"></div>
<div class="panel">
  <button data-action="page-up">PGUP</button>
  <button data-action="top">TOP</button>
  <button data-action="exit">EXIT</button>
  <button data-action="page-down">PGDN</button>
  <button data-action="bottom">BOT</button>
  <button data-action="status">STAT</button>
</div>
<script>
const rail = document.getElementById('rail');
let lastY = null;
let accum = 0;
let pending = false;

async function call(action, query = '') {{
  try {{
    await fetch(`/api/${{action}}${{query}}`, {{ cache: 'no-store' }});
  }} catch (_) {{}}
}}

function queueScroll(direction, lines) {{
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => {{
    pending = false;
    call('scroll', `?direction=${{direction}}&lines=${{lines}}`);
  }});
}}

rail.addEventListener('touchstart', event => {{
  lastY = event.touches[0].clientY;
  accum = 0;
}}, {{ passive: false }});

rail.addEventListener('touchmove', event => {{
  event.preventDefault();
  const y = event.touches[0].clientY;
  if (lastY === null) {{
    lastY = y;
    return;
  }}
  accum += y - lastY;
  lastY = y;
  const threshold = 18;
  while (Math.abs(accum) >= threshold) {{
    const direction = accum > 0 ? 'up' : 'down';
    queueScroll(direction, 4);
    accum += accum > 0 ? -threshold : threshold;
  }}
}}, {{ passive: false }});

rail.addEventListener('touchend', () => {{
  lastY = null;
  accum = 0;
}});

document.querySelectorAll('button[data-action]').forEach(button => {{
  button.addEventListener('click', () => call(button.dataset.action));
}});
</script>
</body>
</html>
"""


def run_tmux(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [TMUX_BIN, *args],
        capture_output=True,
        text=True,
        env={**os.environ, "LANG": "ko_KR.UTF-8", "LC_ALL": "ko_KR.UTF-8"},
    )


def pane_in_mode() -> bool:
    result = run_tmux("display-message", "-p", "-t", TMUX_TARGET, "#{pane_in_mode}")
    return result.returncode == 0 and result.stdout.strip() == "1"


def ensure_copy_mode(direction: str) -> None:
    if pane_in_mode():
        return
    flag = "-u" if direction == "up" else "-d"
    run_tmux("copy-mode", flag, "-t", TMUX_TARGET)


def send_copy_command(*args: str) -> None:
    run_tmux("send-keys", "-t", TMUX_TARGET, "-X", *args)


def handle_action(action: str, params: dict[str, list[str]]) -> tuple[int, dict[str, object]]:
    if action == "scroll":
        direction = params.get("direction", ["up"])[0]
        if direction not in {"up", "down"}:
            return 400, {"ok": False, "error": "invalid direction"}
        try:
            lines = max(1, min(50, int(params.get("lines", ["5"])[0])))
        except ValueError:
            lines = 5
        ensure_copy_mode(direction)
        command = "scroll-up" if direction == "up" else "scroll-down"
        send_copy_command("-N", str(lines), command)
        return 200, {"ok": True}

    if action == "page-up":
        ensure_copy_mode("up")
        send_copy_command("page-up")
        return 200, {"ok": True}

    if action == "page-down":
        ensure_copy_mode("down")
        send_copy_command("page-down")
        return 200, {"ok": True}

    if action == "top":
        ensure_copy_mode("up")
        send_copy_command("history-top")
        return 200, {"ok": True}

    if action == "bottom":
        ensure_copy_mode("down")
        send_copy_command("history-bottom")
        return 200, {"ok": True}

    if action == "exit":
        if pane_in_mode():
            send_copy_command("cancel")
        return 200, {"ok": True}

    if action == "status":
        return 200, {"ok": True, "target": TMUX_TARGET, "pane_in_mode": pane_in_mode()}

    return 404, {"ok": False, "error": "unknown action"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def proxy_ttyd(self) -> None:
        try:
            backend = socket.create_connection((TTYD_BACKEND_HOST, int(TTYD_PORT)), timeout=10)
        except OSError:
            self.send_response(502)
            self.end_headers()
            return

        with backend:
            upgrade = self.headers.get("Upgrade", "").lower() == "websocket"
            request = f"{self.command} {self.path} {self.request_version}\r\n"
            for key, value in self.headers.items():
                key_lower = key.lower()
                if key_lower == "host":
                    value = f"{TTYD_BACKEND_HOST}:{TTYD_PORT}"
                if key_lower in {"connection", "proxy-connection"}:
                    continue
                request += f"{key}: {value}\r\n"
            if upgrade:
                request += "Connection: Upgrade\r\n"
            else:
                request += "Connection: close\r\n"
            request += "\r\n"
            backend.sendall(request.encode("iso-8859-1"))

            sockets = [self.connection, backend]
            while True:
                readable, _, _ = select.select(sockets, [], [], 60)
                if not readable:
                    continue
                for source in readable:
                    try:
                        data = source.recv(65536)
                    except OSError:
                        return
                    if not data:
                        return
                    target = backend if source is self.connection else self.connection
                    try:
                        target.sendall(data)
                    except OSError:
                        return

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/ttyd/") or parsed.path == "/ttyd":
            self.proxy_ttyd()
            return
        if parsed.path in {"/", "/index.html"}:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(HTML.encode())))
            self.end_headers()
            return
        if parsed.path.startswith("/api/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/ttyd":
            self.send_response(302)
            self.send_header("Location", "/ttyd/")
            self.end_headers()
            return
        if parsed.path.startswith("/ttyd/"):
            self.proxy_ttyd()
            return
        if parsed.path in {"/", "/index.html"}:
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path.startswith("/api/"):
            action = parsed.path.removeprefix("/api/").strip("/")
            status, payload = handle_action(action, parse_qs(parsed.query))
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
