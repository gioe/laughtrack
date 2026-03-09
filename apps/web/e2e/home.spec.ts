import { test, expect } from "@playwright/test";

test("home page loads and shows main content", async ({ page }) => {
    await page.goto("/");

    await expect(page).toHaveTitle(/LaughTrack/i);
    await expect(page.locator("h1")).toContainText(/laughtrack/i);
});
