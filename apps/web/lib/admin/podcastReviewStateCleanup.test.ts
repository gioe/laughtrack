import { beforeEach, describe, expect, it, vi } from "vitest";

import {
    applyPodcastReviewStateCleanup,
    listPodcastReviewStateCleanupCandidates,
} from "./podcastReviewStateCleanup";

describe("podcast review state cleanup", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("targets reviewed podcasts that have no pending review, no accepted visible hostship, and no active deny-list row", async () => {
        const db = {
            $queryRaw: vi.fn().mockResolvedValue([]),
        };

        await listPodcastReviewStateCleanupCandidates(db);

        const sql = Array.from(db.$queryRaw.mock.calls[0][0]).join(" ");
        expect(sql).toContain("pcr.candidate_status <> 'pending'");
        expect(sql).toContain("pending.candidate_status = 'pending'");
        expect(sql).toContain("cp.review_status = 'accepted'");
        expect(sql).toContain("comedian.visible = TRUE");
        expect(sql).toContain("pdl.restored_at IS NULL");
    });

    it("bulk deny-lists cleanup candidates and converts ignored review rows to rejected", async () => {
        const now = new Date("2026-06-12T12:00:00Z");
        const db = {
            $executeRaw: vi
                .fn()
                .mockResolvedValueOnce(9)
                .mockResolvedValueOnce(3),
        };

        const result = await applyPodcastReviewStateCleanup(db, {
            deniedBy: "script:test",
            now,
        });

        const denySql = Array.from(db.$executeRaw.mock.calls[0][0]).join(" ");
        expect(denySql).toContain("INSERT INTO podcast_deny_list");
        expect(denySql).toContain("ON CONFLICT (podcast_id) DO UPDATE");
        expect(denySql).toContain("pcr.candidate_status <> 'pending'");
        expect(denySql).toContain("comedian.visible = TRUE");
        const normalizeSql = Array.from(db.$executeRaw.mock.calls[1][0]).join(
            " ",
        );
        expect(normalizeSql).toContain("UPDATE podcast_candidate_reviews");
        expect(normalizeSql).toContain("candidate_status = 'ignored'");
        expect(result).toEqual({
            deniedPodcastCount: 9,
            normalizedIgnoredReviewCount: 3,
        });
    });
});
