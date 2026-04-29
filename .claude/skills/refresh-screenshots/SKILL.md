---
name: refresh-screenshots
description: Regenerate the iOS + web reference screenshots under screenshots/<view>/{ios,web}.jpg for cross-platform UX comparison against the Spotify-inspired destination
allowed-tools: Bash, Read, mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_resize, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_close, mcp__plugin_playwright_playwright__browser_wait_for, mcp__plugin_playwright_playwright__browser_evaluate, mcp__XcodeBuildMCP__session_show_defaults, mcp__XcodeBuildMCP__build_run_sim, mcp__XcodeBuildMCP__launch_app_sim, mcp__XcodeBuildMCP__stop_app_sim, mcp__XcodeBuildMCP__screenshot, mcp__XcodeBuildMCP__tap, mcp__XcodeBuildMCP__snapshot_ui
---

# Refresh Screenshots

Refresh the cross-platform reference screenshots used for web ↔ iOS ↔ Spotify-inspired
UX comparison. Each `screenshots/<view>/` subdirectory holds one `web.jpg` (Playwright
against `https://laugh-track.com`), one `ios.jpg` (XcodeBuildMCP against the iPhone 16
Pro Max simulator), and optionally a `spotify*.png` reference design that is **not**
regenerated.

The comparison set is the source of truth for "how does the new build look across
surfaces" — refresh after meaningful UI changes on either platform.

## Inventory

13 web screenshots (iPhone viewport 390×844, full page, JPEG):

| View | URL |
|---|---|
| `homeview` | `/` |
| `clubsdiscoveryview` | `/club/search` |
| `comediansdiscoveryview` | `/comedian/search` |
| `showsdiscoveryview` | `/show/search` |
| `clubdetailview` | `/club/Comedy%20Cellar%20New%20York` |
| `comediandetailview` | `/comedian/Mark%20Normand` |
| `showdetailview` | `/show/<id>` — pick the first card from `/show/search` |
| `loginmodalview` | `/` then click the header `Log In` button (viewport screenshot, not full page) |
| `aboutview` | `/about` |
| `privacyview` | `/privacy` |
| `termsview` | `/terms` |
| `supportview` | `/support` |
| `unsubscribeview` | `/unsubscribe` |

11 iOS screenshots (iPhone 16 Pro Max simulator, dark mode, native screenshot tool):

| View | How to reach |
|---|---|
| `homeview` | App launch (Home tab default) |
| `searchview` | Tap **Search** tab |
| `showsdiscoveryview` | Search tab → **Shows** sub-tab (default) |
| `comediansdiscoveryview` | Search tab → **Comedians** sub-tab |
| `clubsdiscoveryview` | Search tab → **Clubs** sub-tab |
| `clubdetailview` | Clubs sub-tab → tap **Comedy Cellar New York** card |
| `comediandetailview` | Comedians sub-tab → tap any visible comedian card (Mark Normand if visible) |
| `libraryview` | Tap **Library** tab |
| `profileview` | Tap **Profile** tab |
| `settingsview` | Profile tab → tap **Open Settings** |
| `loginmodalview` | Profile tab → tap **Sign in** |

Views with no iOS counterpart (web-only): `aboutview`, `privacyview`, `termsview`,
`supportview`, `unsubscribeview`, `showdetailview`. Views with no web counterpart
(iOS-only): `searchview`, `libraryview`, `profileview`, `settingsview`.

Never delete or overwrite `spotify*.png` files — they are the static reference design.

## Web procedure (Playwright MCP)

1. `browser_close` (in case a stale page is open), then `browser_resize` to width=390,
   height=844 to match iPhone viewport.
2. For each view in the table above:
   - `browser_navigate` to the URL.
   - `browser_wait_for` 2–3 seconds so client data loads (especially the discovery
     pages and detail rails — they're SSR-cached but still hydrate JS).
   - `browser_take_screenshot` with `type: "jpeg"`, `fullPage: true`, and
     `filename: "<view>-web.jpg"`. **Exception:** `loginmodalview` uses
     `fullPage: false` (viewport-only) so the modal sits centered without an
     irrelevant tail of dark page below it.
3. The Playwright MCP saves screenshots to the project root (relative to repo root,
   not a configurable absolute path). After each capture, move the file with
   `mv <view>-web.jpg screenshots/<view>/web.jpg`.

For `loginmodalview`: navigate to `/` first, then trigger the modal via
`browser_evaluate` clicking the `Log In` button — the React handler doesn't always
fire reliably from the MCP `browser_click` selector path:

```javascript
() => {
  const btn = Array.from(document.querySelectorAll('button'))
    .find(b => b.textContent?.trim() === 'Log In');
  btn?.click();
}
```

For `showdetailview`: detail pages use numeric IDs (`/show/<id>`). IDs change as old
shows expire, so don't hardcode one. Navigate to `/show/search`, run
`browser_evaluate` to pull the first href matching `/show/\d+`, and use that ID.

Comedian and club slugs use URL-encoded full names (`Mark%20Normand`,
`Comedy%20Cellar%20New%20York`) — not lowercase-hyphenated. Lowercase-hyphenated
slugs return 404 (the route is just `[name]`, not a slug column).

## iOS procedure (XcodeBuildMCP)

1. `session_show_defaults` to confirm: `LaughTrack.xcodeproj`, scheme `LaughTrack`,
   `iPhone 16 Pro Max` simulator, bundle `com.laughtrack.app`. These are the
   committed defaults — adjust only if the harness reports otherwise.
2. `build_run_sim` to build + install + launch a fresh build. (`launch_app_sim`
   alone re-runs whatever is already installed and may be stale after a code
   change — always rebuild for an accurate snapshot.)
3. Wait ~5 seconds after launch for tabs to wire up and home rails to fetch.
4. For each iOS view:
   - Use `tap` with an accessibility `label` when available; fall back to
     coordinates when labels are ambiguous (e.g. multiple "Try again" buttons,
     tab bar icons that have no unique label).
   - The bottom tab bar at logical 440×956 sits at y≈914. Tab x-centers:
     Home=55, Search=165, Library=275, Profile=385.
   - After each tap, wait 2–4 seconds before screenshotting so the new view
     animates in and remote data loads.
   - `screenshot` with `returnFormat: "path"`, then `cp` the temp file to
     `screenshots/<view>/ios.jpg`.
5. If a tap by label says "multiple matches", call `snapshot_ui` to get unique
   AXUniqueIds or distinguishing coordinates.

The simulator stays in dark mode by default — don't toggle appearance unless the
prior screenshot set was light mode (it isn't).

## What to expect from the home feed

iOS home rails ("Shows tonight", "Trending comedians") may render error states
("Data issue" / "No connection") even when the production API returns 200. The
parser is brittle to schema drift — capture the current state regardless and
flag the failure to the user. Don't try to fix the iOS bug as part of a
screenshot refresh.

## Verify

After both platforms, run `git status screenshots/` — you should see modified
`.jpg` files for every view in the inventory. If a file is unchanged, the
refresh missed it; investigate before continuing.

Visually skim a few of the regenerated images via `Read` to confirm they captured
real content (not error toasts, not auth walls, not stale localhost). Pay
attention to the detail views — these are the most likely to break when the
underlying entity gets renamed or removed.

## Don't

- Don't regenerate the `spotify*.png` reference designs — they're the third leg
  of the comparison and never refresh from this skill.
- Don't switch the iOS simulator to a different device. The committed
  screenshots are all iPhone 16 Pro Max — mixing devices breaks visual diffing.
- Don't run the web captures against `localhost:3000`. The screenshots compare
  against production (`laugh-track.com`) so detail pages exercise the real
  Vercel cache + SSR path. Pre-merge verification of fresh DB writes is a
  separate workflow (`npm run dev`) — not relevant here.
