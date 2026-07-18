from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.bootstrap.checks import load_check_entries, run_check
from scripts.bootstrap.deps import check_is_active
from scripts.bootstrap.validation import check_json_formatting, validate_checks_schema


class SystemChecksTest(unittest.TestCase):
    def test_checks_json_matches_schema(self) -> None:
        self.assertEqual(validate_checks_schema(), [])

    def test_malformed_json_fails_formatting_check_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_json = Path(temp_dir) / "invalid.json"
            invalid_json.write_text("{", encoding="utf-8")

            self.assertFalse(check_json_formatting(invalid_json))

    def test_personal_profile_selects_disabled_remote_checks(self) -> None:
        active_ids = {
            entry["id"]
            for entry in load_check_entries()
            if check_is_active(entry, {"personal"})
        }

        self.assertIn("ssh-disabled", active_ids)
        self.assertIn("screen-sharing-disabled", active_ids)
        self.assertIn("remote-management-disabled", active_ids)
        self.assertIn("cloudflare-tunnel-disabled", active_ids)
        self.assertIn("cloudflare-homebrew-service-disabled", active_ids)
        self.assertIn("cloudflare-tunnel-stopped", active_ids)
        self.assertIn("tailscale-connected", active_ids)
        self.assertNotIn("ssh-enabled", active_ids)
        self.assertNotIn("screen-sharing-enabled", active_ids)

    def test_cloudflare_pattern_covers_tunnel_command_variants(self) -> None:
        entry = next(
            item
            for item in load_check_entries()
            if item["id"] == "cloudflare-tunnel-stopped"
        )
        pattern = re.compile(entry["pattern"])

        self.assertRegex(
            "/opt/homebrew/bin/cloudflared --config config.yml tunnel run",
            pattern,
        )
        self.assertRegex(
            "/opt/homebrew/bin/cloudflared tunnel --url localhost:8000",
            pattern,
        )

    @patch("scripts.bootstrap.checks.socket.create_connection")
    def test_tcp_check_reports_open_port(self, create_connection) -> None:
        result = run_check(
            {
                "kind": "tcp",
                "host": "localhost",
                "port": 22,
                "expected": "open",
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.actual, "open")
        create_connection.assert_called_once_with(("localhost", 22), timeout=1.0)

    @patch("scripts.bootstrap.checks.subprocess.run")
    def test_launchd_check_reads_disabled_override(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            [],
            0,
            stdout='\t\t"com.openssh.sshd" => disabled\n',
            stderr="",
        )

        result = run_check(
            {
                "kind": "launchd",
                "domain": "system",
                "service": "com.openssh.sshd",
                "expected": "disabled",
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.actual, "disabled")

    @patch("scripts.bootstrap.checks.subprocess.run")
    def test_process_check_reports_stopped_process(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="")

        result = run_check(
            {
                "kind": "process",
                "pattern": "cloudflared.*tunnel run",
                "expected": "stopped",
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.actual, "stopped")

    @patch("scripts.bootstrap.checks.subprocess.run")
    def test_command_check_reports_success(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")

        result = run_check(
            {
                "kind": "command",
                "argv": ["example", "status"],
                "expected": "success",
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.actual, "success")


if __name__ == "__main__":
    unittest.main()
