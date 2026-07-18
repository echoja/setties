from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from .utils import repo_root

# 이 머신의 active profile 을 읽는 소스. env 가 우선, 없으면 gitignore 밖의 로컬 파일.
PROFILES_ENV = "SETTIES_PROFILES"
PROFILES_FILE = Path.home() / ".config" / "setties" / "profiles"

KIND_PREDICATE: dict[str, Callable[[str], object]] = {
    "command": shutil.which,
    "dir": os.path.isdir,
    "file": os.path.isfile,
}


def load_dep_checks() -> list[dict]:
    checks_file = repo_root() / "scripts" / "deps.json"
    with open(checks_file, encoding="utf-8") as f:
        data = json.load(f)
    home = str(Path.home())
    for check in data["checks"]:
        check["target"] = check["target"].replace("$HOME", home)
    return data["checks"]


def _split_profiles(raw: str) -> set[str]:
    return {p for p in re.split(r"[,\s]+", raw.strip()) if p}


def active_profiles() -> set[str]:
    """이 머신에서 켜진 profile 집합. env(SETTIES_PROFILES)가 우선, 없으면 로컬 파일.

    둘 다 없으면 빈 집합. 빈 집합에서는 profiles 를 요구하는 체크가 비활성(skip)되고,
    아무 selector 없는 universal 체크와 exceptProfiles 체크만 활성이다.
    """
    env = os.environ.get(PROFILES_ENV)
    if env is not None:
        return _split_profiles(env)
    if PROFILES_FILE.is_file():
        return _split_profiles(PROFILES_FILE.read_text(encoding="utf-8"))
    return set()


def check_is_active(check: dict, active: set[str]) -> bool:
    """profiles / exceptProfiles 를 active 집합에 대해 판정.

    active = (profiles 없음 or active ∩ profiles ≠ ∅)
         and (exceptProfiles 없음 or active ∩ exceptProfiles = ∅)
    exceptProfiles 는 hard veto (AND). selector 가 둘 다 없으면 universal.
    """
    return check_inactive_reason(check, active) is None


def check_inactive_reason(check: dict, active: set[str]) -> str | None:
    profiles = check.get("profiles")
    if profiles is not None and not (active & set(profiles)):
        return f"needs profile: {', '.join(sorted(profiles))}"
    matched = sorted(active & set(check.get("exceptProfiles") or []))
    if matched:
        return f"excluded on profile: {', '.join(matched)}"
    return None


def run_update_check(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", "-c", command],
        cwd=repo_root(),
        capture_output=True,
        text=True,
    )
