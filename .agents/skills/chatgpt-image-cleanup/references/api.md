# ChatGPT Images cleanup API observations

These are sanitized observations from the ChatGPT web application, last confirmed on 2026-08-18. The endpoints are internal and undocumented. Treat a schema or status change as a reason to pause, not as permission to improvise another endpoint.

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

Use only `id` and `conversation_id`. Treat the cursor as opaque, deduplicate records by image ID, then group by conversation ID. Never reuse counts from a previous run.

The UI used a page size of 25. A raw in-page request with a larger limit returned `401` because it bypassed the application's authenticated request layer. Drive the gallery loader and reuse captured authenticated response bodies instead of extracting credentials.

The carousel count is unreliable until the complete feed has loaded. Compare the stable `Open image:` card count with the deduplicated captured responses.

## Conversation deletion

The visible deletion flow issued:

```text
DELETE /backend-api/conversation/id/{conversation_id}
Body: none
Success: 200 {"success":true}
```

Cookie-only `fetch` and `page.request.delete` attempts returned `401`. The helper captures a short-lived authorization header from one authenticated ChatGPT application request during a browser reload, keeps it only in page memory, and performs deletion with `page.evaluate(fetch)`. Never return, print, or persist the credential. Clear it and pause on `401` or `403`.

## Fixed request policy

- Delete once per unique conversation ID.
- Process at most 20 conversations per batch.
- Use concurrency 10 with randomized 250–400 ms request starts.
- Abort an individual request after 30 seconds.
- Treat `200`, `204`, and `404` as complete.
- Honor a numeric `Retry-After` for `429`; pause rather than waiting longer than 60 seconds.
- Retry network failures and `5xx` responses at most three times with exponential backoff and jitter.
- Pause on `401`, `403`, schema changes, unexpected statuses, sustained rate limits, or repeated failures.
- Checkpoint each completed result and never retry it during ordinary resume.
- Reconcile after deletion. Stop after three passes or when the same residual set appears twice.

When paused, report sanitized evidence and propose the fixing process only as prose or instructions. Do not edit the helper, change the endpoint, or alter request policy automatically. Resume only after explicit user approval.
