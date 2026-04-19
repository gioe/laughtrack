import { defineConfig, devices } from "@playwright/test";

// Dedicated config for visual regression tests (E2E_FIXTURE_MODE=1).
//
// Server lifecycle:
//   - CI: the workflow starts `next start` out-of-band before invoking this
//     config. `reuseExistingServer: true` makes Playwright detect the running
//     server at `url` and skip `webServer.command` entirely.
//   - Local: if no server is running at `url`, Playwright runs `command` to
//     build and start one. Env-var overrides let developers point at a real
//     database (to reproduce an issue) without editing this file.
//
// Baselines are OS-specific; CI (ubuntu-latest) reads/writes `*-linux.png`.
// Regenerate with `npm run test:e2e:visual:update` locally, or trigger the
// `web-ci.yml` workflow_dispatch with `update_baselines=true` for Linux.

const PORT = process.env.VISUAL_PORT || "3100";
const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`;

// Build-time defaults for `next build` inside webServer.command. The sitemap
// route prerenders against a real DB; the AUTH_SECRET is throwaway — fixture
// mode bypasses `auth()` on the home page. Override via the real env vars
// before invoking test:e2e:visual if you need different values.
const FIXTURE_DB_URL =
    process.env.DATABASE_URL ||
    "postgresql://fixture:fixture@localhost:5432/fixture?sslmode=disable";
const FIXTURE_AUTH_SECRET =
    process.env.AUTH_SECRET ||
    "visualtest-dummy-secret-do-not-use-in-production-32c";

export default defineConfig({
    testDir: "./e2e",
    testMatch: /home-carousels\.spec\.ts$/,
    fullyParallel: false,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 1 : 0,
    workers: 1,
    reporter: [["html"], ["list"]],
    use: {
        baseURL: BASE_URL,
        trace: "on-first-retry",
    },
    projects: [
        {
            name: "chromium",
            use: { ...devices["Desktop Chrome"] },
        },
    ],
    webServer: {
        command: `npm run build && PORT=${PORT} E2E_FIXTURE_MODE=1 DATABASE_URL='${FIXTURE_DB_URL}' DIRECT_URL='${FIXTURE_DB_URL}' AUTH_SECRET='${FIXTURE_AUTH_SECRET}' npm start`,
        url: BASE_URL,
        timeout: 180_000,
        reuseExistingServer: true,
    },
});
