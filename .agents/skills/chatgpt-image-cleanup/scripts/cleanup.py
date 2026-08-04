#!/usr/bin/env python3
"""Build and inspect resumable ChatGPT Images cleanup checkpoints."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile
import time
from typing import Any


IMAGE_REQUEST_RE = re.compile(
    r"^(\d+)\. \[GET\] "
    r"https://chatgpt\.com/backend-api/my/recent/image_gen\?.* => \[200\]\s*$"
)
CONVERSATION_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def state_root() -> Path:
    configured = os.environ.get("XDG_STATE_HOME")
    root = Path(configured).expanduser() if configured else Path.home() / ".local/state"
    return root / "chatgpt-image-cleanup"


def run_cli(session: str, *args: str) -> str:
    command = ["playwright-cli", f"-s={session}", *args]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"playwright-cli failed: {detail}")
    return completed.stdout


def run_code_json(session: str, source: str) -> dict[str, Any]:
    raw = run_cli(session, "--raw", "run-code", source).strip()
    value: Any = json.loads(raw)
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise RuntimeError("Unexpected playwright-cli run-code result")
    return value


def captured_image_request_ids(session: str) -> list[str]:
    request_log = run_cli(session, "requests")
    return [
        match.group(1)
        for line in request_log.splitlines()
        if (match := IMAGE_REQUEST_RE.match(line))
    ]


def captured_image_pages(
    session: str,
    request_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    request_ids = request_ids or captured_image_request_ids(session)
    if not request_ids:
        raise RuntimeError(
            "No captured image_gen responses found. Open the Images page and load "
            "the complete gallery first."
        )

    pages: list[dict[str, Any]] = []
    for request_id in request_ids:
        raw = run_cli(session, "--raw", "response-body", request_id)
        page = json.loads(raw)
        if not isinstance(page, dict) or not isinstance(page.get("items"), list):
            raise RuntimeError(f"Unexpected image response schema for request {request_id}")
        pages.append(page)
    return pages


def atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.chmod(0o600)
    os.replace(temp_path, path)


def load_manifest() -> tuple[Path, dict[str, Any]]:
    path = active_manifest_path()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise RuntimeError("Unsupported cleanup checkpoint schema")
    return path, manifest


def build_manifest(session: str, expected_images: int | None) -> dict[str, Any]:
    pages = captured_image_pages(session)
    images_by_id: dict[str, dict[str, Any]] = {}
    ordered_image_ids: list[str] = []

    for page in pages:
        for item in page["items"]:
            if not isinstance(item, dict):
                raise RuntimeError("Unexpected non-object image item")
            image_id = item.get("id")
            conversation_id = item.get("conversation_id")
            if not isinstance(image_id, str) or not image_id:
                raise RuntimeError("Image item is missing an id")
            if not isinstance(conversation_id, str) or not CONVERSATION_ID_RE.fullmatch(
                conversation_id
            ):
                raise RuntimeError(f"Image {image_id} has an invalid conversation_id")
            if image_id not in images_by_id:
                images_by_id[image_id] = item
                ordered_image_ids.append(image_id)

    if expected_images is not None and len(images_by_id) != expected_images:
        raise RuntimeError(
            f"Expected {expected_images} unique images, captured {len(images_by_id)}"
        )

    counts: dict[str, int] = {}
    conversation_order: list[str] = []
    for image_id in ordered_image_ids:
        conversation_id = images_by_id[image_id]["conversation_id"]
        if conversation_id not in counts:
            counts[conversation_id] = 0
            conversation_order.append(conversation_id)
        counts[conversation_id] += 1

    canary_id = next(
        (conversation_id for conversation_id in conversation_order if counts[conversation_id] == 1),
        None,
    )
    if canary_id is None:
        raise RuntimeError("No single-image conversation is available for the canary")

    created_at = utc_now()
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = state_root() / run_id
    manifest_path = run_dir / "manifest.json"
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "session": session,
        "source": "captured_image_gen_responses",
        "created_at": created_at,
        "updated_at": created_at,
        "captured_pages": len(pages),
        "image_count": len(images_by_id),
        "conversation_count": len(counts),
        "canary_conversation_id": canary_id,
        "canary_status": "pending",
        "conversations": [
            {
                "conversation_id": conversation_id,
                "image_count": counts[conversation_id],
                "status": "pending",
                "attempts": 0,
                "last_http_status": None,
                "updated_at": created_at,
            }
            for conversation_id in conversation_order
        ],
    }
    atomic_json_write(manifest_path, manifest)

    active_path = state_root() / "active.json"
    atomic_json_write(
        active_path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "manifest_path": str(manifest_path),
            "updated_at": created_at,
        },
    )
    return {
        "run_id": run_id,
        "manifest_path": str(manifest_path),
        "captured_pages": len(pages),
        "image_count": len(images_by_id),
        "conversation_count": len(counts),
        "shared_image_excess": len(images_by_id) - len(counts),
        "canary_conversation_id": canary_id,
    }


def active_manifest_path() -> Path:
    active_path = state_root() / "active.json"
    if not active_path.exists():
        raise RuntimeError("No active cleanup checkpoint exists")
    active = json.loads(active_path.read_text(encoding="utf-8"))
    manifest_path = active.get("manifest_path")
    if not isinstance(manifest_path, str):
        raise RuntimeError("The active checkpoint has an invalid manifest path")
    return Path(manifest_path)


def manifest_status() -> dict[str, Any]:
    path, manifest = load_manifest()
    statuses: dict[str, int] = {}
    for conversation in manifest.get("conversations", []):
        status = conversation.get("status", "unknown")
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "run_id": manifest.get("run_id"),
        "manifest_path": str(path),
        "image_count": manifest.get("image_count"),
        "conversation_count": manifest.get("conversation_count"),
        "canary_status": manifest.get("canary_status"),
        "reconciliation_status": manifest.get("reconciliation_status"),
        "statuses": statuses,
    }


def record_canary(
    delete_http_status: int,
    image_count_after: int,
    conversation_get_status: int,
) -> dict[str, Any]:
    path, manifest = load_manifest()
    canary_id = manifest.get("canary_conversation_id")
    if not isinstance(canary_id, str) or not CONVERSATION_ID_RE.fullmatch(canary_id):
        raise RuntimeError("The active checkpoint has an invalid canary id")

    expected_after = manifest.get("image_count") - 1
    if image_count_after != expected_after:
        raise RuntimeError(
            f"Expected {expected_after} images after canary, observed {image_count_after}"
        )
    if delete_http_status != 200 or conversation_get_status != 404:
        raise RuntimeError("Canary verification did not match the required 200/404 statuses")

    conversation = next(
        (
            item
            for item in manifest.get("conversations", [])
            if item.get("conversation_id") == canary_id
        ),
        None,
    )
    if conversation is None or conversation.get("image_count") != 1:
        raise RuntimeError("The canary is not a single-image conversation in the manifest")

    updated_at = utc_now()
    conversation.update(
        {
            "status": "complete",
            "attempts": max(1, int(conversation.get("attempts", 0))),
            "last_http_status": delete_http_status,
            "updated_at": updated_at,
        }
    )
    manifest.update(
        {
            "updated_at": updated_at,
            "canary_status": "verified",
            "image_count_after_canary": image_count_after,
            "verified_delete_request": {
                "method": "DELETE",
                "path_template": "/backend-api/conversation/id/{conversation_id}",
                "body": None,
                "success_status": delete_http_status,
            },
            "canary_verification": {
                "conversation_get_status": conversation_get_status,
                "verified_at": updated_at,
            },
        }
    )
    atomic_json_write(path, manifest)
    return manifest_status()


def load_gallery(session: str) -> dict[str, Any]:
    before_request_ids = set(captured_image_request_ids(session))
    run_cli(session, "goto", "https://chatgpt.com/images")
    source = r"""async page => {
      let stable = 0;
      let last = await page.getByRole('button', {name: /^Open image:/}).count();
      let iterations = 0;
      for (; iterations < 200 && stable < 8; iterations++) {
        const before = last;
        await page.evaluate(() => {
          const main = document.querySelector('main#main');
          const scroller = [...document.querySelectorAll('*')].find(
            element => element !== main && element.contains(main) &&
              element.scrollHeight > element.clientHeight + 10
          );
          if (scroller) {
            scroller.scrollTop = Math.max(
              0,
              scroller.scrollHeight - scroller.clientHeight - 600
            );
          }
        });
        await page.waitForTimeout(150);
        await page.evaluate(() => {
          const main = document.querySelector('main#main');
          const scroller = [...document.querySelectorAll('*')].find(
            element => element !== main && element.contains(main) &&
              element.scrollHeight > element.clientHeight + 10
          );
          if (scroller) scroller.scrollTop = scroller.scrollHeight;
        });
        await page.waitForTimeout(900);
        last = await page.getByRole('button', {name: /^Open image:/}).count();
        stable = last === before ? stable + 1 : 0;
      }
      return JSON.stringify({image_count: last, iterations, stable});
    }"""
    result = run_code_json(session, source)
    if result.get("stable") != 8:
        raise RuntimeError("Gallery loading did not reach a stable image count")
    after_request_ids = captured_image_request_ids(session)
    new_request_ids = [
        request_id for request_id in after_request_ids if request_id not in before_request_ids
    ]
    result["request_ids"] = new_request_ids or after_request_ids
    return result


def delete_request(session: str, conversation_id: str) -> dict[str, Any]:
    if not CONVERSATION_ID_RE.fullmatch(conversation_id):
        raise RuntimeError("Refusing to delete an invalid conversation id")
    source = f"""async page => {{
      const response = await page.request.delete(
        'https://chatgpt.com/backend-api/conversation/id/{conversation_id}',
        {{headers: {{referer: 'https://chatgpt.com/'}}}}
      );
      const headers = response.headers();
      return JSON.stringify({{
        status: response.status(),
        retry_after: headers['retry-after'] || null
      }});
    }}"""
    result = run_code_json(session, source)
    status = result.get("status")
    if not isinstance(status, int):
        raise RuntimeError("Deletion returned an unexpected response schema")
    retry_after = result.get("retry_after")
    if retry_after is not None and not isinstance(retry_after, str):
        raise RuntimeError("Deletion returned an invalid Retry-After value")
    return result


def retry_delay(retry_after: str | None, attempt: int) -> float:
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return min(60.0, (2 ** max(0, attempt - 1)) + random.uniform(0.0, 1.0))


def save_attempt(
    path: Path,
    manifest: dict[str, Any],
    conversation: dict[str, Any],
    status: str,
    http_status: int | None,
    error_code: str | None,
) -> None:
    updated_at = utc_now()
    conversation.update(
        {
            "status": status,
            "attempts": int(conversation.get("attempts", 0)) + 1,
            "last_http_status": http_status,
            "last_error_code": error_code,
            "updated_at": updated_at,
        }
    )
    manifest["updated_at"] = updated_at
    atomic_json_write(path, manifest)


def run_batch(
    session: str,
    confirmed_run_id: str,
    limit: int,
    minimum_delay: float,
    maximum_delay: float,
) -> dict[str, Any]:
    path, manifest = load_manifest()
    if manifest.get("run_id") != confirmed_run_id:
        raise RuntimeError("--confirm-run-id does not match the active checkpoint")
    if manifest.get("canary_status") != "verified":
        raise RuntimeError("A verified canary is required before bulk deletion")
    verified = manifest.get("verified_delete_request", {})
    if verified.get("method") != "DELETE" or verified.get("path_template") != (
        "/backend-api/conversation/id/{conversation_id}"
    ):
        raise RuntimeError("The checkpoint does not contain the verified delete request")
    if not 1 <= limit <= 20:
        raise RuntimeError("Batch limit must be between 1 and 20")
    if not 0.8 <= minimum_delay <= maximum_delay:
        raise RuntimeError("Delay range must start at 0.8 seconds or slower")

    candidates = [
        item
        for item in manifest.get("conversations", [])
        if item.get("status") in {"pending", "pending_reconcile", "retryable"}
    ][:limit]
    completed = 0
    calls = 0
    paused_reason: str | None = None

    for index, conversation in enumerate(candidates):
        if index > 0:
            time.sleep(random.uniform(minimum_delay, maximum_delay))
        conversation_id = conversation["conversation_id"]
        per_item_attempts = 0

        while per_item_attempts < 3:
            per_item_attempts += 1
            try:
                result = delete_request(session, conversation_id)
                calls += 1
                http_status = result["status"]
            except (RuntimeError, json.JSONDecodeError) as error:
                save_attempt(
                    path,
                    manifest,
                    conversation,
                    "retryable",
                    None,
                    "network_or_cli_failure",
                )
                if per_item_attempts >= 3:
                    paused_reason = "three_consecutive_failures"
                    break
                time.sleep(retry_delay(None, per_item_attempts))
                continue

            if http_status in {200, 204, 404}:
                save_attempt(path, manifest, conversation, "complete", http_status, None)
                completed += 1
                break

            if http_status == 429:
                save_attempt(
                    path,
                    manifest,
                    conversation,
                    "retryable",
                    http_status,
                    "rate_limited",
                )
                delay = retry_delay(result.get("retry_after"), per_item_attempts)
                if delay > 60 or per_item_attempts >= 3:
                    paused_reason = "rate_limited"
                    break
                time.sleep(delay)
                continue

            if 500 <= http_status <= 599:
                save_attempt(
                    path,
                    manifest,
                    conversation,
                    "retryable",
                    http_status,
                    "server_error",
                )
                if per_item_attempts >= 3:
                    paused_reason = "three_consecutive_failures"
                    break
                time.sleep(retry_delay(None, per_item_attempts))
                continue

            error_code = (
                "authentication_failed"
                if http_status in {401, 403}
                else "unexpected_http_status"
            )
            save_attempt(
                path,
                manifest,
                conversation,
                "paused",
                http_status,
                error_code,
            )
            paused_reason = error_code
            break

        if paused_reason:
            break

    summary = manifest_status()
    summary.update(
        {
            "batch_completed": completed,
            "delete_calls": calls,
            "paused_reason": paused_reason,
        }
    )
    return summary


def verify_and_reconcile(session: str) -> dict[str, Any]:
    gallery = load_gallery(session)
    pages = captured_image_pages(session, gallery["request_ids"])
    residual_images: dict[str, str] = {}
    residual_counts: dict[str, int] = {}
    for page in pages:
        for item in page["items"]:
            image_id = item.get("id")
            conversation_id = item.get("conversation_id")
            if not isinstance(image_id, str) or not isinstance(conversation_id, str):
                raise RuntimeError("Residual image response has an invalid schema")
            residual_images[image_id] = conversation_id
    for conversation_id in residual_images.values():
        residual_counts[conversation_id] = residual_counts.get(conversation_id, 0) + 1
    if gallery["image_count"] != len(residual_images):
        raise RuntimeError(
            "Gallery DOM count does not match the captured response manifest"
        )

    path, manifest = load_manifest()
    passes = manifest.setdefault("reconciliation_passes", [])
    if len(passes) >= 3:
        raise RuntimeError("The checkpoint already reached three reconciliation passes")
    residual_ids = sorted(residual_counts)
    previous_ids = passes[-1].get("conversation_ids", []) if passes else []
    updated_at = utc_now()
    status = "complete" if not residual_ids else "pending"
    if residual_ids and residual_ids == previous_ids:
        status = "stalled"

    conversations = {
        item["conversation_id"]: item for item in manifest.get("conversations", [])
    }
    if status == "pending":
        for conversation_id in residual_ids:
            existing = conversations.get(conversation_id)
            if existing is None:
                existing = {
                    "conversation_id": conversation_id,
                    "image_count": residual_counts[conversation_id],
                    "status": "pending_reconcile",
                    "attempts": 0,
                    "last_http_status": None,
                    "updated_at": updated_at,
                }
                manifest["conversations"].append(existing)
            elif existing.get("status") == "complete":
                existing.update(
                    {
                        "status": "pending_reconcile",
                        "image_count": residual_counts[conversation_id],
                        "updated_at": updated_at,
                    }
                )

    passes.append(
        {
            "pass": len(passes) + 1,
            "verified_at": updated_at,
            "image_count": len(residual_images),
            "conversation_count": len(residual_ids),
            "conversation_ids": residual_ids,
            "status": status,
        }
    )
    manifest.update(
        {
            "updated_at": updated_at,
            "current_image_count": len(residual_images),
            "reconciliation_status": status,
        }
    )
    atomic_json_write(path, manifest)
    summary = manifest_status()
    summary.update(
        {
            "gallery_image_count": gallery["image_count"],
            "residual_images": len(residual_images),
            "residual_conversations": len(residual_ids),
        }
    )
    return summary


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Manage resumable ChatGPT Images cleanup checkpoints"
    )
    subparsers = result.add_subparsers(dest="command", required=True)

    manifest = subparsers.add_parser(
        "manifest-from-capture",
        help="Build a manifest from responses already captured by playwright-cli",
    )
    manifest.add_argument("--session", default="browser")
    manifest.add_argument("--expected-images", type=int)

    canary = subparsers.add_parser(
        "record-canary",
        help="Record a successfully verified single-conversation canary",
    )
    canary.add_argument("--delete-http-status", type=int, required=True)
    canary.add_argument("--image-count-after", type=int, required=True)
    canary.add_argument("--conversation-get-status", type=int, required=True)

    load = subparsers.add_parser(
        "load-gallery",
        help="Open Images and load its complete authenticated cursor feed",
    )
    load.add_argument("--session", default="browser")

    run = subparsers.add_parser(
        "run-batch",
        help="Delete one confirmed resumable batch of at most 20 conversations",
    )
    run.add_argument("--session", default="browser")
    run.add_argument("--confirm-run-id", required=True)
    run.add_argument("--limit", type=int, default=20)
    run.add_argument("--minimum-delay", type=float, default=0.8)
    run.add_argument("--maximum-delay", type=float, default=1.2)

    verify = subparsers.add_parser(
        "verify",
        help="Reload the gallery and reconcile residual conversation ids",
    )
    verify.add_argument("--session", default="browser")

    subparsers.add_parser("status", help="Show a sanitized active-run summary")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "manifest-from-capture":
            output = build_manifest(args.session, args.expected_images)
        elif args.command == "record-canary":
            output = record_canary(
                args.delete_http_status,
                args.image_count_after,
                args.conversation_get_status,
            )
        elif args.command == "load-gallery":
            output = load_gallery(args.session)
        elif args.command == "run-batch":
            output = run_batch(
                args.session,
                args.confirm_run_id,
                args.limit,
                args.minimum_delay,
                args.maximum_delay,
            )
        elif args.command == "verify":
            output = verify_and_reconcile(args.session)
        else:
            output = manifest_status()
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
