"""Send a short final-response excerpt from a Codex Stop hook to Slack.

The webhook is stored locally in ~/.config/agent-notifications/slack-webhook,
outside this repository. This script never prints it or network error details.
"""

import json
from pathlib import Path
import sys
import urllib.request


def main():
    event = json.load(sys.stdin)
    if event.get("hook_event_name") != "Stop":
        return
    message = (event.get("last_assistant_message") or "").strip()
    if not message:
        return
    # Bound the notification without sending the full conversation or tool output.
    if len(message) > 700:
        message = message[:697].rsplit(" ", 1)[0] + "…"
    project = Path(event.get("cwd") or ".").name
    payload = {
        "text": f"Codex · {project}\n{message}",
        "mrkdwn": False,
        "unfurl_links": False,
        "unfurl_media": False,
    }
    secret = Path.home() / ".config/agent-notifications/slack-webhook"
    request = urllib.request.Request(
        secret.read_text().strip(),
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 200 or response.read().strip() != b"ok":
            raise RuntimeError("Slack rejected the notification")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(json.dumps({"systemMessage": "Slack notification failed; check the local webhook and network."}))
    else:
        print("{}")
