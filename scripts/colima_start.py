"""Start the default Colima VM, recovering PID files left by an earlier boot."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def archive_preboot_pids(instance: Path, boot_time: int) -> None:
    # A process cannot survive a reboot. Never touch current-boot PID files,
    # kill a process by PID, follow symlinks, or modify VM disks/configuration.
    for name in ("vz.pid", "ha.pid"):
        pid_file = instance / name
        if pid_file.is_symlink() or not pid_file.is_file():
            continue
        if pid_file.stat().st_mtime >= boot_time:
            continue
        backup = instance / f"{name}.before-boot-{boot_time}"
        if backup.exists() or backup.is_symlink():
            raise RuntimeError(f"Refusing to overwrite {backup}")
        pid_file.rename(backup)
        print(f"Archived pre-boot PID file: {pid_file} -> {backup}", flush=True)


def main() -> int:
    if subprocess.run(
        ["colima", "status", "--profile", "default"], capture_output=True
    ).returncode == 0:
        return 0
    boot = subprocess.check_output(
        ["/usr/sbin/sysctl", "-n", "kern.boottime"], text=True
    )
    match = re.search(r"\bsec\s*=\s*(\d+)", boot)
    if not match:
        raise RuntimeError("Cannot determine boot time; refusing PID cleanup")
    archive_preboot_pids(
        Path.home() / ".colima" / "_lima" / "colima", int(match.group(1))
    )
    return subprocess.run(["colima", "start", "--profile", "default"]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
