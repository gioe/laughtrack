---
name: send-test-push
description: Send a diagnostic APNs push notification to a LaughTrack user by email address or users.id. Use when testing production push delivery, checking a newly registered iOS device token, or investigating a user who sees in-app notifications but does not receive push alerts.
---

# Send Test Push

Send one alert to the target user's newest active iOS token through the production notification service.

## Workflow

1. Resolve exactly one target from the user's request:
   - Use `--email` for an email address.
   - Use `--user-id` for a `users.id` value.
   - If neither is available, ask for one before proceeding.
2. Tell the user that the skill is about to send an external push notification.
3. From the repository root, run exactly one of:

   ```bash
   apps/scraper/.venv/bin/python .agents/skills/send-test-push/scripts/send_test_push.py --email user@example.com
   apps/scraper/.venv/bin/python .agents/skills/send-test-push/scripts/send_test_push.py --user-id <user-id>
   ```

   Optional copy overrides:

   ```bash
   apps/scraper/.venv/bin/python .agents/skills/send-test-push/scripts/send_test_push.py \
     --email user@example.com \
     --title "LaughTrack push test" \
     --body "Testing your newest registered device."
   ```

4. Report the script's result:
   - User not found: no push was sent; verify the identifier.
   - No active iOS token: the script exits successfully without sending. Ask the user to foreground the signed-in app, then retry so launch/foreground registration can upload the current token.
   - APNs success: report the selected token ID, its registration timestamp, and HTTP status. Ask whether the alert appeared; APNs acceptance does not prove device display.
   - APNs rejection: report the status and reason. Never expose the raw device token.

## Guardrails

- The script always selects the newest active `ios` token by `last_registered_at`, then `created_at`.
- Do not insert a `sent_notifications` row for a diagnostic push.
- Do not deactivate older tokens merely because a newer token exists; a user may have multiple devices.
- Do not treat the in-app notification center or an APNs `200` response as proof that iOS displayed the alert.
- Do not rewrite the SQL or APNs call inline. Use the bundled script so future investigations follow the same path.
