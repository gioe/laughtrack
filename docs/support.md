# Support Operations

How user support requests reach LaughTrack, how they are triaged, and how outage reports turn into fixes.

## Inbox

- **Public address:** `contact@laugh-track.com` (listed on the [support page](https://laugh-track.com/support) and the site footer).
- **Routing:** forwarded to `gioematt@gmail.com` (Matt Gioe's personal Gmail).
- **App Store / TestFlight review contact:** `gioematt@gmail.com` directly (see `ios/fastlane/metadata/review_information/email_address.txt`).

There is no separate ticketing tool. Treat the personal inbox as the single source of truth for inbound support mail.

## Triage cadence and SLA

- **Triage:** solo — Matt checks the inbox daily on business days (Mon–Fri).
- **Public SLA:** first human response within **2 business days** of receipt.
- A "first response" is an acknowledgement and a question or next step — not necessarily a fix.

If a mail goes more than 2 business days without a reply, treat that as an operational miss and surface it (see escalation below).

## Escalation: email → tusk task → fix

Every actionable report becomes a tracked task. The flow:

1. **Reply within SLA.** Acknowledge, ask any clarifying questions, and tell the reporter the issue is being tracked.
2. **File a tusk task** via `/create-task` (or `tusk task-insert` for trivial cases). Severity sets priority:
   - **Site-wide outage / data loss / auth broken** → `priority=Critical`, work it immediately, drop other in-flight work.
   - **Broken feature affecting many users** (e.g., scraper down, ticket links 404) → `priority=High`, schedule next.
   - **Single-venue or single-comedian bug, cosmetic issue, feature request** → `priority=Medium` or `Low`, normal backlog.
3. **Work the task through `/tusk`** like any other bug — feature branch, fix, merge to `main`, Vercel auto-deploys.
4. **Close the loop with the reporter** once the fix is live. Reference the deployed change so they can verify.

For a confirmed live outage, also note it in the Discord #laughtrack channel (see `MEMORY.md` reference) so the next nightly scraper run is monitored more closely.
