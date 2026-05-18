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

        expect(screen.getByText("Jane Comic")).toBeTruthy();
        expect(screen.getByText("The Jane Show")).toBeTruthy();
        expect(screen.getByText("91%")).toBeTruthy();
        expect(screen.getByText(/matched_name/)).toBeTruthy();
    });

    it("accepts a candidate with a reason", async () => {
        render(<AdminPodcastOwnershipReviewManager candidates={[candidate]} />);

        fireEvent.change(screen.getByLabelText("Review note for Jane Comic"), {
            target: { value: "Verified host credit" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Accept Jane Comic" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-ownership-reviews",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        candidateId: 12,
                        action: "accept",
                        reason: "Verified host credit",
                    }),
                }),
            );
        });
        expect(mocks.refresh).toHaveBeenCalled();
    });

    it("rejects a candidate", async () => {
        render(<AdminPodcastOwnershipReviewManager candidates={[candidate]} />);

        fireEvent.change(screen.getByLabelText("Review note for Jane Comic"), {
            target: { value: "Wrong Jane" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Reject Jane Comic" }),
        );

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                "/api/admin/podcast-ownership-reviews",
                expect.objectContaining({
                    method: "POST",
                    body: JSON.stringify({
                        candidateId: 12,
                        action: "reject",
                        reason: "Wrong Jane",
                    }),
                }),
            );
        });
    });
});
