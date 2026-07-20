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
                activeImageAsset: {
                    id: 100,
                    sourceImageUrl: "https://source.test/albany.png",
                    originalPath: "club-images/10/current/original.png",
                    iconPath: "club-images/10/current/icon.png",
                    heroPath: "club-images/10/current/hero.jpg",
                    iconUrl: "https://cdn.test/club-images/10/current/icon.png",
                    heroUrl: "https://cdn.test/club-images/10/current/hero.jpg",
                    mimeType: "image/png",
                    width: 800,
                    height: 800,
                },
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
                activeImageAsset: null,
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
                activeImageAsset: null,
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

    class FakeImage {
        public onload: (() => void) | null = null;
        public onerror: (() => void) | null = null;
        public naturalWidth = 1000;
        public naturalHeight = 1000;
        set src(_value: string) {
            queueMicrotask(() => this.onload?.());
        }
    }
    (global as unknown as { Image: typeof FakeImage }).Image = FakeImage;
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
            { target: { value: "blocked" } },
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

    it("preserves unsaved row edits across group views", () => {
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(getFunnyBoneGroupToggle());
        fireEvent.change(screen.getAllByLabelText("Club name")[0], {
            target: { value: "Albany Draft Name" },
        });

        fireEvent.click(screen.getByRole("button", { name: "By scraper" }));
        fireEvent.click(screen.getByRole("button", { name: /seatengine/ }));

        expect(
            screen
                .getAllByLabelText("Club name")
                .some(
                    (input) =>
                        (input as HTMLInputElement).value ===
                        "Albany Draft Name",
                ),
        ).toBe(true);

        fireEvent.click(screen.getByRole("button", { name: "By chain" }));

        expect(
            (screen.getAllByLabelText("Club name")[0] as HTMLInputElement)
                .value,
        ).toBe("Albany Draft Name");
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

    it("includes not_open_yet in status controls", () => {
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(getFunnyBoneGroupToggle());

        const statusFilter = screen.getByLabelText(
            "Filter Funny Bone clubs by status",
        );
        expect(
            within(statusFilter).getByRole("option", {
                name: "not_open_yet",
            }),
        ).toBeTruthy();
        expect(
            within(screen.getAllByLabelText("Status")[0]).getByRole("option", {
                name: "not_open_yet",
            }),
        ).toBeTruthy();
    });

    it("includes every intentional club type in type controls", () => {
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(getFunnyBoneGroupToggle());

        const expectedTypes = [
            "club",
            "venue",
            "festival",
            "producer",
            "secret_location",
            "non_comedy",
        ];
        const typeFilter = screen.getByLabelText(
            "Filter Funny Bone clubs by type",
        );
        for (const type of expectedTypes) {
            expect(
                within(typeFilter).getByRole("option", { name: type }),
            ).toBeTruthy();
        }
        for (const type of expectedTypes) {
            expect(
                within(screen.getAllByLabelText("Type")[0]).getByRole(
                    "option",
                    { name: type },
                ),
            ).toBeTruthy();
        }
    });

    it("saves status overrides", async () => {
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(getFunnyBoneGroupToggle());

        const statusSelects = screen.getAllByLabelText("Status");
        fireEvent.change(statusSelects[0], { target: { value: "closed" } });
        fireEvent.change(screen.getAllByLabelText("Visibility")[0], {
            target: { value: "blocked" },
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

    it("uploads a club thumbnail from a URL", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                clubId: 11,
                hasImage: true,
                asset: {
                    id: 201,
                    sourceImageUrl: "https://images.example.com/boston.png",
                    originalPath: "club-images/11/new/original.png",
                    iconPath: "club-images/11/new/icon.png",
                    heroPath: null,
                    iconUrl: "https://cdn.test/club-images/11/new/icon.png",
                    heroUrl: null,
                    mimeType: "image/png",
                    width: 900,
                    height: 900,
                },
            }),
        } as never);
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(getFunnyBoneGroupToggle());
        const urlInputs = screen.getAllByLabelText("Club thumbnail image URL");
        fireEvent.change(urlInputs[1], {
            target: { value: "https://images.example.com/boston.png" },
        });
        fireEvent.click(
            screen.getAllByRole("button", {
                name: "Save club thumbnail URL",
            })[1],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/clubs/images/publish",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        clubId: 11,
                        iconImageUrl: "https://images.example.com/boston.png",
                    }),
                }),
            );
        });
        expect(
            await screen.findAllByText("Funny Bone Boston thumbnail updated."),
        ).toHaveLength(2);
        expect(
            screen
                .getByAltText("Funny Bone Boston current thumbnail image")
                .getAttribute("src"),
        ).toBe("https://cdn.test/club-images/11/new/icon.png");
    });

    it("stages and publishes a club thumbnail file", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                clubId: 11,
                hasImage: true,
                asset: {
                    id: 201,
                    sourceImageUrl: "upload:thumbnail.png",
                    originalPath: "club-images/11/new/original.png",
                    iconPath: "club-images/11/new/icon.png",
                    heroPath: null,
                    iconUrl: "https://cdn.test/club-images/11/new/icon.png",
                    heroUrl: null,
                    mimeType: "image/png",
                    width: 1000,
                    height: 1000,
                },
            }),
        } as never);
        render(<AdminClubManager groups={groups} />);
        fireEvent.click(getFunnyBoneGroupToggle());

        const file = new File([new Uint8Array([1, 2, 3])], "thumbnail.png", {
            type: "image/png",
        });
        fireEvent.change(
            screen.getAllByLabelText("Upload club thumbnail file")[1],
            { target: { files: [file] } },
        );

        expect(
            await screen.findByAltText("Funny Bone Boston pending thumbnail"),
        ).toBeTruthy();
        expect(global.fetch).not.toHaveBeenCalled();

        fireEvent.click(
            screen.getByRole("button", { name: "Publish to Bunny" }),
        );

        await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
        const [url, options] = vi.mocked(global.fetch).mock.calls[0];
        expect(url).toBe("/api/admin/clubs/images/publish");
        expect(options).toEqual(expect.objectContaining({ method: "POST" }));
        const body = (options as RequestInit).body as FormData;
        expect(body.get("clubId")).toBe("11");
        expect(body.get("iconFile")).toBe(file);
        expect(
            (
                await screen.findByAltText(
                    "Funny Bone Boston current thumbnail image",
                )
            ).getAttribute("src"),
        ).toBe("https://cdn.test/club-images/11/new/icon.png");
    });

    it("rejects invalid club thumbnail dimensions before staging", async () => {
        class WrongShapeImage {
            public onload: (() => void) | null = null;
            public onerror: (() => void) | null = null;
            public naturalWidth = 400;
            public naturalHeight = 600;
            set src(_value: string) {
                queueMicrotask(() => this.onload?.());
            }
        }
        (global as unknown as { Image: typeof WrongShapeImage }).Image =
            WrongShapeImage;

        render(<AdminClubManager groups={groups} />);
        fireEvent.click(getFunnyBoneGroupToggle());
        const file = new File([new Uint8Array([1, 2, 3])], "thumbnail.png", {
            type: "image/png",
        });
        fireEvent.change(
            screen.getAllByLabelText("Upload club thumbnail file")[1],
            { target: { files: [file] } },
        );

        expect((await screen.findByRole("alert")).textContent).toContain(
            "Headshot is 400x600",
        );
        expect(
            screen.queryByAltText("Funny Bone Boston pending thumbnail"),
        ).toBeNull();
        expect(global.fetch).not.toHaveBeenCalled();
    });

    it("discards a staged club thumbnail without publishing", async () => {
        render(<AdminClubManager groups={groups} />);
        fireEvent.click(getFunnyBoneGroupToggle());
        const file = new File([new Uint8Array([1, 2, 3])], "thumbnail.png", {
            type: "image/png",
        });
        fireEvent.change(
            screen.getAllByLabelText("Upload club thumbnail file")[1],
            { target: { files: [file] } },
        );

        expect(
            await screen.findByAltText("Funny Bone Boston pending thumbnail"),
        ).toBeTruthy();
        fireEvent.click(screen.getByRole("button", { name: "Discard" }));

        await waitFor(() =>
            expect(
                screen.queryByAltText("Funny Bone Boston pending thumbnail"),
            ).toBeNull(),
        );
        expect(
            screen.queryByRole("button", { name: "Publish to Bunny" }),
        ).toBeNull();
        expect(global.fetch).not.toHaveBeenCalled();
    });

    it("removes an existing club thumbnail", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                clubId: 10,
                hasImage: false,
                asset: null,
            }),
        } as never);
        render(<AdminClubManager groups={groups} />);

        fireEvent.click(getFunnyBoneGroupToggle());
        fireEvent.click(
            screen.getAllByRole("button", { name: "Remove thumbnail" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/clubs/images",
                expect.objectContaining({
                    method: "DELETE",
                    body: JSON.stringify({ clubId: 10 }),
                }),
            );
        });
        expect(
            await screen.findAllByText("Funny Bone Albany thumbnail removed."),
        ).toHaveLength(2);
    });
});
