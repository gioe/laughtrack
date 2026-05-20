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
import AdminPodcastOwnershipReviewManager, {
    type AdminPodcastOwnershipReviewCandidate,
} from "./AdminPodcastOwnershipReviewManager";

const mocks = vi.hoisted(() => ({
    refresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        refresh: mocks.refresh,
    }),
}));

const candidate: AdminPodcastOwnershipReviewCandidate = {
    id: 12,
    source: "podcast-index",
    sourcePodcastId: "feed-99",
    candidateStatus: "pending",
    associationType: "host",
    confidence: 0.91,
    evidence: { matched_name: "Jane Comic" },
    createdAt: "2026-05-17T12:00:00.000Z",
    updatedAt: "2026-05-17T12:00:00.000Z",
    comedian: { id: 42, uuid: "uuid-42", name: "Jane Comic", popularity: 74 },
    podcast: {
        id: 99,
        slug: "jane-show",
        title: "The Jane Show",
        authorName: "Jane Comic",
        imageUrl: null,
        websiteUrl: "https://pod.example",
        feedUrl: "https://pod.example/feed.xml",
    },
    existingOwnerships: [],
};

beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ ok: true }),
    }) as never;
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

function openGroup(name: RegExp | string) {
    fireEvent.click(screen.getByRole("button", { name }));
}

describe("AdminPodcastOwnershipReviewManager", () => {
    it("renders candidate context and evidence", () => {
        render(<AdminPodcastOwnershipReviewManager candidates={[candidate]} />);

        openGroup(/The Jane Show/);

        expect(screen.getAllByText("Jane Comic").length).toBeGreaterThan(0);
        expect(screen.getAllByText("The Jane Show").length).toBeGreaterThan(0);
        expect(screen.getByText("Owner: Jane Comic")).toBeTruthy();
        expect(screen.getAllByText("91%").length).toBeGreaterThan(0);
        expect(screen.getByText(/matched_name/)).toBeTruthy();
    });

    it("does not preselect owners for non-pending rejected candidates", () => {
        render(
            <AdminPodcastOwnershipReviewManager
                candidates={[
                    {
                        ...candidate,
                        candidateStatus: "rejected",
                        existingOwnerships: [],
                    },
                ]}
            />,
        );

        openGroup(/The Jane Show/);

        expect(screen.getByText("No owner")).toBeTruthy();
        expect(screen.getAllByText(/blocked/i).length).toBeGreaterThan(0);
    });

    it("switches to comedian view and sorts by popularity", () => {
        const lowerPopularityCandidate: AdminPodcastOwnershipReviewCandidate = {
            ...candidate,
            id: 13,
            comedian: {
                id: 77,
                uuid: "uuid-77",
                name: "Lower Pop",
                popularity: 0.06,
            },
            podcast: {
                ...candidate.podcast!,
                id: 100,
                slug: "lower-pop-show",
                title: "Lower Pop Show",
            },
        };
        const nonOwnedJaneCandidate: AdminPodcastOwnershipReviewCandidate = {
            ...candidate,
            id: 14,
            podcast: {
                ...candidate.podcast!,
                id: 101,
                slug: "jane-guest-show",
                title: "Jane Guest Show",
            },
            existingOwnerships: [
                {
                    id: 202,
                    associationType: "owner",
                    source: "manual",
                    reviewStatus: "accepted",
                    confidence: 1,
                    reviewedAt: "2026-05-18T12:00:00.000Z",
                    reviewedBy: "profile-1",
                    comedian: {
                        id: 88,
                        uuid: "uuid-88",
                        name: "Other Owner",
                        popularity: 2,
                    },
                },
            ],
        };
        render(
            <AdminPodcastOwnershipReviewManager
                candidates={[
                    lowerPopularityCandidate,
                    nonOwnedJaneCandidate,
                    candidate,
                ]}
            />,
        );

        fireEvent.click(screen.getByRole("button", { name: "By comedian" }));
        fireEvent.change(screen.getByLabelText("Sort"), {
            target: { value: "popularity-desc" },
        });
        openGroup(/Jane Comic/);

        const headings = screen.getAllByRole("heading", { level: 2 });
        expect(headings[0].textContent).toBe("Jane Comic");
        expect(screen.getAllByText(/Popularity 74/).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/1 owned podcast/).length).toBeGreaterThan(
            0,
        );
        expect(screen.queryByText(/2 podcasts attached/)).toBeNull();
        fireEvent.change(screen.getByLabelText("Sort"), {
            target: { value: "popularity-asc" },
        });
        openGroup(/Lower Pop/);
        expect(
            screen.getAllByRole("heading", { level: 2 })[0].textContent,
        ).toBe("Lower Pop");
        expect(screen.getAllByText(/Popularity 0.06/).length).toBeGreaterThan(
            0,
        );
        const rssLink = screen.getAllByRole("link", {
            name: /RSS: https:\/\/pod\.example\/feed\.xml/,
        })[0] as HTMLAnchorElement;
        expect(rssLink.href).toBe("https://pod.example/feed.xml");
        const websiteLink = screen.getAllByRole("link", {
            name: /Website: https:\/\/pod\.example/,
        })[0] as HTMLAnchorElement;
        expect(websiteLink.href).toBe("https://pod.example/");
    });

    it("can ingest an arbitrary RSS feed from the comedian view", async () => {
        vi.mocked(global.fetch).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                ok: true,
                podcast: { title: "Manual Jane Feed" },
                episodeCount: 7,
            }),
        } as never);
        render(<AdminPodcastOwnershipReviewManager candidates={[candidate]} />);

        fireEvent.click(screen.getByRole("button", { name: "By comedian" }));
        openGroup(/Jane Comic/);
        fireEvent.change(screen.getByLabelText("Add arbitrary RSS feed"), {
            target: { value: "https://feeds.example.com/jane.xml" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Ingest RSS" }));

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-ownership-reviews",
                expect.objectContaining({
                    method: "PUT",
                    body: JSON.stringify({
                        comedianId: 42,
                        feedUrl: "https://feeds.example.com/jane.xml",
                        reason: "Manual RSS feed added during podcast ownership review for Jane Comic",
                    }),
                }),
            );
        });
        expect(
            await screen.findByText(/Manual Jane Feed ingested/),
        ).toBeTruthy();
    });

    it("saves a selected podcast owner with a reason", async () => {
        render(<AdminPodcastOwnershipReviewManager candidates={[candidate]} />);

        openGroup(/The Jane Show/);
        fireEvent.change(screen.getByLabelText("Review note"), {
            target: { value: "Verified host credit" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Save The Jane Show" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-ownership-reviews",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        podcastId: 99,
                        ownerComedianId: 42,
                        reason: "Verified host credit",
                    }),
                }),
            );
        });
        expect(mocks.refresh).toHaveBeenCalled();
    });

    it("blocks a podcast when the owner tag is removed", async () => {
        render(<AdminPodcastOwnershipReviewManager candidates={[candidate]} />);

        openGroup(/The Jane Show/);
        fireEvent.click(
            screen.getByRole("button", { name: "Remove Jane Comic as owner" }),
        );
        fireEvent.change(screen.getByLabelText("Review note"), {
            target: { value: "Wrong Jane" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Save The Jane Show" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-ownership-reviews",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        podcastId: 99,
                        ownerComedianId: null,
                        reason: "Wrong Jane",
                    }),
                }),
            );
        });
    });

    it("can search for and add a different owner", async () => {
        vi.mocked(global.fetch)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    data: [{ id: 77, uuid: "uuid-77", name: "Right Owner" }],
                }),
            } as never)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ ok: true }),
            } as never);
        render(<AdminPodcastOwnershipReviewManager candidates={[candidate]} />);

        openGroup(/The Jane Show/);
        fireEvent.change(
            screen.getByLabelText("Add owner", { selector: "input" }),
            {
                target: { value: "Right Owner" },
            },
        );
        fireEvent.click(screen.getByRole("button", { name: "Search" }));
        await screen.findByText("Right Owner");
        fireEvent.click(screen.getByRole("button", { name: "Right Owner" }));
        fireEvent.click(
            screen.getByRole("button", { name: "Save The Jane Show" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenLastCalledWith(
                "/api/admin/podcast-ownership-reviews",
                expect.objectContaining({
                    body: JSON.stringify({
                        podcastId: 99,
                        ownerComedianId: 77,
                        reason: "",
                    }),
                }),
            );
        });
    });
});
