import { test, expect } from "@playwright/test";
import { CAROUSEL_TEST_IDS } from "@/lib/data/home/homeFixtures";

const CAROUSEL_IDS = [
    CAROUSEL_TEST_IDS.showsTonight,
    CAROUSEL_TEST_IDS.trendingThisWeek,
] as const;

const VIEWPORTS = [
    { name: "mobile-390", width: 390, height: 900 },
    { name: "desktop-1440", width: 1440, height: 900 },
] as const;

for (const viewport of VIEWPORTS) {
    test.describe(`home carousels @ ${viewport.name}`, () => {
        test.use({
            viewport: { width: viewport.width, height: viewport.height },
        });

        test("carousels render stable baseline", async ({ page }) => {
            await page.goto("/", {
                waitUntil: "domcontentloaded",
                timeout: 60_000,
            });
            await page.waitForLoadState("load", { timeout: 60_000 });
            // Give React a beat to hydrate so scroll-button measurements settle
            // before the screenshot. The carousel's useEffect resolves
            // canScrollLeft/canScrollRight after layout.
            await page.waitForTimeout(500);

            for (const id of CAROUSEL_IDS) {
                const locator = page.locator(`[data-testid="${id}"]`);
                await expect(locator).toBeVisible();
                await expect(locator).toHaveScreenshot(
                    `${id}-${viewport.name}.png`,
                    {
                        animations: "disabled",
                        maxDiffPixelRatio: 0.01,
                    },
                );
            }
        });
    });
}
