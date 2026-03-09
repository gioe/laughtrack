import { test, expect } from "@playwright/test";

test("comedian detail page loads correctly", async ({ page }) => {
    await page.goto("/comedian/search");

    await expect(
        page.getByRole("heading", { name: /search comedians/i }),
    ).toBeVisible();

    // Grab the first comedian card link and navigate to the detail page
    const firstLink = page.locator('a[href^="/comedian/"]').first();
    const href = await firstLink.getAttribute("href");
    expect(href).toBeTruthy();

    await page.goto(href!);

    await expect(page.locator("h1")).toBeVisible();
});
