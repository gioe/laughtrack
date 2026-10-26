import { test, expect } from "@playwright/test";

// Run against npm run dev with E2E_FIXTURE_MODE=1. All podcast responses are
// intercepted: this test never requires a published production snapshot.
for (const width of [390, 1440]) {
    test.describe(`podcast discovery at ${width}px`, () => {
        test.use({ viewport: { width, height: 900 }, bypassCSP: true });
        test("main content works while podcast loading is stalled; playback is explicit", async ({
            page,
        }) => {
            let release!: () => void;
            const gate = new Promise<void>((resolve) => {
                release = resolve;
            });
            let audioRequests = 0;
            await page.route("**/snapshot-audio.mp3", async (route) => {
                audioRequests++;
                await route.abort();
            });
            await page.route(
                "**/api/v1/home/podcast-discovery",
                async (route) => {
                    await gate;
                    await route.fulfill({
                        json: {
                            data: {
                                generatedAt: new Date().toISOString(),
                                episodes: Array.from(
                                    { length: 5 },
                                    (_, index) => ({
                                        id: index + 1,
                                        title: `Finding the funny in everyday life ${index + 1}`,
                                        releaseDate: new Date().toISOString(),
                                        audioUrl:
                                            "https://example.com/snapshot-audio.mp3",
                                        podcast: {
                                            id: index + 10,
                                            slug: "comedy-hour",
                                            title: "The Comedy Hour",
                                            imageUrl: null,
                                        },
                                        recommendation: {
                                            appearanceRole: "guest",
                                            comedian: {
                                                id: index,
                                                name: `Avery Stone ${index + 1}`,
                                            },
                                        },
                                    }),
                                ),
                            },
                        },
                    });
                },
            );
            await page.goto("/", { waitUntil: "domcontentloaded" });
            await expect(
                page.getByRole("heading", { name: "Shows tonight" }),
            ).toBeVisible();
            const rail = page.getByTestId("podcast-discovery-rail");
            await rail.scrollIntoViewIfNeeded();
            await expect(rail.getByRole("status")).toBeVisible();
            release();
            await expect(
                rail.getByRole("button", { name: /Play Finding/ }),
            ).toHaveCount(5);
            expect(audioRequests).toBe(0);
            await expect(
                rail.getByRole("link", { name: "Avery Stone 1", exact: true }),
            ).toHaveAttribute("href", "/comedian/Avery%20Stone%201");
            const overflow = await page.evaluate(
                () => document.documentElement.scrollWidth > window.innerWidth,
            );
            expect(overflow).toBe(false);
            await rail.screenshot({
                path: `/private/tmp/podcast-discovery-${width}.png`,
            });
            await rail
                .getByRole("button", { name: /Play Finding/ })
                .first()
                .click();
            await expect(
                page.getByRole("complementary", {
                    name: "Podcast mini-player",
                }),
            ).toBeVisible();
            await expect.poll(() => audioRequests).toBeGreaterThan(0);
        });
    });
}
