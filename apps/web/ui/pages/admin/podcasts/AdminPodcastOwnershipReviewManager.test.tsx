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
import AdminPodcastHostshipReviewManager, {
    type AdminPodcastHostshipReviewCandidate,
} from "./AdminPodcastHostshipReviewManager";

const mocks = vi.hoisted(() => ({
    refresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        refresh: mocks.refresh,
    }),
}));

const candidate: AdminPodcastHostshipReviewCandidate = {
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
        denyListEntry: null,
    },
    existingHostships: [],
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

describe("AdminPodcastHostshipReviewManager", () => {
    it("renders candidate context and evidence", () => {
        render(<AdminPodcastHostshipReviewManager candidates={[candidate]} />);

        openGroup(/The Jane Show/);

        expect(screen.getAllByText("Jane Comic").length).toBeGreaterThan(0);
        expect(screen.getAllByText("The Jane Show").length).toBeGreaterThan(0);
        expect(screen.getByText("Host: Jane Comic")).toBeTruthy();
        expect(screen.getAllByText("91%").length).toBeGreaterThan(0);
        expect(screen.getByText(/matched_name/)).toBeTruthy();
    });

    it("does not preselect hosts for non-pending rejected candidates", () => {
        render(
            <AdminPodcastHostshipReviewManager
                candidates={[
                    {
                        ...candidate,
                        candidateStatus: "rejected",
                        existingHostships: [],
                    },
                ]}
            />,
        );

        openGroup(/The Jane Show/);

        expect(screen.getAllByText("No host").length).toBeGreaterThan(0);
        expect(screen.getAllByText(/no host/i).length).toBeGreaterThan(0);
    });

    it("switches to comedian view and sorts by popularity", () => {
        const lowerPopularityCandidate: AdminPodcastHostshipReviewCandidate = {
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
        const hostedJaneCandidate: AdminPodcastHostshipReviewCandidate = {
            ...candidate,
            existingHostships: [
                {
                    id: 201,
                    associationType: "host",
                    source: "manual",
                    reviewStatus: "accepted",
                    confidence: 1,
                    reviewedAt: "2026-05-18T12:00:00.000Z",
                    reviewedBy: "profile-1",
                    comedian: candidate.comedian,
                },
            ],
        };
        const nonHostedJaneCandidate: AdminPodcastHostshipReviewCandidate = {
            ...candidate,
            id: 14,
            podcast: {
                ...candidate.podcast!,
                id: 101,
                slug: "jane-guest-show",
                title: "Jane Guest Show",
            },
            existingHostships: [
                {
                    id: 202,
                    associationType: "host",
                    source: "manual",
                    reviewStatus: "accepted",
                    confidence: 1,
                    reviewedAt: "2026-05-18T12:00:00.000Z",
                    reviewedBy: "profile-1",
                    comedian: {
                        id: 88,
                        uuid: "uuid-88",
                        name: "Other Host",
                        popularity: 2,
                    },
                },
            ],
        };
        render(
            <AdminPodcastHostshipReviewManager
                candidates={[
                    lowerPopularityCandidate,
                    nonHostedJaneCandidate,
                    hostedJaneCandidate,
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
        expect(screen.getAllByText(/1 hosted podcast/).length).toBeGreaterThan(
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

    it("filters the podcast view by podcast name", () => {
        const otherCandidate: AdminPodcastHostshipReviewCandidate = {
            ...candidate,
            id: 13,
            comedian: {
                id: 77,
                uuid: "uuid-77",
                name: "Other Comic",
                popularity: 12,
            },
            podcast: {
                ...candidate.podcast!,
                id: 100,
                slug: "other-show",
                title: "Other Show",
                authorName: "Other Comic",
            },
        };
        render(
            <AdminPodcastHostshipReviewManager
                candidates={[candidate, otherCandidate]}
            />,
        );

        fireEvent.change(screen.getByLabelText("Search podcasts"), {
            target: { value: "jane" },
        });

        expect(
            screen.getByRole("button", { name: /The Jane Show/ }),
        ).toBeTruthy();
        expect(screen.queryByRole("button", { name: /Other Show/ })).toBeNull();
        expect(screen.getAllByText("1-1 of 1 podcasts").length).toBe(2);
    });

    it("filters the comedian view by comedian name", () => {
        const otherCandidate: AdminPodcastHostshipReviewCandidate = {
            ...candidate,
            id: 13,
            comedian: {
                id: 77,
                uuid: "uuid-77",
                name: "Other Comic",
                popularity: 12,
            },
            podcast: {
                ...candidate.podcast!,
                id: 100,
                slug: "other-show",
                title: "Other Show",
                authorName: "Other Comic",
            },
        };
        render(
            <AdminPodcastHostshipReviewManager
                candidates={[candidate, otherCandidate]}
            />,
        );

        fireEvent.click(screen.getByRole("button", { name: "By comedian" }));
        fireEvent.change(screen.getByLabelText("Search comedians"), {
            target: { value: "other" },
        });

        expect(
            screen.getByRole("button", { name: /Other Comic/ }),
        ).toBeTruthy();
        expect(screen.queryByRole("button", { name: /Jane Comic/ })).toBeNull();
        expect(screen.getAllByText("1-1 of 1 comedians").length).toBe(2);
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
        render(<AdminPodcastHostshipReviewManager candidates={[candidate]} />);

        fireEvent.click(screen.getByRole("button", { name: "By comedian" }));
        openGroup(/Jane Comic/);
        fireEvent.change(screen.getByLabelText("Add arbitrary RSS feed"), {
            target: { value: "https://feeds.example.com/jane.xml" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Ingest RSS" }));

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-hostship-reviews",
                expect.objectContaining({
                    method: "PUT",
                    body: JSON.stringify({
                        comedianId: 42,
                        feedUrl: "https://feeds.example.com/jane.xml",
                        reason: "Manual RSS feed added during podcast hostship review for Jane Comic",
                    }),
                }),
            );
        });
        expect(
            await screen.findByText(/Manual Jane Feed ingested/),
        ).toBeTruthy();
    });

    it("saves a selected podcast host with a reason", async () => {
        render(<AdminPodcastHostshipReviewManager candidates={[candidate]} />);

        openGroup(/The Jane Show/);
        fireEvent.change(screen.getByLabelText("Review note"), {
            target: { value: "Verified host credit" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Save The Jane Show" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-hostship-reviews",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        podcastId: 99,
                        hostComedianIds: [42],
                        cohostComedianIds: [],
                        denyListed: false,
                        reason: "Verified host credit",
                    }),
                }),
            );
        });
        expect(mocks.refresh).toHaveBeenCalled();
    });

    it("saves selected host and co-host roles", async () => {
        render(
            <AdminPodcastHostshipReviewManager
                candidates={[
                    candidate,
                    {
                        ...candidate,
                        id: 13,
                        associationType: "cohost",
                        comedian: {
                            id: 77,
                            uuid: "uuid-77",
                            name: "Co Host",
                            popularity: 31,
                        },
                    },
                ]}
            />,
        );

        openGroup(/The Jane Show/);
        fireEvent.click(screen.getByRole("button", { name: "Co-host: Co Host" }));
        fireEvent.click(
            screen.getByRole("button", { name: "Save The Jane Show" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-hostship-reviews",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        podcastId: 99,
                        hostComedianIds: [42],
                        cohostComedianIds: [77],
                        denyListed: false,
                        reason: "",
                    }),
                }),
            );
        });
    });

    it("blocks a podcast when the host tag is removed", async () => {
        render(<AdminPodcastHostshipReviewManager candidates={[candidate]} />);

        openGroup(/The Jane Show/);
        fireEvent.click(
            screen.getByRole("button", { name: "Remove Jane Comic as host" }),
        );
        fireEvent.change(screen.getByLabelText("Review note"), {
            target: { value: "Wrong Jane" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Save The Jane Show" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-hostship-reviews",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        podcastId: 99,
                        hostComedianIds: [],
                        cohostComedianIds: [],
                        denyListed: false,
                        reason: "Wrong Jane",
                    }),
                }),
            );
        });
    });

    it("deny-lists a podcast from the podcast row action", async () => {
        render(<AdminPodcastHostshipReviewManager candidates={[candidate]} />);

        openGroup(/The Jane Show/);
        fireEvent.change(screen.getByLabelText("Review note"), {
            target: { value: "Not a host-hosted feed" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Block The Jane Show" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-hostship-reviews",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        podcastId: 99,
                        hostComedianIds: [],
                        cohostComedianIds: [],
                        denyListed: true,
                        reason: "Not a host-hosted feed",
                    }),
                }),
            );
        });
        expect(
            await screen.findByText("The Jane Show deny-listed."),
        ).toBeTruthy();
        expect(screen.getAllByText("No host").length).toBeGreaterThan(0);
    });

    it("shows and restores durable deny-list state", async () => {
        render(
            <AdminPodcastHostshipReviewManager
                candidates={[
                    {
                        ...candidate,
                        podcast: {
                            ...candidate.podcast!,
                            denyListEntry: {
                                id: 5,
                                reason: "Not comedy",
                                deniedAt: "2026-05-18T12:00:00.000Z",
                                deniedBy: "profile-1",
                            },
                        },
                    },
                ]}
            />,
        );

        openGroup(/The Jane Show/);
        expect(screen.getAllByText("Deny-listed").length).toBeGreaterThan(0);
        expect(screen.getByText(/Not comedy/)).toBeTruthy();
        fireEvent.click(
            screen.getByRole("button", { name: "Restore The Jane Show" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-hostship-reviews",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        podcastId: 99,
                        hostComedianIds: [],
                        cohostComedianIds: [],
                        denyListed: false,
                        reason: "",
                    }),
                }),
            );
        });
    });

    it("can search for and add a different host", async () => {
        vi.mocked(global.fetch)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    data: [{ id: 77, uuid: "uuid-77", name: "Right Host" }],
                }),
            } as never)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ ok: true }),
            } as never);
        render(<AdminPodcastHostshipReviewManager candidates={[candidate]} />);

        openGroup(/The Jane Show/);
        fireEvent.change(
            screen.getByLabelText("Add host", { selector: "input" }),
            {
                target: { value: "Right Host" },
            },
        );
        fireEvent.click(screen.getByRole("button", { name: "Search" }));
        await screen.findByText("Right Host");
        fireEvent.click(screen.getByRole("button", { name: "Right Host" }));
        fireEvent.click(
            screen.getByRole("button", { name: "Save The Jane Show" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenLastCalledWith(
                "/api/admin/podcast-hostship-reviews",
                expect.objectContaining({
                    body: JSON.stringify({
                        podcastId: 99,
                        hostComedianIds: [77],
                        cohostComedianIds: [],
                        denyListed: false,
                        reason: "",
                    }),
                }),
            );
        });
    });
});
