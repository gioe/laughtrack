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
import type { AdminComedianListItem } from "@/lib/admin/comedianManagement";
import AdminComedianManager from "./AdminComedianManager";

const mocks = vi.hoisted(() => ({
    refresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        refresh: mocks.refresh,
    }),
}));

const comedians: AdminComedianListItem[] = [
    {
        id: 1,
        uuid: "uuid-1",
        name: "Parent Comic",
        website: "https://parent.example.com",
        websiteScrapingUrl: "https://parent.example.com/tour",
        hasImage: true,
        activeImageAsset: {
            id: 101,
            sourceImageUrl: "https://parent.example.com/original.jpg",
            avatarPath: "comedian-images/1/avatar.jpg",
            heroPath: "comedian-images/1/hero.jpg",
            avatarUrl: "https://test.b-cdn.net/comedian-images/1/avatar.jpg",
            heroUrl: "https://test.b-cdn.net/comedian-images/1/hero.jpg",
            mimeType: "image/jpeg",
            width: 1200,
            height: 1600,
        },
        legacyImageUrl: "https://test.b-cdn.net/comedians/Parent%20Comic.png",
        popularity: 82,
        totalShows: 10,
        parent: null,
        childCount: 0,
        isBlocked: false,
        blockReason: null,
        blockAddedBy: null,
        blockAddedAt: null,
        latestTicketPurchase: {
            url: "https://tickets.example.com/parent",
            showId: 100,
            showName: "Parent Comic Live",
            showDate: "2026-05-20T00:00:00.000Z",
            clubName: "Comedy Cellar",
        },
        attributedPodcasts: [
            {
                id: 10,
                slug: "parent-podcast",
                title: "Parent Podcast",
                feedUrl: "https://example.com/parent.xml",
                websiteUrl: "https://example.com/parent",
                associationType: "owner",
                source: "manual",
                reviewStatus: "approved",
                confidence: 0.96,
            },
        ],
    },
    {
        id: 2,
        uuid: "uuid-2",
        name: "Alias Comic",
        website: null,
        websiteScrapingUrl: null,
        hasImage: false,
        activeImageAsset: null,
        legacyImageUrl: "",
        popularity: 12,
        totalShows: 1,
        parent: null,
        childCount: 0,
        isBlocked: false,
        blockReason: null,
        blockAddedBy: null,
        blockAddedAt: null,
        latestTicketPurchase: null,
        attributedPodcasts: [],
    },
];

beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
            ok: true,
            comedian: {
                ...comedians[1],
                parent: { id: 1, name: "Parent Comic" },
            },
        }),
    }) as never;
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

describe("AdminComedianManager", () => {
    it("renders current image state and legacy fallback previews", () => {
        render(<AdminComedianManager comedians={comedians} />);

        expect(screen.getByText("Active asset")).toBeTruthy();
        expect(screen.getByText("Legacy fallback")).toBeTruthy();
        expect(screen.getAllByText("No current image").length).toBeGreaterThan(
            0,
        );
        expect(
            screen
                .getByAltText("Parent Comic current avatar preview")
                .getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedian-images/1/avatar.jpg");
        expect(
            screen
                .getByAltText("Parent Comic legacy fallback preview")
                .getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedians/Parent%20Comic.png");
    });

    it("displays ranked discovery candidates with score, dimensions, and reasons", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedianId: 2,
                seedPages: ["https://alias.example.com"],
                crawledPages: ["https://alias.example.com/press"],
                candidates: [
                    {
                        imageUrl: "https://alias.example.com/headshot.jpg",
                        sourcePage: "https://alias.example.com/press",
                        width: 1200,
                        height: 1600,
                        mimeType: "image/jpeg",
                        score: 145,
                        reasons: ["headshot signal", "large portrait"],
                    },
                ],
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);

        fireEvent.click(
            screen.getAllByRole("button", { name: "Discover images" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians/images/discover",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({ comedianId: 2 }),
                }),
            );
        });
        expect(screen.getByText("Score 145")).toBeTruthy();
        expect(screen.getAllByText("1200x1600").length).toBeGreaterThan(0);
        expect(screen.getByText("headshot signal")).toBeTruthy();
        expect(screen.getByText("large portrait")).toBeTruthy();
    });

    it("previews avatar and hero crops after selecting a candidate", async () => {
        vi.mocked(global.fetch)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ok: true,
                    comedianId: 2,
                    seedPages: ["https://alias.example.com"],
                    crawledPages: ["https://alias.example.com/press"],
                    candidates: [
                        {
                            imageUrl: "https://alias.example.com/headshot.jpg",
                            sourcePage: "https://alias.example.com/press",
                            width: 1200,
                            height: 1600,
                            mimeType: "image/jpeg",
                            score: 145,
                            reasons: ["headshot signal"],
                        },
                    ],
                }),
            } as never)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ok: true,
                    comedianId: 2,
                    source: {
                        imageUrl: "https://alias.example.com/headshot.jpg",
                        sourcePageUrl: "https://alias.example.com/press",
                        mimeType: "image/jpeg",
                        width: 1200,
                        height: 1600,
                    },
                    avatarDataUrl: "data:image/jpeg;base64,avatar",
                    heroDataUrl: "data:image/jpeg;base64,hero",
                    warnings: ["hero crop may be lower quality"],
                }),
            } as never);
        render(<AdminComedianManager comedians={comedians} />);

        fireEvent.click(
            screen.getAllByRole("button", { name: "Discover images" })[0],
        );
        const candidate = await screen.findByRole("button", {
            name: "Select image candidate 1",
        });
        fireEvent.click(candidate);

        await waitFor(() => {
            expect(global.fetch).toHaveBeenLastCalledWith(
                "/api/admin/comedians/images/preview",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        comedianId: 2,
                        imageUrl: "https://alias.example.com/headshot.jpg",
                        sourcePageUrl: "https://alias.example.com/press",
                    }),
                }),
            );
        });
        expect(
            screen
                .getByAltText("Alias Comic avatar crop preview")
                .getAttribute("src"),
        ).toBe("data:image/jpeg;base64,avatar");
        expect(
            screen
                .getByAltText("Alias Comic hero crop preview")
                .getAttribute("src"),
        ).toBe("data:image/jpeg;base64,hero");
        expect(screen.getByText("hero crop may be lower quality")).toBeTruthy();
    });

    it("previews and publishes manually entered headshot and hero image urls", async () => {
        vi.mocked(global.fetch)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ok: true,
                    comedianId: 2,
                    source: {
                        imageUrl: "https://alias.example.com/headshot.jpg",
                        heroImageUrl: "https://alias.example.com/hero.jpg",
                        sourcePageUrl: null,
                        mimeType: "image/jpeg",
                        width: 1200,
                        height: 1600,
                    },
                    avatarDataUrl: "data:image/jpeg;base64,avatar",
                    heroDataUrl: "data:image/jpeg;base64,hero",
                    warnings: [],
                }),
            } as never)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ok: true,
                    comedianId: 2,
                    asset: {
                        id: 202,
                        sourceImageUrl:
                            "https://alias.example.com/headshot.jpg",
                        originalPath: "comedian-images/2/original.jpg",
                        avatarPath: "comedian-images/2/avatar.jpg",
                        heroPath: "comedian-images/2/hero.jpg",
                        avatarUrl:
                            "https://test.b-cdn.net/comedian-images/2/avatar.jpg",
                        heroUrl:
                            "https://test.b-cdn.net/comedian-images/2/hero.jpg",
                        mimeType: "image/jpeg",
                        width: 1200,
                        height: 1600,
                    },
                }),
            } as never);
        render(<AdminComedianManager comedians={comedians} />);

        fireEvent.change(screen.getAllByLabelText("Headshot image URL")[0], {
            target: { value: "https://alias.example.com/headshot.jpg" },
        });
        fireEvent.change(screen.getAllByLabelText("Hero image URL")[0], {
            target: { value: "https://alias.example.com/hero.jpg" },
        });
        fireEvent.click(
            screen.getAllByRole("button", { name: "Preview image URLs" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenLastCalledWith(
                "/api/admin/comedians/images/preview",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        comedianId: 2,
                        imageUrl: "https://alias.example.com/headshot.jpg",
                        heroImageUrl: "https://alias.example.com/hero.jpg",
                    }),
                }),
            );
        });
        expect(
            screen
                .getByAltText("Alias Comic avatar crop preview")
                .getAttribute("src"),
        ).toBe("data:image/jpeg;base64,avatar");

        fireEvent.click(
            screen.getByRole("button", { name: "Publish selected image" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenLastCalledWith(
                "/api/admin/comedians/images/publish",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        comedianId: 2,
                        imageUrl: "https://alias.example.com/headshot.jpg",
                        heroImageUrl: "https://alias.example.com/hero.jpg",
                    }),
                }),
            );
        });
        expect(screen.getByText("Alias Comic image published.")).toBeTruthy();
    });

    it("updates row preview after publish without losing other comedian edits", async () => {
        vi.mocked(global.fetch)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ok: true,
                    comedianId: 2,
                    seedPages: ["https://alias.example.com"],
                    crawledPages: ["https://alias.example.com/press"],
                    candidates: [
                        {
                            imageUrl: "https://alias.example.com/headshot.jpg",
                            sourcePage: "https://alias.example.com/press",
                            width: 1200,
                            height: 1600,
                            mimeType: "image/jpeg",
                            score: 145,
                            reasons: ["headshot signal"],
                        },
                    ],
                }),
            } as never)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ok: true,
                    comedianId: 2,
                    source: {
                        imageUrl: "https://alias.example.com/headshot.jpg",
                        sourcePageUrl: "https://alias.example.com/press",
                        mimeType: "image/jpeg",
                        width: 1200,
                        height: 1600,
                    },
                    avatarDataUrl: "data:image/jpeg;base64,avatar",
                    heroDataUrl: "data:image/jpeg;base64,hero",
                    warnings: [],
                }),
            } as never)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ok: true,
                    comedianId: 2,
                    asset: {
                        id: 202,
                        sourceImageUrl:
                            "https://alias.example.com/headshot.jpg",
                        originalPath: "comedian-images/2/original.jpg",
                        avatarPath: "comedian-images/2/avatar.jpg",
                        heroPath: "comedian-images/2/hero.jpg",
                        avatarUrl:
                            "https://test.b-cdn.net/comedian-images/2/avatar.jpg",
                        heroUrl:
                            "https://test.b-cdn.net/comedian-images/2/hero.jpg",
                        mimeType: "image/jpeg",
                        width: 1200,
                        height: 1600,
                    },
                }),
            } as never);
        render(<AdminComedianManager comedians={comedians} />);

        const websiteInput = screen.getAllByLabelText("Comedian website")[0];
        fireEvent.change(websiteInput, {
            target: { value: "https://alias.example.com" },
        });
        fireEvent.click(
            screen.getAllByRole("button", { name: "Discover images" })[0],
        );
        fireEvent.click(
            await screen.findByRole("button", {
                name: "Select image candidate 1",
            }),
        );
        fireEvent.click(
            await screen.findByRole("button", {
                name: "Publish selected image",
            }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenLastCalledWith(
                "/api/admin/comedians/images/publish",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        comedianId: 2,
                        imageUrl: "https://alias.example.com/headshot.jpg",
                        sourcePageUrl: "https://alias.example.com/press",
                    }),
                }),
            );
        });
        expect(
            screen
                .getByAltText("Alias Comic current avatar preview")
                .getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedian-images/2/avatar.jpg");
        expect(screen.getByDisplayValue("https://alias.example.com")).toBe(
            websiteInput,
        );
        expect(screen.getByText("Alias Comic image published.")).toBeTruthy();
    });

    it("sorts comedians by popularity", () => {
        render(<AdminComedianManager comedians={comedians} />);

        fireEvent.change(screen.getByLabelText("Sort"), {
            target: { value: "popularity-asc" },
        });

        const headings = screen.getAllByRole("heading", { level: 2 });
        expect(headings[0].textContent).toBe("Alias Comic");
        expect(headings[1].textContent).toBe("Parent Comic");
    });

    it("saves a parent relationship", async () => {
        render(<AdminComedianManager comedians={comedians} />);

        const parentInputs =
            screen.getAllByPlaceholderText("Search parent name");
        fireEvent.change(parentInputs[0], {
            target: { value: "Parent" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Parent Comic" }));
        fireEvent.click(
            screen.getAllByRole("button", {
                name: "Save relationship",
            })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians",
                expect.objectContaining({
                    method: "PATCH",
                    body: JSON.stringify({
                        action: "set-parent",
                        comedianId: 2,
                        parentComedianId: 1,
                    }),
                }),
            );
        });
        expect(mocks.refresh).toHaveBeenCalled();
    });

    it("saves an inline comedian record edit", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedian: {
                    ...comedians[1],
                    name: "Alias Comic",
                    uuid: "updated-uuid",
                    website: "https://alias.example.com",
                    websiteScrapingUrl: "https://alias.example.com/tour",
                },
            }),
        } as never);
        render(
            <AdminComedianManager
                comedians={[
                    comedians[0],
                    {
                        ...comedians[1],
                        name: "alias comic",
                    },
                ]}
            />,
        );

        const nameInputs = screen.getAllByLabelText("Comedian name");
        fireEvent.change(nameInputs[0], {
            target: { value: "Alias Comic" },
        });
        fireEvent.change(screen.getAllByLabelText("Comedian website")[0], {
            target: { value: "https://alias.example.com" },
        });
        fireEvent.change(
            screen.getAllByLabelText("Comedian website scraping URL")[0],
            {
                target: { value: "https://alias.example.com/tour" },
            },
        );
        fireEvent.click(
            screen.getAllByRole("button", { name: "Save record" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians",
                expect.objectContaining({
                    method: "PUT",
                    body: JSON.stringify({
                        comedianId: 2,
                        name: "Alias Comic",
                        website: "https://alias.example.com",
                        websiteScrapingUrl: "https://alias.example.com/tour",
                    }),
                }),
            );
        });
    });

    it("starts podcast attribution dropdowns closed and expands them", () => {
        render(<AdminComedianManager comedians={comedians} />);

        const toggle = screen.getAllByRole("button", {
            name: "Podcasts attributed",
        })[1];
        const panelId = toggle.getAttribute("aria-controls");
        expect(panelId).toBeTruthy();
        const panel = document.getElementById(panelId!);
        expect(panel).toBeTruthy();
        expect(toggle.getAttribute("aria-expanded")).toBe("false");
        expect(panel!.hidden).toBe(true);

        fireEvent.click(toggle);

        expect(toggle.getAttribute("aria-expanded")).toBe("true");
        expect(panel!.hidden).toBe(false);
        expect(screen.getByText("Parent Podcast")).toBeTruthy();
        expect(
            screen.getByRole("link", { name: /RSS/ }).getAttribute("href"),
        ).toBe("https://example.com/parent.xml");
    });

    it("links to the latest ticket purchase url", () => {
        render(<AdminComedianManager comedians={comedians} />);

        const link = screen.getByRole("link", {
            name: /Latest ticket purchase/,
        });

        expect(link.getAttribute("href")).toBe(
            "https://tickets.example.com/parent",
        );
        expect(screen.getByText(/Parent Comic Live/)).toBeTruthy();
    });

    it("adds a comedian to the blocklist", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedian: {
                    ...comedians[0],
                    isBlocked: true,
                    blockReason: "Venue, not a person",
                    blockAddedBy: "profile-1",
                    blockAddedAt: "2026-05-19T12:00:00.000Z",
                },
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);

        const reasonInputs = screen.getAllByLabelText("Blocklist reason");
        fireEvent.change(reasonInputs[0], {
            target: { value: "Venue, not a person" },
        });
        fireEvent.click(
            screen.getAllByRole("button", { name: "Add to blocklist" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians",
                expect.objectContaining({
                    method: "PATCH",
                    body: JSON.stringify({
                        action: "blocklist-add",
                        comedianId: 2,
                        reason: "Venue, not a person",
                    }),
                }),
            );
        });
    });

    it("removes a comedian from the blocklist", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedian: {
                    ...comedians[1],
                    isBlocked: false,
                    blockReason: null,
                    blockAddedBy: null,
                    blockAddedAt: null,
                },
            }),
        } as never);
        render(
            <AdminComedianManager
                comedians={[
                    comedians[0],
                    {
                        ...comedians[1],
                        isBlocked: true,
                        blockReason: "Venue, not a person",
                        blockAddedBy: "profile-1",
                        blockAddedAt: "2026-05-19T12:00:00.000Z",
                    },
                ]}
            />,
        );

        fireEvent.click(
            screen.getByRole("button", { name: "Remove from blocklist" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians",
                expect.objectContaining({
                    method: "PATCH",
                    body: JSON.stringify({
                        action: "blocklist-remove",
                        comedianId: 2,
                    }),
                }),
            );
        });
    });

    it("shows blocked comedians as a minimal row with unblock available", () => {
        render(
            <AdminComedianManager
                comedians={[
                    {
                        ...comedians[1],
                        isBlocked: true,
                        blockReason: "Venue, not a person",
                        blockAddedBy: "profile-1",
                        blockAddedAt: "2026-05-19T12:00:00.000Z",
                    },
                ]}
            />,
        );

        expect(
            screen.getByRole("heading", { level: 2, name: "Alias Comic" }),
        ).toBeTruthy();
        expect(screen.getByText("Blocked")).toBeTruthy();
        expect(screen.getByText("Venue, not a person")).toBeTruthy();
        expect(
            screen.getByRole("button", { name: "Remove from blocklist" }),
        ).toBeTruthy();
        expect(screen.queryByLabelText("Comedian name")).toBeNull();
        expect(screen.queryByLabelText("Comedian website")).toBeNull();
        expect(screen.queryByPlaceholderText("Search parent name")).toBeNull();
        expect(
            screen.queryByRole("button", { name: "Podcasts attributed" }),
        ).toBeNull();
        expect(screen.queryByText("No ticket purchase link found.")).toBeNull();
    });

    it("filters by blocked status", () => {
        render(
            <AdminComedianManager
                comedians={[
                    comedians[0],
                    {
                        ...comedians[1],
                        isBlocked: true,
                        blockReason: "Venue, not a person",
                        blockAddedBy: "profile-1",
                        blockAddedAt: "2026-05-19T12:00:00.000Z",
                    },
                ]}
            />,
        );

        fireEvent.change(screen.getByLabelText("Blocked status"), {
            target: { value: "blocked" },
        });

        expect(screen.getByText("Alias Comic")).toBeTruthy();
        expect(screen.queryByText("Parent Comic")).toBeNull();

        fireEvent.change(screen.getByLabelText("Blocked status"), {
            target: { value: "unblocked" },
        });

        expect(screen.queryByText("Alias Comic")).toBeNull();
        expect(screen.getByText("Parent Comic")).toBeTruthy();
    });
});
