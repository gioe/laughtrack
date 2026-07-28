import { describe, expect, it, vi } from "vitest";
import {
    listCandidates,
    runPodcastDenyBackfill,
} from "./deny-podcasts-for-denied-comedians";

const candidateRows = [
    {
        comedian_names: ["Blocked Host", "Other Blocked Host"],
        podcast_id: 11,
        title: "First Podcast",
        source: "apple",
        source_podcast_id: "first",
        feed_url: "https://example.com/first.xml",
    },
    {
        comedian_names: ["Blocked Host"],
        podcast_id: 22,
        title: "Second Podcast",
        source: "spotify",
        source_podcast_id: "second",
        feed_url: null,
    },
    {
        comedian_names: ["Shared Feed Host"],
        podcast_id: 33,
        title: "Third Podcast",
        source: "apple",
        source_podcast_id: "third",
        feed_url: "https://example.com/first.xml",
    },
];

const candidates = [
    {
        ...candidateRows[0],
        comedian_names: [
            "Blocked Host",
            "Other Blocked Host",
            "Shared Feed Host",
        ],
    },
    candidateRows[1],
];

describe("deny-podcasts-for-denied-comedians", () => {
    it("returns one candidate per podcast when multiple denied hosts match", async () => {
        const queryRaw = vi.fn().mockResolvedValue(candidateRows);

        const result = await listCandidates({
            $queryRaw: queryRaw,
        } as never);

        expect(result).toEqual(candidates);
        const sql = Array.from(
            queryRaw.mock.calls[0][0] as TemplateStringsArray,
        ).join("?");
        expect(sql).toContain("array_agg(DISTINCT dl.name");
        expect(sql).toContain("GROUP BY");
    });

    it("returns one candidate when podcast rows share a deny-list feed identity", async () => {
        const queryRaw = vi.fn().mockResolvedValue(candidateRows);

        const result = await listCandidates({
            $queryRaw: queryRaw,
        } as never);

        expect(result).toEqual(candidates);
        expect(result).toHaveLength(2);
    });

    it("applies exactly the candidates selected in the transaction", async () => {
        const queryRaw = vi
            .fn()
            .mockResolvedValueOnce(candidateRows)
            .mockResolvedValueOnce([{ podcast_id: 11 }])
            .mockResolvedValueOnce([{ podcast_id: 22 }]);
        const transaction = vi.fn(
            async (callback: (tx: unknown) => Promise<unknown>) =>
                callback({ $queryRaw: queryRaw }),
        );

        const result = await runPodcastDenyBackfill(
            {
                $queryRaw: vi.fn(),
                $transaction: transaction,
            } as never,
            true,
        );

        expect(result.candidateCount).toBe(2);
        expect(result.deniedPodcastCount).toBe(2);
        expect(result.denied).toEqual(candidates);
        expect(queryRaw).toHaveBeenCalledTimes(3);

        const appliedPodcastIds = queryRaw.mock.calls
            .slice(1)
            .map((call) => call[1]);
        expect(appliedPodcastIds).toEqual([11, 22]);
    });

    it("never updates an already-active deny row", async () => {
        const queryRaw = vi
            .fn()
            .mockResolvedValueOnce([candidates[0]])
            .mockResolvedValueOnce([]);
        const transaction = vi.fn(
            async (callback: (tx: unknown) => Promise<unknown>) =>
                callback({ $queryRaw: queryRaw }),
        );

        const result = await runPodcastDenyBackfill(
            {
                $queryRaw: vi.fn(),
                $transaction: transaction,
            } as never,
            true,
        );

        const mutationSql = Array.from(
            queryRaw.mock.calls[1][0] as TemplateStringsArray,
        ).join("?");
        expect(mutationSql).toContain("restored_at IS NOT NULL");
        expect(mutationSql).toContain("restored_at IS NULL");
        expect(mutationSql).toContain("ON CONFLICT DO NOTHING");
        expect(result.deniedPodcastCount).toBe(0);
    });
});
