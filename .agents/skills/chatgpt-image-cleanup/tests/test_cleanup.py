from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "cleanup.py"
SPEC = importlib.util.spec_from_file_location("chatgpt_image_cleanup", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
cleanup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleanup)


class CleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_state = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(
            os.environ,
            {"XDG_STATE_HOME": self.temporary_state.name},
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_state.cleanup()

    def write_manifest(
        self,
        *,
        run_id: str = "20260819T000000Z",
        reconciliation_status: str | None = None,
        current_image_count: int | None = None,
        conversations: list[dict[str, object]] | None = None,
    ) -> tuple[Path, dict[str, object]]:
        root = cleanup.state_root()
        path = root / run_id / "manifest.json"
        manifest: dict[str, object] = {
            "run_id": run_id,
            "execution_mode": "fast",
            "image_count": len(conversations or []),
            "conversation_count": len(conversations or []),
            "conversations": conversations or [],
            "reconciliation_status": reconciliation_status,
        }
        if current_image_count is not None:
            manifest["current_image_count"] = current_image_count
        cleanup.atomic_json_write(path, manifest)
        cleanup.atomic_json_write(
            root / "active.json",
            {
                "run_id": run_id,
                "manifest_path": str(path),
            },
        )
        return path, manifest

    def test_build_manifest_deduplicates_images_and_conversations(self) -> None:
        conversation_id = "11111111-1111-1111-1111-111111111111"
        pages = [
            {
                "items": [
                    {"id": "image-1", "conversation_id": conversation_id},
                    {"id": "image-2", "conversation_id": conversation_id},
                ]
            },
            {
                "items": [
                    {"id": "image-2", "conversation_id": conversation_id},
                ]
            },
        ]
        with mock.patch.object(cleanup, "captured_image_pages", return_value=pages):
            result = cleanup.build_manifest("browser", 2, ["1", "2"])

        manifest_path = Path(result["manifest_path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(result["image_count"], 2)
        self.assertEqual(result["conversation_count"], 1)
        self.assertEqual(result["shared_image_excess"], 1)
        self.assertEqual(manifest["execution_mode"], "fast")
        self.assertEqual(stat.S_IMODE(manifest_path.stat().st_mode), 0o600)

    def test_authentication_preflight_rejects_signed_out_session(self) -> None:
        with mock.patch.object(
            cleanup,
            "run_code_json",
            return_value={"authenticated": False},
        ):
            with self.assertRaisesRegex(RuntimeError, "not authenticated"):
                cleanup.require_authenticated_session("browser")

    def test_prepare_refuses_to_replace_unfinished_checkpoint(self) -> None:
        self.write_manifest(
            conversations=[
                {
                    "conversation_id": "11111111-1111-1111-1111-111111111111",
                    "status": "pending",
                }
            ]
        )
        with mock.patch.object(cleanup, "require_authenticated_session") as preflight:
            with self.assertRaisesRegex(RuntimeError, "unfinished cleanup checkpoint"):
                cleanup.prepare_run("browser")
        preflight.assert_not_called()

    def test_prepare_refuses_to_replace_completed_checkpoint(self) -> None:
        self.write_manifest(
            reconciliation_status="complete",
            current_image_count=0,
        )
        with mock.patch.object(cleanup, "require_authenticated_session") as preflight:
            with self.assertRaisesRegex(RuntimeError, "completed cleanup checkpoint"):
                cleanup.prepare_run("browser")
        preflight.assert_not_called()

    def test_checkpoint_requires_fast_execution_format(self) -> None:
        root = cleanup.state_root()
        path = root / "20260819T000000Z" / "manifest.json"
        cleanup.atomic_json_write(
            path,
            {
                "run_id": "20260819T000000Z",
                "conversations": [],
            },
        )
        cleanup.atomic_json_write(
            root / "active.json",
            {
                "run_id": "20260819T000000Z",
                "manifest_path": str(path),
            },
        )
        with self.assertRaisesRegex(RuntimeError, "Unsupported cleanup checkpoint format"):
            cleanup.load_manifest()

    def test_delete_batch_uses_only_fixed_fast_settings_and_timeout(self) -> None:
        captured: dict[str, object] = {}

        def fake_run_code_json(
            session: str,
            source: str,
            *,
            timeout: int,
        ) -> dict[str, object]:
            captured.update({"session": session, "source": source, "timeout": timeout})
            return {"results": [], "delete_calls": 0, "paused_reason": None}

        with mock.patch.object(cleanup, "run_code_json", side_effect=fake_run_code_json):
            cleanup.delete_browser_batch(
                "browser",
                "20260819T000000Z",
                ["11111111-1111-1111-1111-111111111111"],
            )

        source = str(captured["source"])
        self.assertIn('"minimum_delay_ms": 250', source)
        self.assertIn('"maximum_delay_ms": 400', source)
        self.assertIn('"concurrency": 10', source)
        self.assertIn('"request_timeout_ms": 30000', source)
        self.assertIn("new AbortController()", source)
        self.assertIn("codex.chatgpt-image-cleanup.journal", source)
        self.assertIn("retryAfterHeader === null", source)
        self.assertEqual(captured["timeout"], cleanup.BATCH_CLI_TIMEOUT_SECONDS)

    def test_run_all_stops_and_reports_unexpected_response(self) -> None:
        before = {
            "run_id": "20260819T000000Z",
            "statuses": {"pending": 20},
        }
        paused = {
            "run_id": "20260819T000000Z",
            "statuses": {"complete": 9, "paused": 1, "pending": 10},
            "batch_completed": 9,
            "delete_calls": 10,
            "paused_reason": "unexpected_http_status",
        }
        output = StringIO()
        with (
            mock.patch.object(cleanup, "manifest_status", return_value=before),
            mock.patch.object(cleanup, "run_batch", return_value=paused) as run_batch,
            redirect_stdout(output),
        ):
            result = cleanup.run_all("browser", "20260819T000000Z")

        self.assertEqual(result["run_status"], "paused")
        self.assertEqual(result["paused_reason"], "unexpected_http_status")
        self.assertIn('"remaining_conversations": 11', output.getvalue())
        run_batch.assert_called_once_with("browser", "20260819T000000Z")

    def test_run_all_streams_each_successful_batch(self) -> None:
        initial = {
            "run_id": "20260819T000000Z",
            "statuses": {"pending": 25},
        }
        after_first = {
            "run_id": "20260819T000000Z",
            "statuses": {"complete": 20, "pending": 5},
        }
        complete = {
            "run_id": "20260819T000000Z",
            "statuses": {"complete": 25},
        }
        first_batch = {
            **after_first,
            "batch_completed": 20,
            "delete_calls": 20,
            "paused_reason": None,
        }
        second_batch = {
            **complete,
            "batch_completed": 5,
            "delete_calls": 5,
            "paused_reason": None,
        }
        output = StringIO()
        with (
            mock.patch.object(
                cleanup,
                "manifest_status",
                side_effect=[initial, after_first, complete],
            ),
            mock.patch.object(
                cleanup,
                "run_batch",
                side_effect=[first_batch, second_batch],
            ),
            redirect_stdout(output),
        ):
            result = cleanup.run_all("browser", "20260819T000000Z")

        self.assertEqual(result["run_status"], "complete")
        self.assertEqual(result["batches"], 2)
        self.assertEqual(output.getvalue().count('"event": "batch"'), 2)

    def test_verify_records_zero_residual_completion(self) -> None:
        self.write_manifest(
            conversations=[
                {
                    "conversation_id": "11111111-1111-1111-1111-111111111111",
                    "status": "complete",
                }
            ]
        )
        with (
            mock.patch.object(cleanup, "require_authenticated_session"),
            mock.patch.object(
                cleanup,
                "load_gallery",
                return_value={"image_count": 0, "request_ids": ["1"]},
            ),
            mock.patch.object(
                cleanup,
                "captured_image_pages",
                return_value=[{"items": []}],
            ),
        ):
            result = cleanup.verify_and_reconcile("browser")

        self.assertEqual(result["residual_images"], 0)
        self.assertEqual(result["reconciliation_status"], "complete")

    def test_clear_state_requires_and_removes_only_completed_checkpoint(self) -> None:
        path, _ = self.write_manifest(
            reconciliation_status="complete",
            current_image_count=0,
        )
        result = cleanup.clear_completed_state("20260819T000000Z")

        self.assertTrue(result["state_removed"])
        self.assertFalse(path.exists())
        self.assertFalse((cleanup.state_root() / "active.json").exists())
        self.assertTrue(cleanup.state_root().exists())

    def test_clear_state_refuses_unverified_checkpoint(self) -> None:
        path, _ = self.write_manifest(reconciliation_status="pending")
        with self.assertRaisesRegex(RuntimeError, "zero-residual"):
            cleanup.clear_completed_state("20260819T000000Z")
        self.assertTrue(path.exists())

    def test_cli_timeout_is_sanitized(self) -> None:
        with mock.patch.object(
            cleanup.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["playwright-cli"], 60),
        ):
            with self.assertRaisesRegex(RuntimeError, "playwright-cli timed out"):
                cleanup.run_cli("browser", "snapshot")

    def test_parser_exposes_only_compact_workflow(self) -> None:
        subparsers = next(
            action
            for action in cleanup.parser()._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        self.assertEqual(
            set(subparsers.choices),
            {"prepare", "run-all", "verify", "clear-state", "status"},
        )


if __name__ == "__main__":
    unittest.main()
