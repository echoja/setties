from __future__ import annotations

import json
import os
import re
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .utils import repo_root


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    actual: str


def _expand_value(value: object) -> object:
    if isinstance(value, str):
        return value.replace("$HOME", str(Path.home())).replace(
            "$UID", str(os.getuid())
        )
    if isinstance(value, list):
        return [_expand_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_value(item) for key, item in value.items()}
    return value


def load_check_entries() -> list[dict]:
    checks_file = repo_root() / "scripts" / "checks.json"
    with open(checks_file, encoding="utf-8") as f:
        data = json.load(f)
    entries: list[dict] = []
    for entry in data["checks"]:
        expanded = _expand_value(entry)
        if not isinstance(expanded, dict):
            raise TypeError("system check entries must be objects")
        entries.append(expanded)
    return entries


def _run_tcp_check(entry: dict) -> str:
    try:
        with socket.create_connection(
            (entry["host"], entry["port"]), timeout=1.0
        ):
            return "open"
    except (OSError, TimeoutError):
        return "closed"


def _run_launchd_check(entry: dict) -> str:
    domain = "system" if entry["domain"] == "system" else f"gui/{os.getuid()}"
    try:
        result = subprocess.run(
            ["launchctl", "print-disabled", domain],
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unavailable"
    if result.returncode != 0:
        return f"error (exit {result.returncode})"

    pattern = rf'"{re.escape(entry["service"])}"\s*=>\s*(enabled|disabled)'
    match = re.search(pattern, result.stdout)
    return match.group(1) if match else "enabled"


def _run_process_check(entry: dict) -> str:
    try:
        result = subprocess.run(
            ["pgrep", "-f", entry["pattern"]],
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unavailable"
    if result.returncode == 0:
        return "running"
    if result.returncode == 1:
        return "stopped"
    return f"error (exit {result.returncode})"


def _run_command_check(entry: dict) -> str:
    try:
        result = subprocess.run(
            entry["argv"], capture_output=True, text=True
        )
    except OSError:
        return "unavailable"
    return "success" if result.returncode == 0 else "failure"


def run_check(entry: dict) -> CheckResult:
    runners = {
        "tcp": _run_tcp_check,
        "launchd": _run_launchd_check,
        "process": _run_process_check,
        "command": _run_command_check,
    }
    kind = entry["kind"]
    runner = runners.get(kind)
    if runner is None:
        raise ValueError(f"unknown system check kind: {kind}")
    actual = runner(entry)
    return CheckResult(ok=actual == entry["expected"], actual=actual)
