import { test, expect } from "@playwright/test";

test("show listing page renders results", async ({ page }) => {
    await page.goto("/show/search");

    await expect(page.locator("main")).toBeVisible();

    // Either show cards (h2 with club name) or the empty state should be visible
    const showCards = page.locator("section h2").first();
    const emptyState = page.getByText("No Shows Found");

    await expect(showCards.or(emptyState)).toBeVisible({ timeout: 10000 });
});
