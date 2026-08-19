#!/usr/bin/env python3
"""Build and inspect resumable ChatGPT Images cleanup checkpoints."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any


IMAGE_REQUEST_RE = re.compile(
    r"^(\d+)\. \[GET\] "
    r"https://chatgpt\.com/backend-api/my/recent/image_gen\?.* => \[200\]\s*$"
)
CONVERSATION_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
RUN_ID_RE = re.compile(r"^\d{8}T\d{6}Z$")
FAST_BATCH_LIMIT = 20
FAST_CONCURRENCY = 10
FAST_MINIMUM_DELAY = 0.25
FAST_MAXIMUM_DELAY = 0.4
DELETE_REQUEST_TIMEOUT_MS = 30_000
CLI_TIMEOUT_SECONDS = 60
BATCH_CLI_TIMEOUT_SECONDS = 240


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def state_root() -> Path:
    configured = os.environ.get("XDG_STATE_HOME")
    root = Path(configured).expanduser() if configured else Path.home() / ".local/state"
    return root / "chatgpt-image-cleanup"


def run_cli(
    session: str,
    *args: str,
    timeout: int = CLI_TIMEOUT_SECONDS,
) -> str:
    command = ["playwright-cli", f"-s={session}", *args]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("playwright-cli timed out") from None
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"playwright-cli failed: {detail}")
    return completed.stdout


def run_code_json(
    session: str,
    source: str,
    *,
    timeout: int = CLI_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    raw = run_cli(
        session,
        "--raw",
        "run-code",
        source,
        timeout=timeout,
    ).strip()
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
    if (
        not isinstance(manifest, dict)
        or manifest.get("execution_mode") != "fast"
        or not isinstance(manifest.get("run_id"), str)
        or not RUN_ID_RE.fullmatch(manifest["run_id"])
        or manifest["run_id"] != path.parent.name
        or not isinstance(manifest.get("conversations"), list)
    ):
        raise RuntimeError("Unsupported cleanup checkpoint format")
    return path, manifest


def build_manifest(
    session: str,
    expected_images: int | None,
    request_ids: list[str] | None = None,
) -> dict[str, Any]:
    pages = captured_image_pages(session, request_ids)
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

    created_at = utc_now()
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = state_root() / run_id
    manifest_path = run_dir / "manifest.json"
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "session": session,
        "source": "captured_image_gen_responses",
        "execution_mode": "fast",
        "batch_limit": FAST_BATCH_LIMIT,
        "concurrency": FAST_CONCURRENCY,
        "minimum_delay": FAST_MINIMUM_DELAY,
        "maximum_delay": FAST_MAXIMUM_DELAY,
        "created_at": created_at,
        "updated_at": created_at,
        "captured_pages": len(pages),
        "image_count": len(images_by_id),
        "conversation_count": len(counts),
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
        "execution_mode": "fast",
    }


def active_manifest_path() -> Path:
    active_path = state_root() / "active.json"
    if not active_path.exists():
        raise RuntimeError("No active cleanup checkpoint exists")
    active = json.loads(active_path.read_text(encoding="utf-8"))
    if not isinstance(active, dict):
        raise RuntimeError("Unsupported active checkpoint format")
    run_id = active.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise RuntimeError("The active checkpoint has an invalid run id")
    manifest_path = active.get("manifest_path")
    if not isinstance(manifest_path, str):
        raise RuntimeError("The active checkpoint has an invalid manifest path")
    path = Path(manifest_path)
    expected = state_root() / run_id / "manifest.json"
    if path.resolve() != expected.resolve():
        raise RuntimeError("The active checkpoint has an unexpected manifest path")
    return path


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
        "execution_mode": manifest.get("execution_mode"),
        "reconciliation_status": manifest.get("reconciliation_status"),
        "statuses": statuses,
    }


def require_authenticated_session(session: str) -> None:
    source = r"""async page => {
      await page.goto('https://chatgpt.com/images', {waitUntil: 'domcontentloaded'});
      const loginButtons = await page.getByRole('button', {name: /^Log in$/}).count();
      const profileButtons = await page.getByRole(
        'button', {name: /open profile menu/i}
      ).count();
      return JSON.stringify({
        authenticated: loginButtons === 0 && profileButtons > 0
      });
    }"""
    result = run_code_json(session, source)
    if result.get("authenticated") is not True:
        raise RuntimeError(
            "The browser session is not authenticated. Sign in in the existing "
            "headed browser, then run prepare again from the same working directory."
        )


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


def prepare_run(session: str) -> dict[str, Any]:
    active_path = state_root() / "active.json"
    if active_path.exists():
        _, active_manifest = load_manifest()
        if active_manifest.get("reconciliation_status") == "complete":
            raise RuntimeError(
                "A completed cleanup checkpoint is still active. Obtain approval and "
                "remove it before preparing another run."
            )
        raise RuntimeError(
            "An unfinished cleanup checkpoint is already active. Resume and verify "
            "that run before preparing another one."
        )
    require_authenticated_session(session)
    gallery = load_gallery(session)
    return build_manifest(
        session,
        gallery["image_count"],
        gallery["request_ids"],
    )


def prime_browser_authorization(session: str) -> dict[str, Any]:
    source = r"""async page => {
      const existing = await page.evaluate(() =>
        typeof window.__codexCleanupAuthorization === 'string' &&
        window.__codexCleanupAuthorization.startsWith('Bearer ')
      );
      if (existing) return JSON.stringify({primed: true, reused: true});

      const requestPromise = page.waitForRequest(request => {
        const authorization = request.headers().authorization;
        return request.url().includes('/backend-api/') &&
          typeof authorization === 'string' &&
          authorization.startsWith('Bearer ');
      }, {timeout: 20000});
      await page.reload({waitUntil: 'domcontentloaded'});
      const request = await requestPromise;
      const authorization = request.headers().authorization;
      await page.evaluate(value => {
        Object.defineProperty(window, '__codexCleanupAuthorization', {
          value,
          configurable: true,
          writable: true
        });
      }, authorization);
      return JSON.stringify({primed: true, reused: false});
    }"""
    result = run_code_json(session, source)
    if result.get("primed") is not True:
        raise RuntimeError("Could not prime volatile browser authorization")
    return result


def save_batch_result(
    path: Path,
    manifest: dict[str, Any],
    conversation: dict[str, Any],
    batch_id: str,
    result: dict[str, Any],
) -> None:
    if conversation.get("last_batch_id") == batch_id:
        return
    updated_at = utc_now()
    conversation.update(
        {
            "status": result["outcome"],
            "attempts": int(conversation.get("attempts", 0)) + result["attempts"],
            "last_http_status": result["http_status"],
            "last_error_code": result["error_code"],
            "last_batch_id": batch_id,
            "updated_at": updated_at,
        }
    )
    manifest["updated_at"] = updated_at
    atomic_json_write(path, manifest)


def browser_journal(session: str) -> dict[str, Any] | None:
    source = r"""async page => {
      const journal = await page.evaluate(() => {
        const raw = localStorage.getItem('codex.chatgpt-image-cleanup.journal');
        return raw ? JSON.parse(raw) : null;
      });
      return JSON.stringify({journal});
    }"""
    result = run_code_json(session, source)
    journal = result.get("journal")
    if journal is not None and not isinstance(journal, dict):
        raise RuntimeError("Browser cleanup journal has an invalid schema")
    return journal


def clear_browser_journal(session: str, batch_id: str) -> None:
    source = f"""async page => {{
      return JSON.stringify(await page.evaluate(expectedBatchId => {{
        const key = 'codex.chatgpt-image-cleanup.journal';
        const raw = localStorage.getItem(key);
        if (!raw) return {{cleared: true, missing: true}};
        const journal = JSON.parse(raw);
        if (journal.batch_id !== expectedBatchId) return {{cleared: false}};
        localStorage.removeItem(key);
        return {{cleared: true, missing: false}};
      }}, '{batch_id}'));
    }}"""
    result = run_code_json(session, source)
    if result.get("cleared") is not True:
        raise RuntimeError("Refusing to clear a mismatched browser cleanup journal")


def apply_browser_journal(
    session: str,
    path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any] | None:
    journal = browser_journal(session)
    if journal is None:
        return None
    if journal.get("run_id") != manifest.get("run_id"):
        raise RuntimeError("Browser cleanup journal does not match the active run")
    batch_id = journal.get("batch_id")
    results = journal.get("results")
    if not isinstance(batch_id, str) or not isinstance(results, list):
        raise RuntimeError("Browser cleanup journal is malformed")

    conversations = {
        item.get("conversation_id"): item for item in manifest.get("conversations", [])
    }
    for result in results:
        if not isinstance(result, dict):
            raise RuntimeError("Browser cleanup result is malformed")
        conversation_id = result.get("conversation_id")
        conversation = conversations.get(conversation_id)
        if conversation is None or not CONVERSATION_ID_RE.fullmatch(conversation_id):
            raise RuntimeError("Browser cleanup result references an unknown conversation")
        attempts = result.get("attempts")
        http_status = result.get("http_status")
        outcome = result.get("outcome")
        error_code = result.get("error_code")
        if (
            not isinstance(attempts, int)
            or not 1 <= attempts <= 3
            or (http_status is not None and not isinstance(http_status, int))
            or outcome not in {"complete", "retryable", "paused"}
            or (error_code is not None and not isinstance(error_code, str))
        ):
            raise RuntimeError("Browser cleanup result has invalid fields")
        save_batch_result(path, manifest, conversation, batch_id, result)

    clear_browser_journal(session, batch_id)
    return journal


def delete_browser_batch(
    session: str,
    run_id: str,
    conversation_ids: list[str],
) -> dict[str, Any]:
    if not conversation_ids or len(conversation_ids) > FAST_BATCH_LIMIT:
        raise RuntimeError("Browser batch must contain between 1 and 20 conversations")
    if any(not CONVERSATION_ID_RE.fullmatch(item) for item in conversation_ids):
        raise RuntimeError("Browser batch contains an invalid conversation id")
    config = json.dumps(
        {
            "run_id": run_id,
            "conversation_ids": conversation_ids,
            "minimum_delay_ms": int(FAST_MINIMUM_DELAY * 1000),
            "maximum_delay_ms": int(FAST_MAXIMUM_DELAY * 1000),
            "concurrency": FAST_CONCURRENCY,
            "request_timeout_ms": DELETE_REQUEST_TIMEOUT_MS,
        }
    )
    source = f"""async page => {{
      const config = {config};
      return JSON.stringify(await page.evaluate(async config => {{
        const key = 'codex.chatgpt-image-cleanup.journal';
        const authorization = window.__codexCleanupAuthorization;
        if (typeof authorization !== 'string' || !authorization.startsWith('Bearer ')) {{
          return {{error: 'authorization_not_primed'}};
        }}
        const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
        const jitter = (minimum, maximum) =>
          minimum + Math.floor(Math.random() * (maximum - minimum + 1));
        const batchId = crypto.randomUUID();
        const journal = {{
          run_id: config.run_id,
          batch_id: batchId,
          results: [],
          delete_calls: 0,
          paused_reason: null
        }};
        localStorage.setItem(key, JSON.stringify(journal));

        let nextIndex = 0;
        let nextStartAt = Date.now();
        const acquireStartSlot = async () => {{
          const scheduledAt = nextStartAt;
          nextStartAt += jitter(config.minimum_delay_ms, config.maximum_delay_ms);
          await wait(Math.max(0, scheduledAt - Date.now()));
        }};

        const processConversation = async conversationId => {{
          let finalResult = null;
          for (let attempt = 1; attempt <= 3; attempt++) {{
            let response;
            let timeoutId;
            try {{
              const controller = new AbortController();
              timeoutId = setTimeout(
                () => controller.abort(), config.request_timeout_ms
              );
              journal.delete_calls += 1;
              response = await fetch('/backend-api/conversation/id/' + conversationId, {{
                method: 'DELETE',
                credentials: 'include',
                headers: {{authorization: window.__codexCleanupAuthorization}},
                signal: controller.signal
              }});
            }} catch {{
              if (attempt === 3) {{
                finalResult = {{
                  conversation_id: conversationId,
                  attempts: attempt,
                  http_status: null,
                  outcome: 'retryable',
                  error_code: 'network_failure'
                }};
                journal.paused_reason = 'three_consecutive_failures';
                break;
              }}
              await wait(Math.min(60000, (2 ** (attempt - 1)) * 1000 + jitter(0, 1000)));
              continue;
            }} finally {{
              if (timeoutId) clearTimeout(timeoutId);
            }}

            const status = response.status;
            if (status === 200 || status === 204 || status === 404) {{
              finalResult = {{
                conversation_id: conversationId,
                attempts: attempt,
                http_status: status,
                outcome: 'complete',
                error_code: null
              }};
              break;
            }}
            if (status === 401 || status === 403) {{
              window.__codexCleanupAuthorization = null;
              finalResult = {{
                conversation_id: conversationId,
                attempts: attempt,
                http_status: status,
                outcome: 'paused',
                error_code: 'authentication_failed'
              }};
              journal.paused_reason = 'authentication_failed';
              break;
            }}
            if (status === 429 || (status >= 500 && status <= 599)) {{
              const retryAfterHeader = response.headers.get('retry-after');
              const retryAfter = retryAfterHeader === null
                ? Number.NaN
                : Number(retryAfterHeader);
              const delay = Number.isFinite(retryAfter) && retryAfter >= 0
                ? retryAfter * 1000
                : Math.min(60000, (2 ** (attempt - 1)) * 1000 + jitter(0, 1000));
              if (attempt === 3 || delay > 60000) {{
                finalResult = {{
                  conversation_id: conversationId,
                  attempts: attempt,
                  http_status: status,
                  outcome: 'retryable',
                  error_code: status === 429 ? 'rate_limited' : 'server_error'
                }};
                journal.paused_reason = status === 429
                  ? 'rate_limited'
                  : 'three_consecutive_failures';
                break;
              }}
              await wait(delay);
              continue;
            }}
            finalResult = {{
              conversation_id: conversationId,
              attempts: attempt,
              http_status: status,
              outcome: 'paused',
              error_code: 'unexpected_http_status'
            }};
            journal.paused_reason = 'unexpected_http_status';
            break;
          }}

          if (!finalResult) throw new Error('Deletion attempt ended without a result');
          journal.results.push(finalResult);
          localStorage.setItem(key, JSON.stringify(journal));
        }};

        const worker = async () => {{
          while (!journal.paused_reason) {{
            const index = nextIndex++;
            if (index >= config.conversation_ids.length) return;
            await acquireStartSlot();
            if (journal.paused_reason) return;
            await processConversation(config.conversation_ids[index]);
          }}
        }};
        const workerCount = Math.min(config.concurrency, config.conversation_ids.length);
        await Promise.all(Array.from({{length: workerCount}}, () => worker()));
        return journal;
      }}, config));
    }}"""
    result = run_code_json(
        session,
        source,
        timeout=BATCH_CLI_TIMEOUT_SECONDS,
    )
    if result.get("error") == "authorization_not_primed":
        raise RuntimeError("Volatile browser authorization is not primed")
    return result


def run_batch(
    session: str,
    confirmed_run_id: str,
) -> dict[str, Any]:
    path, manifest = load_manifest()
    if manifest.get("run_id") != confirmed_run_id:
        raise RuntimeError("--confirm-run-id does not match the active checkpoint")
    if manifest.get("execution_mode") != "fast":
        raise RuntimeError("The checkpoint is not configured for fast execution")

    apply_browser_journal(session, path, manifest)

    candidates = [
        item
        for item in manifest.get("conversations", [])
        if item.get("status")
        in {"pending", "pending_reconcile", "retryable", "paused"}
    ][:FAST_BATCH_LIMIT]
    completed = 0
    calls = 0
    paused_reason: str | None = None
    if candidates:
        prime_browser_authorization(session)
        journal = delete_browser_batch(
            session,
            confirmed_run_id,
            [item["conversation_id"] for item in candidates],
        )
        apply_browser_journal(session, path, manifest)
        results = journal.get("results", [])
        completed = sum(item.get("outcome") == "complete" for item in results)
        calls = int(journal.get("delete_calls", 0))
        paused_reason = journal.get("paused_reason")

    summary = manifest_status()
    summary.update(
        {
            "batch_completed": completed,
            "delete_calls": calls,
            "paused_reason": paused_reason,
        }
    )
    return summary


def remaining_conversation_count(statuses: dict[str, int]) -> int:
    return sum(
        statuses.get(status, 0)
        for status in {"pending", "pending_reconcile", "retryable", "paused"}
    )


def run_all(session: str, confirmed_run_id: str) -> dict[str, Any]:
    batch_number = 0
    while True:
        before = manifest_status()
        if before.get("run_id") != confirmed_run_id:
            raise RuntimeError("--confirm-run-id does not match the active checkpoint")
        before_remaining = remaining_conversation_count(before["statuses"])
        if before_remaining == 0:
            before.update({"run_status": "complete", "batches": batch_number})
            return before

        summary = run_batch(session, confirmed_run_id)
        batch_number += 1
        remaining = remaining_conversation_count(summary["statuses"])
        progress = {
            "event": "batch",
            "batch": batch_number,
            "batch_completed": summary["batch_completed"],
            "delete_calls": summary["delete_calls"],
            "remaining_conversations": remaining,
            "paused_reason": summary["paused_reason"],
        }
        print(json.dumps(progress, ensure_ascii=False, sort_keys=True), flush=True)

        if summary["paused_reason"] is not None:
            summary.update({"run_status": "paused", "batches": batch_number})
            return summary
        if remaining >= before_remaining and summary["batch_completed"] == 0:
            summary.update(
                {
                    "run_status": "paused",
                    "batches": batch_number,
                    "paused_reason": "no_progress",
                }
            )
            return summary


def verify_and_reconcile(session: str) -> dict[str, Any]:
    require_authenticated_session(session)
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


def clear_completed_state(confirmed_run_id: str) -> dict[str, Any]:
    path, manifest = load_manifest()
    if manifest.get("run_id") != confirmed_run_id:
        raise RuntimeError("--confirm-run-id does not match the active checkpoint")
    if (
        manifest.get("reconciliation_status") != "complete"
        or manifest.get("current_image_count") != 0
    ):
        raise RuntimeError("Only a verified zero-residual checkpoint can be removed")

    root = state_root().resolve()
    expected_run_dir = (root / confirmed_run_id).resolve()
    expected_manifest = expected_run_dir / "manifest.json"
    if path.resolve() != expected_manifest or path.parent.resolve() != expected_run_dir:
        raise RuntimeError("The active checkpoint path is outside its expected run directory")
    entries = list(expected_run_dir.iterdir())
    if len(entries) != 1 or entries[0].resolve() != expected_manifest:
        raise RuntimeError("The checkpoint directory contains unexpected files")

    active_path = root / "active.json"
    active = json.loads(active_path.read_text(encoding="utf-8"))
    if active.get("manifest_path") != str(path):
        raise RuntimeError("The active checkpoint pointer does not match the manifest")

    active_path.unlink()
    path.unlink()
    expected_run_dir.rmdir()
    return {"run_id": confirmed_run_id, "state_removed": True}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Manage resumable ChatGPT Images cleanup checkpoints"
    )
    subparsers = result.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare",
        help="Verify authentication, inventory the gallery, and create a checkpoint",
    )
    prepare.add_argument("--session", default="browser")

    run = subparsers.add_parser(
        "run-all",
        help="Delete every pending conversation with the fixed fast settings",
    )
    run.add_argument("--session", default="browser")
    run.add_argument("--confirm-run-id", required=True)

    verify = subparsers.add_parser(
        "verify",
        help="Reload the gallery and reconcile residual conversation ids",
    )
    verify.add_argument("--session", default="browser")

    clear = subparsers.add_parser(
        "clear-state",
        help="Remove one explicitly approved, verified zero-residual checkpoint",
    )
    clear.add_argument("--confirm-run-id", required=True)

    subparsers.add_parser("status", help="Show a sanitized active-run summary")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "prepare":
            output = prepare_run(args.session)
        elif args.command == "run-all":
            output = run_all(args.session, args.confirm_run_id)
        elif args.command == "verify":
            output = verify_and_reconcile(args.session)
        elif args.command == "clear-state":
            output = clear_completed_state(args.confirm_run_id)
        else:
            output = manifest_status()
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
