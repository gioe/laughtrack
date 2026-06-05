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
        createdAt: "2026-05-01T12:00:00.000Z",
        name: "Parent Comic",
        website: "https://parent.example.com",
        websiteScrapingUrl: "https://parent.example.com/tour",
        instagramAccount: "parentcomic",
        tiktokAccount: null,
        youtubeAccount: null,
        linktree: null,
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
        nameImageUrl: "https://test.b-cdn.net/comedians/Parent%20Comic.png",
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
                reviewStatus: "accepted",
                confidence: 0.96,
            },
        ],
        podcastCandidateReviews: [
            {
                id: 1001,
                source: "itunes",
                sourcePodcastId: "12345",
                candidateStatus: "pending",
                associationType: "host",
                confidence: 0.91,
                createdAt: "2026-05-03T12:00:00.000Z",
                updatedAt: "2026-05-03T12:00:00.000Z",
                podcast: {
                    id: 30,
                    slug: "candidate-podcast",
                    title: "Candidate Podcast",
                    authorName: "Candidate Author",
                    feedUrl: "https://feeds.example.com/candidate.xml",
                    websiteUrl: "https://example.com/candidate",
                    denyListEntry: null,
                },
            },
        ],
    },
    {
        id: 2,
        uuid: "uuid-2",
        createdAt: "2026-05-02T12:00:00.000Z",
        name: "Alias Comic",
        website: null,
        websiteScrapingUrl: null,
        instagramAccount: null,
        tiktokAccount: null,
        youtubeAccount: null,
        linktree: null,
        hasImage: false,
        activeImageAsset: null,
        nameImageUrl: "",
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
        podcastCandidateReviews: [],
    },
];

// Comedian rows render collapsed by default. Most tests exercise the expanded
// editor panel, so expand every row after rendering.
function expandAllRows() {
    document
        .querySelectorAll<HTMLElement>(
            '[aria-controls^="comedian-row-"][aria-expanded="false"]',
        )
        .forEach((toggle) => fireEvent.click(toggle));
}

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

    // The image-upload flow validates dimensions client-side via `new Image()`
    // before posting. Tests fabricate tiny File payloads that the browser would
    // refuse to decode, so stub Image to report headshot-shaped dimensions —
    // hero-slot tests override this individually.
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

describe("AdminComedianManager", () => {
    it("renders current image state and current image previews", () => {
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        expect(screen.getByText("Active asset")).toBeTruthy();
        expect(screen.getAllByText("Current image").length).toBeGreaterThan(0);
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
                .getByAltText("Parent Comic current headshot image")
                .className.includes("h-24"),
        ).toBe(true);
        expect(
            screen
                .getByAltText("Parent Comic current hero image")
                .getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedian-images/1/hero.jpg");
        expect(
            screen
                .getByAltText("Parent Comic current hero image")
                .className.includes("w-40"),
        ).toBe(true);
        expect(
            screen.getByAltText("Parent Comic headshot").getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedian-images/1/avatar.jpg");
    });

    it("uploads a headshot URL without requiring a hero", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedianId: 2,
                asset: {
                    id: 202,
                    sourceImageUrl: "https://alias.example.com/headshot.jpg",
                    originalPath: "comedian-images/2/original.jpg",
                    avatarPath: "comedian-images/2/avatar.jpg",
                    heroPath: null,
                    avatarUrl:
                        "https://test.b-cdn.net/comedian-images/2/avatar.jpg",
                    heroUrl: null,
                    mimeType: "image/jpeg",
                    width: 1200,
                    height: 1200,
                },
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        fireEvent.change(screen.getAllByLabelText("Headshot image URL")[0], {
            target: { value: "https://alias.example.com/headshot.jpg" },
        });
        fireEvent.click(
            screen.getAllByRole("button", { name: "Save headshot URL" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians/images/publish",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        comedianId: 2,
                        headshotImageUrl:
                            "https://alias.example.com/headshot.jpg",
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
            screen.queryByAltText("Alias Comic current hero image"),
        ).toBeNull();
    });

    it("uploads a headshot from a local file", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedianId: 2,
                asset: {
                    id: 202,
                    sourceImageUrl: "upload:headshot.jpg",
                    originalPath: "comedian-images/2/original.jpg",
                    avatarPath: "comedian-images/2/avatar.jpg",
                    heroPath: null,
                    avatarUrl:
                        "https://test.b-cdn.net/comedian-images/2/avatar.jpg",
                    heroUrl: null,
                    mimeType: "image/jpeg",
                    width: 1200,
                    height: 1200,
                },
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        const file = new File([new Uint8Array([1, 2, 3])], "headshot.jpg", {
            type: "image/jpeg",
        });
        // Two-step flow: picking a file stages it (no network call yet),
        // then "Publish to Bunny" sends it to the server.
        fireEvent.change(screen.getAllByLabelText("Upload headshot file")[0], {
            target: { files: [file] },
        });
        await waitFor(() =>
            expect(
                screen.getByRole("button", { name: /Publish to Bunny/ }),
            ).toBeTruthy(),
        );
        expect(global.fetch).not.toHaveBeenCalled();

        fireEvent.click(
            screen.getByRole("button", { name: /Publish to Bunny/ }),
        );

        await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
        const [, options] = vi.mocked(global.fetch).mock.calls[0];
        expect(options).toEqual(expect.objectContaining({ method: "POST" }));
        const body = (options as RequestInit).body as FormData;
        expect(body.get("comedianId")).toBe("2");
        expect(body.get("headshotFile")).toBe(file);
        expect(body.get("heroFile")).toBeNull();
    });

    it("blocks headshot upload when the file's dimensions are wrong", async () => {
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

        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        const file = new File([new Uint8Array([1, 2, 3])], "headshot.jpg", {
            type: "image/jpeg",
        });
        fireEvent.change(screen.getAllByLabelText("Upload headshot file")[0], {
            target: { files: [file] },
        });

        await waitFor(() =>
            expect(
                screen.getAllByText(/Headshot is 400x600/).length,
            ).toBeGreaterThan(0),
        );
        // Invalid files never stage, so no Publish-to-Bunny button appears and
        // no network call is made.
        expect(
            screen.queryByRole("button", { name: /Publish to Bunny/ }),
        ).toBeNull();
        expect(global.fetch).not.toHaveBeenCalled();
    });

    it("uploads a hero URL without resubmitting the current headshot", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedianId: 1,
                asset: {
                    id: 303,
                    sourceImageUrl: "https://new.example.com/hero.jpg",
                    originalPath: "comedian-images/1/original.jpg",
                    avatarPath: "comedian-images/1/avatar.jpg",
                    heroPath: "comedian-images/1/hero-new.jpg",
                    avatarUrl:
                        "https://test.b-cdn.net/comedian-images/1/avatar.jpg",
                    heroUrl:
                        "https://test.b-cdn.net/comedian-images/1/hero-new.jpg",
                    mimeType: "image/jpeg",
                    width: 2400,
                    height: 1350,
                },
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        fireEvent.change(screen.getAllByLabelText("Hero image URL")[1], {
            target: { value: "https://new.example.com/hero.jpg" },
        });
        const heroButton = screen.getAllByRole("button", {
            name: "Save hero URL",
        })[1];

        expect(heroButton.hasAttribute("disabled")).toBe(false);
        fireEvent.click(heroButton);

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians/images/publish",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        comedianId: 1,
                        heroImageUrl: "https://new.example.com/hero.jpg",
                    }),
                }),
            );
        });
    });

    it("removes existing headshot and hero images", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedianId: 1,
                hasImage: false,
                asset: null,
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        fireEvent.click(
            screen.getByRole("button", { name: "Remove all images" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians/images",
                expect.objectContaining({
                    method: "DELETE",
                    body: JSON.stringify({ comedianId: 1, slot: "all" }),
                }),
            );
        });
        expect(
            await screen.findByText("Parent Comic images removed."),
        ).toBeTruthy();
        expect(
            screen.queryByAltText("Parent Comic current headshot image"),
        ).toBeNull();
        expect(
            screen.queryByAltText("Parent Comic current hero image"),
        ).toBeNull();
    });

    it("removes only the existing thumbnail image", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedianId: 1,
                hasImage: true,
                asset: {
                    id: 101,
                    avatarPath: null,
                    heroPath: "comedian-images/1/hero.jpg",
                },
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        fireEvent.click(
            screen.getByRole("button", { name: "Remove thumbnail" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians/images",
                expect.objectContaining({
                    method: "DELETE",
                    body: JSON.stringify({
                        comedianId: 1,
                        slot: "thumbnail",
                    }),
                }),
            );
        });
        await waitFor(() => {
            expect(
                screen.queryByAltText("Parent Comic current headshot image"),
            ).toBeNull();
        });
        expect(
            screen.getByAltText("Parent Comic current hero image"),
        ).toBeTruthy();
        expect(
            screen.getByText("Parent Comic thumbnail removed."),
        ).toBeTruthy();
    });

    it("removes only the existing hero image", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedianId: 1,
                hasImage: true,
                asset: {
                    id: 101,
                    avatarPath: "comedian-images/1/avatar.jpg",
                    heroPath: null,
                },
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        fireEvent.click(screen.getByRole("button", { name: "Remove hero" }));

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians/images",
                expect.objectContaining({
                    method: "DELETE",
                    body: JSON.stringify({ comedianId: 1, slot: "hero" }),
                }),
            );
        });
        expect(
            screen.getByAltText("Parent Comic current headshot image"),
        ).toBeTruthy();
        await waitFor(() => {
            expect(
                screen.queryByAltText("Parent Comic current hero image"),
            ).toBeNull();
        });
        expect(screen.getByText("Parent Comic hero removed.")).toBeTruthy();
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
        expandAllRows();

        fireEvent.change(screen.getAllByLabelText("Hero image URL")[0], {
            target: { value: "https://alias.example.com/hero.jpg" },
        });
        fireEvent.click(
            screen.getAllByRole("button", { name: "Save hero URL" })[0],
        );

        await waitFor(() =>
            expect(
                screen.getAllByText(
                    "Hero source 1200x1200 must be close to a 16:9 ratio",
                ).length,
            ).toBeGreaterThan(0),
        );
        expect(
            screen.queryByAltText("Alias Comic current hero image"),
        ).toBeNull();
    });

    it("uploads manually entered headshot and hero image urls to Bunny CDN", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedianId: 2,
                asset: {
                    id: 202,
                    sourceImageUrl: "https://alias.example.com/headshot.jpg",
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
        expandAllRows();

        fireEvent.change(screen.getAllByLabelText("Headshot image URL")[0], {
            target: { value: "https://alias.example.com/headshot.jpg" },
        });
        fireEvent.change(screen.getAllByLabelText("Hero image URL")[0], {
            target: { value: "https://alias.example.com/hero.jpg" },
        });
        fireEvent.click(
            screen.getAllByRole("button", { name: "Upload changed images" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenLastCalledWith(
                "/api/admin/comedians/images/publish",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        comedianId: 2,
                        headshotImageUrl:
                            "https://alias.example.com/headshot.jpg",
                        heroImageUrl: "https://alias.example.com/hero.jpg",
                    }),
                }),
            );
        });
        await waitFor(() =>
            expect(
                screen.getAllByText("Alias Comic images published.").length,
            ).toBeGreaterThan(0),
        );
    });

    it("updates row preview after publish without losing other comedian edits", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedianId: 2,
                asset: {
                    id: 202,
                    sourceImageUrl: "https://alias.example.com/headshot.jpg",
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
        expandAllRows();

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
            screen.getAllByRole("button", { name: "Upload changed images" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenLastCalledWith(
                "/api/admin/comedians/images/publish",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        comedianId: 2,
                        headshotImageUrl:
                            "https://alias.example.com/headshot.jpg",
                        heroImageUrl: "https://alias.example.com/hero.jpg",
                    }),
                }),
            );
        });
        expect(
            (
                await screen.findByAltText("Alias Comic current headshot image")
            ).getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedian-images/2/avatar.jpg");
        expect(
            screen
                .getByAltText("Alias Comic current hero image")
                .getAttribute("src"),
        ).toBe("https://test.b-cdn.net/comedian-images/2/hero.jpg");
        expect(screen.getByDisplayValue("https://alias.example.com")).toBe(
            websiteInput,
        );
        await waitFor(() =>
            expect(
                screen.getAllByText("Alias Comic images published.").length,
            ).toBeGreaterThan(0),
        );
    });

    it("sorts comedians by popularity", () => {
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        fireEvent.change(screen.getByLabelText("Sort"), {
            target: { value: "popularity-asc" },
        });

        const headings = screen.getAllByRole("heading", { level: 2 });
        expect(headings[0].textContent).toBe("Alias Comic");
        expect(headings[1].textContent).toBe("Parent Comic");
    });

    it("sorts comedians by database insertion date", () => {
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        fireEvent.change(screen.getByLabelText("Sort"), {
            target: { value: "created-desc" },
        });

        let headings = screen.getAllByRole("heading", { level: 2 });
        expect(headings[0].textContent).toBe("Alias Comic");
        expect(headings[1].textContent).toBe("Parent Comic");

        fireEvent.change(screen.getByLabelText("Sort"), {
            target: { value: "created-asc" },
        });

        headings = screen.getAllByRole("heading", { level: 2 });
        expect(headings[0].textContent).toBe("Parent Comic");
        expect(headings[1].textContent).toBe("Alias Comic");
    });

    it("saves a parent relationship", async () => {
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

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

    it("nests children under the parent's Children sub-dropdown instead of as top-level rows", () => {
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

        // Top-level list shows only the parent — the child is hidden.
        expect(
            screen.getByRole("heading", { level: 2, name: "Parent Comic" }),
        ).toBeTruthy();
        expect(
            screen.queryByRole("heading", { level: 2, name: "Alias Comic" }),
        ).toBeNull();

        // Expand the parent and the Children sub-dropdown.
        expandAllRows();
        fireEvent.click(screen.getByRole("button", { name: /^Children/ }));

        expect(screen.getByText("Alias Comic")).toBeTruthy();
        expect(
            screen.getByRole("button", { name: "Remove parent" }),
        ).toBeTruthy();
    });

    it("removes a child parent relationship via the Children sub-dropdown and promotes the child to the top level", async () => {
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
                    comedians[0],
                    {
                        ...comedians[1],
                        parent: { id: 1, name: "Parent Comic" },
                    },
                ]}
            />,
        );
        expandAllRows();
        fireEvent.click(screen.getByRole("button", { name: /^Children/ }));

        fireEvent.click(screen.getByRole("button", { name: "Remove parent" }));

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
        // The child is now its own top-level row with the full editor.
        await waitFor(() => {
            expect(
                screen.getByRole("heading", { level: 2, name: "Alias Comic" }),
            ).toBeTruthy();
        });
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
        expandAllRows();

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
                        instagramAccount: null,
                        tiktokAccount: null,
                        youtubeAccount: null,
                        linktree: null,
                    }),
                }),
            );
        });
    });

    it("saves social media handles via the inline record edit", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedian: {
                    ...comedians[1],
                    instagramAccount: "aliashandle",
                    tiktokAccount: "aliastok",
                    youtubeAccount: "@AliasComic",
                    linktree: "https://linktr.ee/alias",
                },
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        fireEvent.change(
            screen.getAllByLabelText("Comedian Instagram handle")[0],
            { target: { value: "@aliashandle" } },
        );
        fireEvent.change(
            screen.getAllByLabelText("Comedian TikTok handle")[0],
            { target: { value: "aliastok" } },
        );
        fireEvent.change(
            screen.getAllByLabelText("Comedian YouTube handle")[0],
            { target: { value: "@AliasComic" } },
        );
        fireEvent.change(screen.getAllByLabelText("Comedian Linktree URL")[0], {
            target: { value: "https://linktr.ee/alias" },
        });
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
                        website: null,
                        websiteScrapingUrl: null,
                        instagramAccount: "@aliashandle",
                        tiktokAccount: "aliastok",
                        youtubeAccount: "@AliasComic",
                        linktree: "https://linktr.ee/alias",
                    }),
                }),
            );
        });
    });

    it("lets comedian rows collapse and expand", () => {
        render(<AdminComedianManager comedians={comedians} />);

        const toggle = screen.getByRole("button", {
            name: /Parent Comic/,
        });
        const panelId = toggle.getAttribute("aria-controls");
        expect(panelId).toBeTruthy();
        const panel = document.getElementById(panelId!);
        expect(panel).toBeTruthy();
        // Rows default to collapsed.
        expect(toggle.getAttribute("aria-expanded")).toBe("false");
        expect(panel!.hidden).toBe(true);

        fireEvent.click(toggle);

        expect(toggle.getAttribute("aria-expanded")).toBe("true");
        expect(panel!.hidden).toBe(false);
        expect(within(panel!).getByText("Podcast RSS")).toBeTruthy();

        fireEvent.click(toggle);

        expect(toggle.getAttribute("aria-expanded")).toBe("false");
        expect(panel!.hidden).toBe(true);
    });

    it("shows and updates existing podcast RSS feed links in the comedian section", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                podcast: {
                    id: 10,
                    slug: "parent-podcast",
                    title: "Parent Podcast",
                    feedUrl: "https://example.com/updated.xml",
                    websiteUrl: "https://example.com/parent",
                    associationType: "owner",
                    source: "manual",
                    reviewStatus: "accepted",
                    confidence: 0.96,
                },
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        expect(screen.getAllByText("Parent Podcast").length).toBeGreaterThan(0);
        expect(
            screen
                .getByLabelText("RSS feed for Parent Podcast")
                .getAttribute("value"),
        ).toBe("https://example.com/parent.xml");

        const input = screen.getByLabelText("RSS feed for Parent Podcast");
        fireEvent.change(input, {
            target: { value: "https://example.com/updated.xml" },
        });
        fireEvent.click(
            within(input.closest("label")!.parentElement!).getByRole("button", {
                name: "Save RSS",
            }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians/podcasts",
                expect.objectContaining({
                    method: "PATCH",
                    body: JSON.stringify({
                        comedianId: 1,
                        podcastId: 10,
                        feedUrl: "https://example.com/updated.xml",
                    }),
                }),
            );
        });
        expect(
            await screen.findByText("Parent Podcast RSS saved."),
        ).toBeTruthy();
    });

    it("removes existing podcast RSS feed links in the comedian section", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                podcast: {
                    id: 10,
                    slug: "parent-podcast",
                    title: "Parent Podcast",
                    feedUrl: null,
                    websiteUrl: "https://example.com/parent",
                    associationType: "owner",
                    source: "manual",
                    reviewStatus: "accepted",
                    confidence: 0.96,
                },
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        fireEvent.click(
            screen.getAllByRole("button", { name: "Remove RSS" })[0],
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians/podcasts",
                expect.objectContaining({
                    method: "PATCH",
                    body: JSON.stringify({
                        comedianId: 1,
                        podcastId: 10,
                        feedUrl: null,
                    }),
                }),
            );
        });
    });

    it("ingests a manual RSS feed when the comedian has no podcast", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                podcast: {
                    id: 20,
                    slug: "alias-podcast",
                    title: "Alias Podcast",
                    feedUrl: "https://feeds.example.com/alias.xml",
                },
                episodeCount: 2,
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        const input = screen.getByLabelText("RSS feed URL for Alias Comic");
        fireEvent.change(input, {
            target: { value: "https://feeds.example.com/alias.xml" },
        });
        fireEvent.click(
            within(input.closest("div")!).getByRole("button", {
                name: "Save RSS",
            }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-ownership-reviews",
                expect.objectContaining({
                    method: "PUT",
                    body: JSON.stringify({
                        comedianId: 2,
                        feedUrl: "https://feeds.example.com/alias.xml",
                        reason: "Manual RSS feed added from comedian admin for Alias Comic",
                    }),
                }),
            );
        });
        expect(
            await screen.findByText("Alias Podcast RSS added."),
        ).toBeTruthy();
        expect(screen.getAllByText("Alias Podcast").length).toBeGreaterThan(0);
    });

    it("does not render rejected duplicate podcast attributions", () => {
        render(
            <AdminComedianManager
                comedians={[
                    {
                        ...comedians[0],
                        attributedPodcasts: [
                            {
                                ...comedians[0].attributedPodcasts[0],
                                id: 10,
                                title: "Wild Ride! with Steve-O",
                                reviewStatus: "accepted",
                                source: "manual",
                            },
                            {
                                ...comedians[0].attributedPodcasts[0],
                                id: 10,
                                title: "Wild Ride! with Steve-O",
                                reviewStatus: "rejected",
                                source: "podcast_index",
                            },
                        ],
                    },
                ]}
            />,
        );
        expandAllRows();

        expect(screen.getByText("1 podcasts")).toBeTruthy();
        expect(screen.getAllByText("Wild Ride! with Steve-O")).toHaveLength(1);
    });

    // TASK-2658: these three tests (this one + "removes a host candidate after
    // rejection" + "adds a comedian to the blocklist") flaked once during
    // TASK-2656's commit-time test gate at suspiciously long durations
    // (10.2s / 6.3s / 6.2s). Under a 3-way-parallel-suite contention repro the
    // failure mode is consistently "Test timed out in 5000ms" — vitest's
    // default testTimeout. The assertions themselves are correct; what blows
    // the budget under CPU starvation is that waitFor's poll loop, React's
    // re-render after setRows, and testTimeout enforcement all share the same
    // starved event loop, so 50ms-interval polls and the 5s timeout itself
    // slip. Raising testTimeout to 15s on just these three tests is targeted
    // (not a vitest.config bump) and gives ~3x default headroom — well above
    // the worst observed 10.2s wall time. If a fourth test in this file ever
    // shows the same shape, file a follow-up to widen the override rather than
    // bumping the global config.
    it("reviews podcast host candidates from the comedian row", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedian: {
                    ...comedians[0],
                    podcastCandidateReviews: [],
                },
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        expect(screen.getByText("Podcast host reviews")).toBeTruthy();
        expect(screen.getByText("Candidate Podcast")).toBeTruthy();
        expect(
            screen.getByRole("link", {
                name: /RSS: https:\/\/feeds\.example\.com\/candidate\.xml/,
            }),
        ).toBeTruthy();
        fireEvent.click(screen.getByRole("button", { name: "Accept as host" }));

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians",
                expect.objectContaining({
                    method: "PATCH",
                    body: JSON.stringify({
                        action: "podcast-review-accept-host",
                        comedianId: 1,
                        candidateReviewId: 1001,
                    }),
                }),
            );
        });
        await waitFor(() => {
            expect(screen.queryByText("Podcast host reviews")).toBeNull();
            expect(screen.queryByText("Candidate Podcast")).toBeNull();
        });
    }, 15000);

    // 15s timeout: see TASK-2658 rationale block above "reviews podcast host
    // candidates from the comedian row" — parallel-suite CPU starvation.
    it("removes a host candidate after rejection", async () => {
        const rejectedComedian = {
            ...comedians[0],
            podcastCandidateReviews: [],
        };
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedian: rejectedComedian,
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        expect(
            screen.queryByRole("button", { name: "Block podcast" }),
        ).toBeNull();
        fireEvent.click(screen.getByRole("button", { name: "Reject as host" }));

        await waitFor(() => {
            expect(screen.queryByText("Podcast host reviews")).toBeNull();
        });
        expect(screen.queryByText("Candidate Podcast")).toBeNull();
        expect(
            screen.queryByRole("button", { name: "Block podcast" }),
        ).toBeNull();
    }, 15000);

    it("links to the latest ticket purchase url", () => {
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        const link = screen.getByRole("link", {
            name: /Latest ticket purchase/,
        });

        expect(link.getAttribute("href")).toBe(
            "https://tickets.example.com/parent",
        );
        expect(screen.getByText(/Parent Comic Live/)).toBeTruthy();
    });

    // 15s timeout: see TASK-2658 rationale block above "reviews podcast host
    // candidates from the comedian row" — parallel-suite CPU starvation.
    it("blocks a comedian with the row toggle and default reason", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                comedian: {
                    ...comedians[0],
                    isBlocked: true,
                    blockReason: "not a comic",
                    blockAddedBy: "profile-1",
                    blockAddedAt: "2026-05-19T12:00:00.000Z",
                },
            }),
        } as never);
        render(<AdminComedianManager comedians={comedians} />);
        expandAllRows();

        expect(screen.queryByLabelText("Blocklist reason")).toBeNull();
        expect(
            screen.queryByRole("button", { name: "Add to blocklist" }),
        ).toBeNull();

        const parentBlocklistGroup = screen.getByRole("group", {
            name: "Parent and blocklist for Alias Comic",
        });

        fireEvent.click(
            within(parentBlocklistGroup).getByRole("checkbox", {
                name: "Blocked status for Alias Comic",
            }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/comedians",
                expect.objectContaining({
                    method: "PATCH",
                    body: JSON.stringify({
                        action: "blocklist-add",
                        comedianId: 2,
                        reason: "not a comic",
                    }),
                }),
            );
        });
    }, 15000);

    it("unblocks a comedian with the row toggle", async () => {
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
        expandAllRows();
        fireEvent.click(screen.getByRole("checkbox", { name: "Blocked" }));
        expandAllRows();

        fireEvent.click(
            screen.getByRole("checkbox", {
                name: "Blocked status for Alias Comic",
            }),
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
        expandAllRows();
        fireEvent.click(screen.getByRole("checkbox", { name: "Blocked" }));
        expandAllRows();

        expect(
            screen.getByRole("heading", { level: 2, name: "Alias Comic" }),
        ).toBeTruthy();
        expect(screen.getAllByText("Blocked").length).toBeGreaterThan(1);
        expect(screen.getByText("Venue, not a person")).toBeTruthy();
        expect(
            (
                screen.getByRole("checkbox", {
                    name: "Blocked status for Alias Comic",
                }) as HTMLInputElement
            ).checked,
        ).toBe(true);
        expect(
            screen.queryByRole("button", { name: "Remove from blocklist" }),
        ).toBeNull();
        expect(screen.queryByLabelText("Comedian name")).toBeNull();
        expect(screen.queryByLabelText("Comedian website")).toBeNull();
        expect(screen.queryByPlaceholderText("Search parent name")).toBeNull();
        expect(screen.queryByText("Blocklist state")).toBeNull();
        expect(screen.queryByLabelText("Blocklist reason")).toBeNull();
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
        expandAllRows();

        expect(screen.queryByRole("combobox", { name: "Blocked" })).toBeNull();
        expect(screen.getByText("Parent Comic")).toBeTruthy();
        expect(screen.queryByText("Alias Comic")).toBeNull();

        fireEvent.click(screen.getByRole("checkbox", { name: "Blocked" }));

        expect(screen.getByText("Alias Comic")).toBeTruthy();
        expect(screen.queryByText("Parent Comic")).toBeNull();

        fireEvent.click(screen.getByRole("checkbox", { name: "Blocked" }));

        expect(screen.getByText("Parent Comic")).toBeTruthy();
        expect(screen.queryByText("Alias Comic")).toBeNull();
    });

    it("hides children from the top level by default", () => {
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

        expect(
            screen.getByRole("heading", { level: 2, name: "Parent Comic" }),
        ).toBeTruthy();
        expect(
            screen.queryByRole("heading", { level: 2, name: "Alias Comic" }),
        ).toBeNull();
        // The Parent filter checkbox is gone — child suppression is implicit.
        expect(screen.queryByRole("checkbox", { name: "Parent" })).toBeNull();
    });
});
