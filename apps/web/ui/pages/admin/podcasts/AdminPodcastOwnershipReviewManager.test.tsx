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
    comedian: { id: 42, uuid: "uuid-42", name: "Jane Comic" },
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

describe("AdminPodcastOwnershipReviewManager", () => {
    it("renders candidate context and evidence", () => {
        render(<AdminPodcastOwnershipReviewManager candidates={[candidate]} />);

        expect(screen.getAllByText("Jane Comic").length).toBeGreaterThan(0);
        expect(screen.getByText("The Jane Show")).toBeTruthy();
        expect(screen.getByText("Owner: Jane Comic")).toBeTruthy();
        expect(screen.getAllByText("91%").length).toBeGreaterThan(0);
        expect(screen.getByText(/matched_name/)).toBeTruthy();
    });

    it("saves a selected podcast owner with a reason", async () => {
        render(<AdminPodcastOwnershipReviewManager candidates={[candidate]} />);

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
