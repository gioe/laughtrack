/**
 * @vitest-environment happy-dom
 */

import {
    cleanup,
    fireEvent,
    render,
    screen,
    within,
    waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AdminClubGroup } from "@/lib/admin/clubManagement";
import AdminClubManager from "./AdminClubManager";

const groups = [
    {
        key: "chain-1",
        chain: {
            id: 1,
            name: "Funny Bone",
            slug: "funny-bone",
            website: "https://example.com/funny-bone",
        },
        totals: {
            clubCount: 3,
            visibleCount: 2,
            activeCount: 2,
            scrapedShowCount: 114,
        },
        clubs: [
            {
                id: 10,
                name: "Funny Bone Albany",
                city: "Albany",
                state: "NY",
                website: "https://example.com/albany",
                popularity: 10,
                hasImage: true,
                iconUrl: "https://cdn.test/clubs/Funny%20Bone%20Albany.png",
                heroUrl:
                    "https://cdn.test/clubs/Funny%20Bone%20Albany-hero.jpg",
                visible: true,
                status: "active",
                clubType: "club",
                closedAt: null,
                totalShows: 8,
                scrapedShowCount: 8,
                latestScrapeAt: "2026-05-18T12:00:00.000Z",
                latestScrapeBy: "seatengine",
                scrapingSources: [
                    {
                        id: 1,
                        platform: "seatengine",
                        scraperKey: "seatengine",
                        enabled: true,
                        priority: 0,
                    },
                ],
                chain: {
                    id: 1,
                    name: "Funny Bone",
                    slug: "funny-bone",
                    website: "https://example.com/funny-bone",
                },
            },
            {
                id: 11,
                name: "Funny Bone Boston",
                city: "Boston",
                state: "MA",
                website: "https://example.com/boston",
                popularity: 90,
                hasImage: false,
                iconUrl: "/placeholders/club-placeholder.svg",
                heroUrl: "",
                visible: false,
                status: "closed",
                clubType: "venue",
                closedAt: null,
                totalShows: 7,
                scrapedShowCount: 7,
                latestScrapeAt: null,
                latestScrapeBy: null,
                scrapingSources: [],
                chain: {
                    id: 1,
                    name: "Funny Bone",
                    slug: "funny-bone",
                    website: "https://example.com/funny-bone",
                },
            },
            {
                id: 12,
                name: "Funny Bone Chicago",
                city: "Chicago",
                state: "IL",
                website: "https://example.com/chicago",
                popularity: 25,
                hasImage: false,
                iconUrl: "/placeholders/club-placeholder.svg",
                heroUrl: "",
                visible: true,
                status: "active",
                clubType: "club",
                closedAt: null,
                totalShows: 99,
                scrapedShowCount: 99,
                latestScrapeAt: null,
                latestScrapeBy: null,
                scrapingSources: [],
                chain: {
                    id: 1,
                    name: "Funny Bone",
                    slug: "funny-bone",
                    website: "https://example.com/funny-bone",
                },
            },
        ],
    },
] satisfies AdminClubGroup[];

beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
            ok: true,
            club: {
                ...groups[0].clubs[0],
                visible: false,
                status: "closed",
                clubType: "festival",
                closedAt: "2026-05-19T00:00:00.000Z",
            },
        }),
    }) as never;
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

function getFunnyBoneGroupToggle() {
    return screen.getByRole("button", {
        name: /^Funny Bone 3 clubs in this chain group/,
    });
}

describe("AdminClubManager", () => {
    it("renders clubs grouped by chain with scrape counts", () => {
        render(<AdminClubManager groups={groups} />);

        expect(screen.getByText("Funny Bone")).toBeTruthy();
        expect(screen.getByText("Funny Bone Albany")).toBeTruthy();
        expect(screen.getAllByText(/114 scraped shows/).length).toBeGreaterThan(
            0,
        );
        expect(screen.getAllByText("8").length).toBeGreaterThan(0);
        expect(screen.getAllByText(/seatengine/).length).toBeGreaterThan(0);
        expect(
            screen
                .getByAltText("Funny Bone Albany current icon image")
                .getAttribute("src"),
        ).toBe("https://cdn.test/clubs/Funny%20Bone%20Albany.png");
        expect(
            screen
                .getByAltText("Funny Bone Albany current hero image")
                .getAttribute("src"),
        ).toBe("https://cdn.test/clubs/Funny%20Bone%20Albany-hero.jpg");
    });

    it("validates and uploads club icon and hero image urls", async () => {
        vi.mocked(global.fetch)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ok: true,
                    clubId: 10,
                    iconDataUrl: "data:image/png;base64,icon",
                    heroDataUrl: "data:image/jpeg;base64,hero",
                    warnings: [],
                }),
            } as never)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ok: true,
                    club: {
                        ...groups[0].clubs[0],
                        hasImage: true,
                        iconUrl:
                            "https://cdn.test/clubs/Funny%20Bone%20Albany.png",
                        heroUrl:
                            "https://cdn.test/clubs/Funny%20Bone%20Albany-hero.jpg",
                    },
                }),
            } as never);
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(getFunnyBoneGroupToggle());
        fireEvent.change(screen.getAllByLabelText("Icon image URL")[0], {
            target: { value: "https://example.com/icon.png" },
        });
        fireEvent.change(screen.getAllByLabelText("Hero image URL")[0], {
            target: { value: "https://example.com/hero.jpg" },
        });
        fireEvent.click(
            screen.getAllByRole("button", { name: "Validate image URLs" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenLastCalledWith(
                "/api/admin/clubs/images/preview",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        clubId: 10,
                        iconImageUrl: "https://example.com/icon.png",
                        heroImageUrl: "https://example.com/hero.jpg",
                    }),
                }),
            );
        });
        expect(
            screen
                .getByAltText("Funny Bone Albany icon preview")
                .getAttribute("src"),
        ).toBe("data:image/png;base64,icon");

        fireEvent.click(
            screen.getByRole("button", { name: "Upload to Bunny CDN" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenLastCalledWith(
                "/api/admin/clubs/images/publish",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        clubId: 10,
                        iconImageUrl: "https://example.com/icon.png",
                        heroImageUrl: "https://example.com/hero.jpg",
                    }),
                }),
            );
        });
        expect(
            screen.getByText("Funny Bone Albany images published."),
        ).toBeTruthy();
    });

    it("shows imageless visible active clubs as a popularity-ranked image review worklist", () => {
        render(<AdminClubManager groups={groups} />);

        const worklist = screen.getByLabelText("Club image review worklist");
        expect(within(worklist).getByText("Funny Bone Chicago")).toBeTruthy();
        expect(within(worklist).queryByText("Funny Bone Boston")).toBeNull();
        expect(within(worklist).queryByText("Funny Bone Albany")).toBeNull();
        expect(within(worklist).getByText("Popularity 25")).toBeTruthy();
        expect(within(worklist).getByText("99 shows")).toBeTruthy();
    });

    it("discovers prospective images and rejects a candidate without publishing it", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                clubId: 12,
                seedPages: ["https://example.com/chicago"],
                crawledPages: ["https://example.com/chicago/gallery"],
                candidates: [
                    {
                        imageUrl: "https://example.com/chicago-stage.jpg",
                        sourcePage: "https://example.com/chicago/gallery",
                        width: 1200,
                        height: 800,
                        mimeType: "image/jpeg",
                        score: 92,
                        reasons: ["venue image", "large image"],
                    },
                ],
            }),
        } as never);
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(
            screen.getByRole("button", {
                name: "Discover images for Funny Bone Chicago",
            }),
        );

        expect(
            await screen.findByText("https://example.com/chicago-stage.jpg"),
        ).toBeTruthy();

        fireEvent.click(
            screen.getByRole("button", {
                name: "Reject image candidate for Funny Bone Chicago",
            }),
        );

        expect(
            screen.queryByText("https://example.com/chicago-stage.jpg"),
        ).toBeNull();
        expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it("approves a discovered image candidate by publishing it and refreshing the club image locally", async () => {
        vi.mocked(global.fetch)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ok: true,
                    clubId: 12,
                    seedPages: ["https://example.com/chicago"],
                    crawledPages: ["https://example.com/chicago/gallery"],
                    candidates: [
                        {
                            imageUrl: "https://example.com/chicago-stage.jpg",
                            sourcePage: "https://example.com/chicago/gallery",
                            width: 1200,
                            height: 800,
                            mimeType: "image/jpeg",
                            score: 92,
                            reasons: ["venue image", "large image"],
                        },
                    ],
                }),
            } as never)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ok: true,
                    club: {
                        ...groups[0].clubs[2],
                        hasImage: true,
                        iconUrl:
                            "https://cdn.test/clubs/Funny%20Bone%20Chicago.png",
                        heroUrl:
                            "https://cdn.test/clubs/Funny%20Bone%20Chicago-hero.jpg",
                    },
                }),
            } as never);
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(
            screen.getByRole("button", {
                name: "Discover images for Funny Bone Chicago",
            }),
        );
        await screen.findByText("https://example.com/chicago-stage.jpg");
        fireEvent.click(
            screen.getByRole("button", {
                name: "Approve image candidate for Funny Bone Chicago",
            }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenLastCalledWith(
                "/api/admin/clubs/images/publish",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        clubId: 12,
                        iconImageUrl: "https://example.com/chicago-stage.jpg",
                        heroImageUrl: "https://example.com/chicago-stage.jpg",
                    }),
                }),
            );
        });
        expect(
            await screen.findByAltText("Funny Bone Chicago current icon image"),
        ).toHaveProperty(
            "src",
            "https://cdn.test/clubs/Funny%20Bone%20Chicago.png",
        );
    });

    it("filters clubs within chain groups", () => {
        render(<AdminClubManager groups={groups} />);

        fireEvent.change(screen.getByLabelText("Search clubs"), {
            target: { value: "Boston" },
        });

        expect(screen.getByText("Funny Bone Boston")).toBeTruthy();
        expect(screen.queryByText("Funny Bone Albany")).toBeNull();
    });

    it("searches, sorts, and filters clubs within an opened chain", () => {
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(getFunnyBoneGroupToggle());

        fireEvent.change(screen.getByLabelText("Search within Funny Bone"), {
            target: { value: "Boston" },
        });
        expect(screen.getByText("1 of 3 clubs shown")).toBeTruthy();
        expect(screen.getByText("Funny Bone Boston")).toBeTruthy();
        expect(screen.queryByText("Funny Bone Albany")).toBeNull();

        fireEvent.change(screen.getByLabelText("Search within Funny Bone"), {
            target: { value: "" },
        });
        fireEvent.change(
            screen.getByLabelText("Filter Funny Bone clubs by status"),
            { target: { value: "closed" } },
        );
        expect(screen.getByText("Funny Bone Boston")).toBeTruthy();
        expect(screen.queryByText("Funny Bone Albany")).toBeNull();

        fireEvent.change(
            screen.getByLabelText("Filter Funny Bone clubs by status"),
            { target: { value: "all" } },
        );
        fireEvent.change(
            screen.getByLabelText("Filter Funny Bone clubs by visibility"),
            { target: { value: "hidden" } },
        );
        expect(screen.getByText("Funny Bone Boston")).toBeTruthy();
        expect(screen.queryByText("Funny Bone Albany")).toBeNull();

        fireEvent.change(
            screen.getByLabelText("Filter Funny Bone clubs by visibility"),
            { target: { value: "all" } },
        );
        fireEvent.change(screen.getByLabelText("Sort Funny Bone clubs"), {
            target: { value: "name-desc" },
        });
        const groupPanelId =
            getFunnyBoneGroupToggle().getAttribute("aria-controls");
        expect(groupPanelId).toBeTruthy();
        const groupPanel = document.getElementById(groupPanelId!);
        expect(groupPanel).toBeTruthy();
        expect(
            within(groupPanel!).getAllByRole("link", { name: /Funny Bone/ })[0]
                .textContent,
        ).toBe("Funny Bone Chicago");
    });

    it("toggles from chain groups to scraper groups", () => {
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(screen.getByRole("button", { name: "By scraper" }));

        expect(screen.getByText("seatengine")).toBeTruthy();
        expect(
            screen.getByRole("button", { name: /No scraping source/ }),
        ).toBeTruthy();

        const scraperToggle = screen.getByRole("button", {
            name: /seatengine/,
        });
        const scraperPanelId = scraperToggle.getAttribute("aria-controls");
        expect(scraperPanelId).toBeTruthy();
        expect(document.getElementById(scraperPanelId!)!.hidden).toBe(true);

        fireEvent.click(scraperToggle);

        expect(document.getElementById(scraperPanelId!)!.hidden).toBe(false);
        expect(screen.getByText("Funny Bone Albany")).toBeTruthy();
        expect(screen.queryByText("Funny Bone Boston")).toBeTruthy();
    });

    it("starts chain groups closed and reopens them", () => {
        render(<AdminClubManager groups={groups} />);

        const toggle = getFunnyBoneGroupToggle();
        const groupId = toggle.getAttribute("aria-controls");
        expect(groupId).toBeTruthy();
        const groupList = document.getElementById(groupId!);
        expect(groupList).toBeTruthy();
        expect(toggle.getAttribute("aria-expanded")).toBe("false");
        expect(groupList!.hidden).toBe(true);

        fireEvent.click(toggle);

        expect(screen.getByText("Funny Bone Albany")).toBeTruthy();
        expect(toggle.getAttribute("aria-expanded")).toBe("true");
        expect(groupList!.hidden).toBe(false);
    });

    it("saves status overrides", async () => {
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(getFunnyBoneGroupToggle());

        const statusSelects = screen.getAllByLabelText("Status");
        fireEvent.change(statusSelects[0], { target: { value: "closed" } });
        fireEvent.change(screen.getAllByLabelText("Visibility")[0], {
            target: { value: "hidden" },
        });
        fireEvent.change(screen.getAllByLabelText("Type")[0], {
            target: { value: "festival" },
        });
        fireEvent.change(screen.getAllByLabelText("Closed date")[0], {
            target: { value: "2026-05-19" },
        });
        fireEvent.click(
            screen.getAllByRole("button", {
                name: "Save status override",
            })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/clubs/10",
                expect.objectContaining({
                    method: "PATCH",
                    body: JSON.stringify({
                        status: "closed",
                        visible: false,
                        clubType: "festival",
                        closedAt: "2026-05-19",
                    }),
                }),
            );
        });
        expect(
            await screen.findByText("Funny Bone Albany saved."),
        ).toBeTruthy();
    });

    it("saves an inline club name edit", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                club: {
                    ...groups[0].clubs[0],
                    name: "Funny Bone Albany Downtown",
                },
            }),
        } as never);
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(getFunnyBoneGroupToggle());
        fireEvent.change(screen.getAllByLabelText("Club name")[0], {
            target: { value: "Funny Bone Albany Downtown" },
        });
        fireEvent.click(
            screen.getAllByRole("button", { name: "Save name" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/clubs/10",
                expect.objectContaining({
                    method: "PATCH",
                    body: JSON.stringify({
                        name: "Funny Bone Albany Downtown",
                    }),
                }),
            );
        });
    });
});
