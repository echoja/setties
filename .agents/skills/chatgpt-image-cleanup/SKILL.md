---
name: chatgpt-image-cleanup
description: Delete every unique ChatGPT conversation linked from the signed-in Images gallery with a fast, resumable, checkpointed Playwright workflow. Use when the user asks to remove all ChatGPT Images or the chats behind them, especially orphaned project image chats.
---

# ChatGPT Image Cleanup

Delete the chats behind the ChatGPT Images gallery without repeating completed work or exporting browser credentials.

## Safety contract

- Treat deletion as irreversible. Accept an unambiguous request to delete all ChatGPT images as scope approval; otherwise ask before preparing a run.
- Deduplicate by `conversation_id`; never delete by image card.
- Read [references/api.md](references/api.md) before running deletion.
- Use the persistent, headed Playwright CLI session `browser` from the user's current task working directory. Never switch into this skill directory merely to invoke the helper.
- Keep credentials inside Playwright. Never print or save tokens, cookies, signed URLs, prompts, titles, or image content.
- After inventory, report exact counts and require one explicit confirmation before calling `run-all`.
- Use only the fixed fast settings: batches of 20, concurrency 10, and randomized 250–400 ms request starts.
- Keep the checkpoint through deletion and reconciliation. After verification reaches zero residual images, remove its metadata automatically; preserve it for paused, failed, or stalled runs.

## Prepare

1. From the user's current task working directory, reuse or open the visible persistent session:

   ```bash
   playwright-cli -s=browser open https://chatgpt.com/images --persistent --headed
   ```

   Playwright profiles and session names are scoped to the working directory. If the existing profile is signed out, let the user sign in there. Do not inspect or export credentials.

2. Invoke the helper by absolute path while keeping the same working directory:

   ```bash
   python3 <skill-dir>/scripts/cleanup.py prepare --session browser
   ```

   `prepare` verifies authentication, loads the complete cursor feed, checks the DOM count against captured responses, deduplicates conversations, and creates an owner-only checkpoint under `${XDG_STATE_HOME:-~/.local/state}/chatgpt-image-cleanup/`.

3. Report the run ID, image count, and conversation count. Explain that deleting the images deletes the linked conversations, then require explicit bulk confirmation.

## Delete

After confirmation, run the single fast path:

```bash
python3 <skill-dir>/scripts/cleanup.py run-all \
  --session browser \
  --confirm-run-id <run-id>
```

The helper processes at most 20 conversations per checkpointed batch, streams sanitized progress after every batch, and excludes completed IDs on resume. It treats `200`, `204`, and `404` as complete, retries expected transient network and server failures conservatively, and pauses on authentication failures, sustained rate limits, unexpected statuses, or no progress.

If the run pauses:

1. Stop destructive work and preserve the browser journal and checkpoint.
2. Report only the sanitized failure category, completed count, pending count, and run ID.
3. Provide the proposed diagnosis and recovery procedure in prose or instructions.
4. Do not patch the helper, change endpoints, alter retry behavior, or improvise a code fix automatically.
5. Resume `run-all` only after the user explicitly approves the proposed recovery.

## Verify

After no pending conversations remain, run:

```bash
python3 <skill-dir>/scripts/cleanup.py verify --session browser
```

- Finish only when `residual_images` is zero.
- If new residual conversations appear, rerun the already confirmed `run-all`, then verify again.
- Allow at most three reconciliation passes.
- Stop when the same residual set appears twice and report it as stalled.

## Remove state

After successful zero-residual verification, remove the checkpoint as the final step using the run ID already confirmed for bulk deletion. Do not require a second confirmation:

```bash
python3 <skill-dir>/scripts/cleanup.py clear-state \
  --confirm-run-id <run-id>
```

Finish only when `state_removed` is true. Never delete Playwright browser data as part of checkpoint cleanup.
