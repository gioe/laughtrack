---
name: fetch-seatengine-token
description: "[DEPRECATED] Use /check-seatengine-token instead. The old cart bundle extraction no longer works — SeatEngine removed the cdn-new React widget."
allowed-tools: Bash
---

# Fetch SeatEngine Token Skill (DEPRECATED)

**This skill is deprecated.** SeatEngine removed the `cdn-new.seatengine.com/cart-*.js`
React cart bundle that contained `APP_AUTH_TOKEN`. The token is no longer embedded in
any static JS bundle. Use `/check-seatengine-token` to verify the current token works.

## What to do instead

Run `/check-seatengine-token` to verify the existing token in `.env` is still valid.
