import { defineConfig, devices } from "@playwright/test";

// Dedicated config for visual regression tests (E2E_FIXTURE_MODE=1).
// The webServer block spins up `next start` with fixture data so screenshots
// are pixel-stable across runs and do not require a live database.
//
// Baselines are OS-specific; CI runs on linux and stores/consumes `-linux.png`
// files. Regenerate locally with:
//   npm run test:e2e:visual:update

const PORT = process.env.VISUAL_PORT || "3100";
const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`;

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
        command: `npm run build && PORT=${PORT} E2E_FIXTURE_MODE=1 DATABASE_URL='postgresql://fixture:fixture@localhost:5432/fixture?sslmode=disable' DIRECT_URL='postgresql://fixture:fixture@localhost:5432/fixture?sslmode=disable' AUTH_SECRET='visualtest-dummy-secret-do-not-use-in-production-32c' npm start`,
        url: BASE_URL,
        timeout: 180_000,
        reuseExistingServer: !process.env.CI,
    },
});
