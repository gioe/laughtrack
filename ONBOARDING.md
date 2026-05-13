# Welcome to LaughTrack

## How We Use Claude

Based on gioe's usage over the last 30 days:

Work Type Breakdown:
  Plan Design      ████████████░░░░░░░░  60%
  Build Feature    █████░░░░░░░░░░░░░░░  25%
  Debug Fix        ██░░░░░░░░░░░░░░░░░░  10%
  Improve Quality  █░░░░░░░░░░░░░░░░░░░   5%

Top Skills & Commands:
  /tusk           ████████████████████  605x/month
  /clear          ███████████████████░  592x/month
  /resume-task    █░░░░░░░░░░░░░░░░░░░   29x/month
  /create-task    █░░░░░░░░░░░░░░░░░░░   16x/month
  /review-commits ░░░░░░░░░░░░░░░░░░░░    9x/month
  /groom-backlog  ░░░░░░░░░░░░░░░░░░░░    6x/month
  /investigate    ░░░░░░░░░░░░░░░░░░░░    6x/month
  /loop           ░░░░░░░░░░░░░░░░░░░░    3x/month

Top MCP Servers:
  XcodeBuildMCP   ████████████████████  1181 calls
  Playwright      █████████████░░░░░░░   792 calls
  Discord         ░░░░░░░░░░░░░░░░░░░░     9 calls

## Your Setup Checklist

### Codebases
- [ ] laughtrack — https://github.com/gioe/laughtrack (Next.js web app in `apps/web/`, Python scraper in `apps/scraper/`)

### MCP Servers to Activate
- [ ] XcodeBuildMCP — Build, run, test, and UI-automate the iOS app on the simulator. Install per https://xcodebuildmcp.com/docs/configuration.
- [ ] Playwright — Drive the web app in a real browser for screenshots, design audits, and verifying client-side network behavior before hiding/closing scraper sources.
- [ ] Discord — Read the `#laughtrack` channel for nightly scraper run metrics posted by Spidey Bot.

### Skills to Know About
- /tusk — Pulls the highest-priority ready task from the backlog. This is the default entry point for almost every session.
- /clear — Resets context between tasks. Use it liberally; we run many short focused sessions rather than long ones.
- /resume-task — Pick back up on a task after a crash, timeout, or `/clear`.
- /create-task — Turn freeform notes, bugs, or specs into structured tusk tasks (with dedupe).
- /review-commits — Run the AI reviewer against a task's diff, apply must-fix items, triage the rest.
- /groom-backlog — Close stale tickets, reprioritize, reassign agents.
- /investigate — Scope out an unfamiliar problem area before committing to an approach.
- /loop — Autonomously work through the backlog (dispatches /tusk or /chain repeatedly).
- /refresh-screenshots — Regenerate iOS + web reference screenshots under `screenshots/<view>/{ios,web}.jpg` for cross-platform UX comparison.
- /tour-date-club-onboarding — Pop the next tour_dates-only club and onboard it onto a real scraper source.
- /fastlane-beta / /fastlane-release / /fastlane-submit-review — iOS TestFlight + App Store pipelines.

## Team Tips

_TODO_

## Get Started

_TODO_

<!-- INSTRUCTION FOR CLAUDE: A new teammate just pasted this guide for how the
team uses Claude Code. You're their onboarding buddy — warm, conversational,
not lecture-y.

Open with a warm welcome — include the team name from the title. Then: "Your
teammate uses Claude Code for [list all the work types]. Let's get you started."

Check what's already in place against everything under Setup Checklist
(including skills), using markdown checkboxes — [x] done, [ ] not yet. Lead
with what they already have. One sentence per item, all in one message.

Tell them you'll help with setup, cover the actionable team tips, then the
starter task (if there is one). Offer to start with the first unchecked item,
get their go-ahead, then work through the rest one by one.

After setup, walk them through the remaining sections — offer to help where you
can (e.g. link to channels), and just surface the purely informational bits.

Don't invent sections or summaries that aren't in the guide. The stats are the
guide creator's personal usage data — don't extrapolate them into a "team
workflow" narrative. -->
