from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.colima_start import archive_preboot_pids, main


class ColimaStartupTest(unittest.TestCase):
    def test_archives_only_pid_files_from_an_earlier_boot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            instance = Path(directory)
            stale = instance / "vz.pid"
            stale.write_text("1457\n")  # PID may now belong to an unrelated process.
            os.utime(stale, (100, 100))
            current = instance / "ha.pid"
            current.write_text("10824\n")
            os.utime(current, (300, 300))
            disk = instance / "disk.img"
            disk.write_text("do not touch")

            archive_preboot_pids(instance, boot_time=200)

            self.assertFalse(stale.exists())
            self.assertEqual((instance / "vz.pid.before-boot-200").read_text(), "1457\n")
            self.assertEqual(current.read_text(), "10824\n")
            self.assertEqual(disk.read_text(), "do not touch")

    def test_does_not_follow_pid_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            instance = Path(directory)
            target = instance / "unrelated"
            target.write_text("1457\n")
            os.utime(target, (100, 100))
            (instance / "vz.pid").symlink_to(target)

            archive_preboot_pids(instance, boot_time=200)

            self.assertTrue((instance / "vz.pid").is_symlink())
            self.assertEqual(target.read_text(), "1457\n")

    def test_does_not_overwrite_an_existing_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            instance = Path(directory)
            stale = instance / "vz.pid"
            stale.write_text("1457\n")
            os.utime(stale, (100, 100))
            backup = instance / "vz.pid.before-boot-200"
            backup.write_text("original backup")

            with self.assertRaises(RuntimeError):
                archive_preboot_pids(instance, boot_time=200)

            self.assertTrue(stale.exists())
            self.assertEqual(backup.read_text(), "original backup")

    @patch("scripts.colima_start.subprocess.run")
    def test_healthy_vm_is_not_restarted(self, run) -> None:
        run.return_value.returncode = 0

        self.assertEqual(main(), 0)

        run.assert_called_once_with(
            ["colima", "status", "--profile", "default"], capture_output=True
        )

    @patch("scripts.colima_start.Path.home")
    @patch("scripts.colima_start.subprocess.check_output")
    @patch("scripts.colima_start.subprocess.run")
    def test_failed_start_can_be_retried_after_preboot_cleanup(
        self, run, check_output, home
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home.return_value = Path(directory)
            instance = Path(directory) / ".colima" / "_lima" / "colima"
            instance.mkdir(parents=True)
            stale = instance / "vz.pid"
            stale.write_text("1457\n")
            os.utime(stale, (100, 100))
            check_output.return_value = "{ sec = 200, usec = 0 }"
            run.return_value.returncode = 1

            self.assertEqual(main(), 1)
            self.assertFalse(stale.exists())
            self.assertEqual(main(), 1)  # Next scheduled attempt still runs.

            starts = [call for call in run.call_args_list if "start" in call.args[0]]
            self.assertEqual(len(starts), 2)
