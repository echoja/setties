# ChatGPT Images cleanup API observations

These are sanitized observations from the ChatGPT web application on 2026-08-04. The endpoints are internal and undocumented. Re-verify them through a visible UI canary on every cleanup run.

## Image inventory

The Images page requested:

```text
GET /backend-api/my/recent/image_gen?limit=25
GET /backend-api/my/recent/image_gen?limit=25&after=<opaque-cursor>
```

The response shape was:

```json
{
  "items": [
    {
      "id": "<image-id>",
      "conversation_id": "<conversation-id>",
      "is_archived": false
    }
  ],
  "cursor": "<opaque-cursor-or-null>"
}
```

Only `id` and `conversation_id` are required for cleanup. Treat the cursor as opaque. Deduplicate image records by `id`, then group by `conversation_id`.

In the observed run, 1,006 unique images mapped to 903 unique conversations; 103 images shared a conversation with another image, and no image lacked a conversation ID. These counts are account- and time-specific and must not be reused as future expectations.

The web UI used a page size of 25. A raw in-page `fetch` with a larger limit returned `401` because it bypassed the application's authenticated request layer. Do not extract a bearer token to work around this. Drive the authenticated gallery loader and reuse its captured response bodies.

The image modal's carousel count is not a reliable gallery total until the complete gallery feed has loaded. Compare the stable `Open image:` card count with the deduplicated response manifest.

## Conversation deletion

The visible **Delete chat?** flow issued:

```text
DELETE /backend-api/conversation/id/{conversation_id}
Body: none
Success: 200 {"success":true}
```

The request succeeded with the Playwright browser context's session cookies. The reusable helper uses `page.request.delete`, so tokens and cookies remain inside Playwright.

After deletion, this read returned `404` and the client redirected home:

```text
GET /backend-api/conversation/{conversation_id}
```

Use one conversation linked to exactly one image as the canary. Require all of the following before bulk deletion:

- The UI-confirmed delete request matches the method, path shape, and empty body above.
- The delete response is `200`.
- The complete gallery count decreases by exactly one.
- Revisiting the canary produces a conversation `404`.

## Request and retry policy

- Make one delete request per unique conversation.
- Use concurrency 1 and randomized 800–1,200 ms pacing.
- Treat `200`, `204`, and `404` as complete.
- On `429`, record the result and honor a numeric `Retry-After`; pause instead of sleeping longer than 60 seconds.
- Retry network failures and `5xx` responses at most three times with exponential backoff and jitter.
- Pause on `401`, `403`, schema changes, unexpected statuses, or repeated failures.
- Atomically checkpoint each result and never retry a completed conversation during ordinary resume.
- Reconcile the gallery after the bulk pass. Stop if the same residual set appears twice or after three passes.
