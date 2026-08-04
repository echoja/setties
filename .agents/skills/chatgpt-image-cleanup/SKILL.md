---
name: chatgpt-image-cleanup
description: Safely delete every unique ChatGPT conversation linked from the signed-in Images gallery using Playwright CLI, a UI-verified canary, deduplicated resumable checkpoints, conservative rate limiting, and reconciliation. Use when the user asks to remove all ChatGPT Images or the chats behind them, especially orphaned project image chats.
---

# ChatGPT Image Cleanup

Delete chats behind the ChatGPT Images gallery without repeating successful work or exporting browser credentials.

## Safety contract

- Treat the operation as irreversible. Require explicit scope approval before creating a run.
- Deduplicate by `conversation_id`; never treat image cards as the deletion unit.
- Read [references/api.md](references/api.md) before using an endpoint. The API is internal and may change.
- Use the persistent, headed Playwright CLI session `browser`. Run the helper from the same working directory where that session was opened.
- Keep credentials inside Playwright. Never print or save tokens, cookies, signed URLs, prompts, titles, or image content.
- Delete one single-image conversation through the visible UI as a canary on every run.
- After the canary passes, report exact counts and require a second explicit confirmation before bulk deletion.
- Keep the checkpoint until verification completes and the user approves its removal.

## Prepare the manifest

1. Open `https://chatgpt.com/images` in the persistent `browser` session and let the user sign in.
   Persistent mode preserves the profile, not the browser process. Playwright CLI session names are scoped to the working directory, so reopen and run the helper from the same directory if the process exits.
2. Load the complete authenticated cursor feed:

   ```bash
   python3 scripts/cleanup.py load-gallery --session browser
   ```

3. Build the checkpoint from already captured `200` responses. Pass the UI count as an integrity check:

   ```bash
   python3 scripts/cleanup.py manifest-from-capture \
     --session browser \
     --expected-images <count>
   ```

The helper writes owner-only files under `${XDG_STATE_HOME:-~/.local/state}/chatgpt-image-cleanup/`. It stores only IDs, image counts, statuses, attempts, timestamps, and sanitized error codes.

## Verify the canary

1. Use the manifest's `canary_conversation_id`, which must map to exactly one image.
2. Navigate to `https://chatgpt.com/c/<conversation_id>`.
3. Use the visible conversation menu and confirmation dialog to delete it.
4. Capture only the request method, path template, body presence, and status. Do not inspect or print request-header values.
5. Reload the full Images gallery and require the count to decrease by exactly one.
6. Revisit the canary chat and require its conversation GET to return `404`.
7. Record the result:

   ```bash
   python3 scripts/cleanup.py record-canary \
     --delete-http-status 200 \
     --image-count-after <count> \
     --conversation-get-status 404
   ```

Stop and ask for the final bulk-run confirmation. Include the run ID and pending-conversation count.

## Run resumable batches

Process at most 20 conversations per invocation:

```bash
python3 scripts/cleanup.py run-batch \
  --session browser \
  --confirm-run-id <run-id> \
  --limit 20
```

The helper uses one request at a time, waits a randomized 800–1,200 ms between conversations by default, and atomically checkpoints every HTTP result. With explicit user approval for faster processing, lower the delay no further than 250–400 ms and raise concurrency no higher than the 20-conversation batch limit. It treats `200`, `204`, and `404` as complete; retries transient failures conservatively; and pauses on authentication failures, unexpected statuses, or repeated failures.

For an explicitly approved faster run, start with `--minimum-delay 0.25 --maximum-delay 0.4 --concurrency 10`. Increase only after clean batches; reduce concurrency when retries increase or throughput worsens.

Report progress after every batch. Resume with the same command and run ID; completed IDs are excluded automatically.

## Reconcile

After no pending conversations remain, run:

```bash
python3 scripts/cleanup.py verify --session browser
```

- Finish only when `residual_images` is zero.
- If residual IDs are new, run another confirmed batch.
- Allow at most three reconciliation passes.
- Stop when the same residual set appears twice; report it as stalled instead of looping.
- Remove the checkpoint only after the user approves cleanup of the state files.
