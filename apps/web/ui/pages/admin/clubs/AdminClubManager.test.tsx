/**
 * @vitest-environment happy-dom
 */

import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AdminClubGroup } from "@/lib/admin/clubManagement";
import AdminClubManager from "./AdminClubManager";

const groups: AdminClubGroup[] = [
    {
        key: "chain-1",
        chain: {
            id: 1,
            name: "Funny Bone",
            slug: "funny-bone",
            website: "https://example.com/funny-bone",
        },
        totals: {
            clubCount: 2,
            visibleCount: 1,
            activeCount: 1,
            scrapedShowCount: 15,
        },
        clubs: [
            {
                id: 10,
                name: "Funny Bone Albany",
                city: "Albany",
                state: "NY",
                website: "https://example.com/albany",
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
        ],
    },
];

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

describe("AdminClubManager", () => {
    it("renders clubs grouped by chain with scrape counts", () => {
        render(<AdminClubManager groups={groups} />);

        expect(screen.getByText("Funny Bone")).toBeTruthy();
        expect(screen.getByText("Funny Bone Albany")).toBeTruthy();
        expect(screen.getAllByText(/15 scraped shows/).length).toBeGreaterThan(
            0,
        );
        expect(screen.getAllByText("8").length).toBeGreaterThan(0);
        expect(screen.getAllByText(/seatengine/).length).toBeGreaterThan(0);
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

        fireEvent.click(screen.getByRole("button", { name: /Funny Bone/ }));

        fireEvent.change(screen.getByLabelText("Search within Funny Bone"), {
            target: { value: "Boston" },
        });
        expect(screen.getByText("1 of 2 clubs shown")).toBeTruthy();
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
        expect(
            screen.getAllByRole("link", { name: /Funny Bone/ })[0].textContent,
        ).toBe("Funny Bone Boston");
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

        const toggle = screen.getByRole("button", { name: /Funny Bone/ });
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

        fireEvent.click(screen.getByRole("button", { name: /Funny Bone/ }));

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

        fireEvent.click(screen.getByRole("button", { name: /Funny Bone/ }));
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
