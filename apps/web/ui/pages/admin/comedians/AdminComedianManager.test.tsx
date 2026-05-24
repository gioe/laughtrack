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
            screen.queryByRole("button", { name: "Discover images" }),
        ).toBeNull();
        expect(
            screen
                .getByAltText("Parent Comic current headshot image")
                .getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedian-images/1/avatar.jpg");
        expect(
            screen
                .getByAltText("Parent Comic current hero image")
                .getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedian-images/1/hero.jpg");
        expect(
            screen
                .getByAltText("Parent Comic legacy fallback preview")
                .getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedians/Parent%20Comic.png");
    });

    it("validates manually entered image urls before upload", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedianId: 2,
                source: {
                    imageUrl: "https://alias.example.com/headshot.jpg",
                    heroImageUrl: "https://alias.example.com/hero.jpg",
                    sourcePageUrl: null,
                    mimeType: "image/jpeg",
                    width: 1600,
                    height: 1600,
                },
                avatarDataUrl: "data:image/jpeg;base64,avatar",
                heroDataUrl: "data:image/jpeg;base64,hero",
                warnings: [],
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
            screen.getAllByRole("button", { name: "Validate image URLs" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
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
        expect(
            screen
                .getByAltText("Alias Comic hero crop preview")
                .getAttribute("src"),
        ).toBe("data:image/jpeg;base64,hero");
    });

    it("surfaces ratio validation errors for manual image urls", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: false,
            status: 400,
            json: async () => ({
                error: "Hero source 1200x1200 must be close to a 16:9 ratio",
                code: "INVALID_ASPECT_RATIO",
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
            screen.getAllByRole("button", { name: "Validate image URLs" })[0],
        );

        expect(
            await screen.findByText(
                "Hero source 1200x1200 must be close to a 16:9 ratio",
            ),
        ).toBeTruthy();
        expect(
            screen.queryByRole("button", { name: "Upload to Bunny CDN" }),
        ).toBeNull();
    });

    it("uploads manually entered headshot and hero image urls to Bunny CDN", async () => {
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
            screen.getAllByRole("button", { name: "Validate image URLs" })[0],
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
            screen.getByRole("button", { name: "Upload to Bunny CDN" }),
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
                    source: {
                        imageUrl: "https://alias.example.com/headshot.jpg",
                        heroImageUrl: "https://alias.example.com/hero.jpg",
                        sourcePageUrl: null,
                        mimeType: "image/jpeg",
                        width: 1600,
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
        fireEvent.change(screen.getAllByLabelText("Headshot image URL")[0], {
            target: { value: "https://alias.example.com/headshot.jpg" },
        });
        fireEvent.change(screen.getAllByLabelText("Hero image URL")[0], {
            target: { value: "https://alias.example.com/hero.jpg" },
        });
        fireEvent.click(
            screen.getAllByRole("button", { name: "Validate image URLs" })[0],
        );
        fireEvent.click(
            await screen.findByRole("button", { name: "Upload to Bunny CDN" }),
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
        expect(
            screen
                .getByAltText("Alias Comic current headshot image")
                .getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedian-images/2/avatar.jpg");
        expect(
            screen
                .getByAltText("Alias Comic current hero image")
                .getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedian-images/2/hero.jpg");
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

    it("shows child comedians as a minimal row with remove parent available", () => {
        render(
            <AdminComedianManager
                comedians={[
                    {
                        ...comedians[1],
                        parent: { id: 1, name: "Parent Comic" },
                    },
                ]}
            />,
        );

        expect(
            screen.getByRole("heading", { level: 2, name: "Alias Comic" }),
        ).toBeTruthy();
        expect(screen.getByText("Child")).toBeTruthy();
        expect(screen.getByText("Parent Comic")).toBeTruthy();
        expect(
            screen.getByRole("button", { name: "Remove parent relationship" }),
        ).toBeTruthy();
        expect(screen.queryByLabelText("Comedian name")).toBeNull();
        expect(screen.queryByLabelText("Headshot image URL")).toBeNull();
        expect(screen.queryByPlaceholderText("Search parent name")).toBeNull();
        expect(
            screen.queryByRole("button", { name: "Podcasts attributed" }),
        ).toBeNull();
        expect(
            screen.queryByRole("button", { name: "Add to blocklist" }),
        ).toBeNull();
    });

    it("renders the full row after removing a child parent relationship", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedian: {
                    ...comedians[1],
                    parent: null,
                },
            }),
        } as never);
        render(
            <AdminComedianManager
                comedians={[
                    {
                        ...comedians[1],
                        parent: { id: 1, name: "Parent Comic" },
                    },
                ]}
            />,
        );

        fireEvent.click(
            screen.getByRole("button", { name: "Remove parent relationship" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians",
                expect.objectContaining({
                    method: "PATCH",
                    body: JSON.stringify({
                        action: "set-parent",
                        comedianId: 2,
                        parentComedianId: null,
                    }),
                }),
            );
        });
        expect(screen.getByLabelText("Comedian name")).toBeTruthy();
        expect(screen.getByLabelText("Headshot image URL")).toBeTruthy();
        expect(screen.queryByText("Child")).toBeNull();
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

    it("filters to blocked comedians with a checkbox", () => {
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

        expect(
            screen.queryByRole("combobox", { name: "Blocked status" }),
        ).toBeNull();

        fireEvent.click(
            screen.getByRole("checkbox", { name: "Blocked status" }),
        );

        expect(screen.getByText("Alias Comic")).toBeTruthy();
        expect(screen.queryByText("Parent Comic")).toBeNull();

        fireEvent.click(
            screen.getByRole("checkbox", { name: "Blocked status" }),
        );

        expect(screen.getByText("Alias Comic")).toBeTruthy();
        expect(screen.getByText("Parent Comic")).toBeTruthy();
    });

    it("filters to parent comedians with a checkbox", () => {
        render(
            <AdminComedianManager
                comedians={[
                    comedians[0],
                    {
                        ...comedians[1],
                        parent: { id: 1, name: "Parent Comic" },
                    },
                ]}
            />,
        );

        fireEvent.click(screen.getByRole("checkbox", { name: "Is Parent" }));

        expect(screen.getByText("Parent Comic")).toBeTruthy();
        expect(screen.queryByText("Alias Comic")).toBeNull();
    });
});
