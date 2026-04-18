import { test, expect, type ConsoleMessage } from "@playwright/test";

// First-hit Next.js dev-mode route compilation can push a single goto past 30s.
// Production/preview builds resolve in well under this.
test.describe.configure({ timeout: 120_000 });

const ROUTES = ["/", "/club/search", "/comedian/search", "/show/search"];
const VIEWPORT_WIDTHS = [1024, 1280, 1440];

// Covers both development (verbose React warnings) and production (minified
// React error codes 418/419/422/423/425 — the hydration-mismatch family).
const HYDRATION_PATTERNS: RegExp[] = [
    /hydrated but some attributes of the server rendered HTML/i,
    /Hydration failed/i,
    /There was an error while hydrating/i,
    /Text content does not match server-rendered HTML/i,
    /did not expect server HTML to contain/i,
    /server rendered HTML didn't match the client/i,
    /Minified React error #(418|419|422|423|425)/i,
];

function isHydrationMessage(text: string): boolean {
    return HYDRATION_PATTERNS.some((p) => p.test(text));
}

function collectHydrationMessages(
    page: import("@playwright/test").Page,
): string[] {
    const messages: string[] = [];
    page.on("console", (msg: ConsoleMessage) => {
        if (msg.type() !== "error" && msg.type() !== "warning") return;
        const text = msg.text();
        if (isHydrationMessage(text)) {
            messages.push(`[console.${msg.type()}] ${text}`);
        }
    });
    page.on("pageerror", (err) => {
        if (isHydrationMessage(err.message)) {
            messages.push(`[pageerror] ${err.message}`);
        }
    });
    return messages;
}

for (const route of ROUTES) {
    for (const width of VIEWPORT_WIDTHS) {
        test(`no hydration console warnings on ${route} at ${width}px`, async ({
            page,
        }) => {
            const hydrationMessages = collectHydrationMessages(page);

            await page.setViewportSize({ width, height: 900 });
            // networkidle hangs against the Next.js dev server due to long-polling
            // clients (e.g. Sentry) — use domcontentloaded + explicit load wait.
            await page.goto(route, {
                waitUntil: "domcontentloaded",
                timeout: 60_000,
            });
            await page.waitForLoadState("load", { timeout: 60_000 });
            // Client-settle wait: lets React finish hydrating and any deferred
            // client-only effects (Radix Portals, HeadlessUI useId, etc.) run.
            await page.waitForTimeout(3_000);

            expect(
                hydrationMessages,
                `Hydration warnings detected on ${route} at ${width}px:\n${hydrationMessages.join("\n") || "(none captured before assertion — investigate)"}`,
            ).toHaveLength(0);
        });
    }
}

// Regression guard for TASK-1603: if the caller in ClubSearchBar drops the
// dropdownId prop, contentId stops flowing through the DropdownComponent →
// DropdownDisplay chain, Radix falls back to its internal useId, and SSR/client
// id drift re-introduces the hydration mismatch. Checking aria-controls on the
// trigger catches this without needing to open the Select popover (which is
// portaled and only mounts on interaction).
test("/club/search distance dropdown exposes static contentId on trigger", async ({
    page,
}) => {
    await page.goto("/club/search", {
        waitUntil: "domcontentloaded",
        timeout: 60_000,
    });
    await page.waitForLoadState("load", { timeout: 60_000 });
    await page.waitForTimeout(1_000);

    const trigger = page.locator('[aria-controls="club-all-distance-listbox"]');
    await expect(trigger).toHaveCount(1);
});
