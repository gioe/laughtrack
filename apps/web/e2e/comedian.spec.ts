import { test, expect } from "@playwright/test";

test("comedian detail page loads correctly", async ({ page }) => {
    await page.goto("/comedian/search");

    await expect(
        page.getByRole("heading", { name: /search comedians/i }),
    ).toBeVisible();

    // Grab the first comedian card link and capture the name before navigating
    const firstLink = page.locator('a[href^="/comedian/"]').first();
    await expect(firstLink).toBeVisible();
    const comedianName = (await firstLink.innerText()).trim();
    const href = await firstLink.getAttribute("href");

    await page.goto(href!);

    await expect(page.locator("h1")).toContainText(comedianName);
});
