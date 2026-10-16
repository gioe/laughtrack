import { beforeEach, expect, it, vi } from "vitest";
import { Prisma } from "@prisma/client";
vi.mock("@/lib/db", () => ({ db: { $queryRaw: vi.fn() } }));
import { db } from "@/lib/db";
import { resolvePodcastIntake, podcastEpisodesAllowed } from "./podcastIntake";
beforeEach(() => vi.clearAllMocks());
it.each([undefined, "blocked", "ambiguous"])(
    "holds manual imports on policy %s",
    async (disposition) => {
        const query = vi
            .fn()
            .mockResolvedValueOnce([])
            .mockResolvedValueOnce(disposition ? [{ disposition }] : []);
        await expect(
            resolvePodcastIntake(
                { $queryRaw: query },
                { source: "manual_rss", source_podcast_id: "1" },
            ),
        ).rejects.toThrow("blocked or has an unresolved identity");
        expect((query.mock.calls[0][0] as Prisma.Sql).text).toBe(
            "SELECT curation_lock_intake()",
        );
        expect(query).toHaveBeenCalledTimes(2);
    },
);
it("reuses a verified identity only after locking and checking policy", async () => {
    const query = vi
        .fn()
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce([{ disposition: "approved", podcast_id: 42 }])
        .mockResolvedValueOnce([]);
    expect(
        await resolvePodcastIntake(
            { $queryRaw: query },
            { feed_url: "https://example.com/feed" },
        ),
    ).toBe(42);
    expect((query.mock.calls[2][0] as Prisma.Sql).text).toContain(
        "curation_observe_podcast",
    );
});
it.each([{ rows: [] }, { rows: [{ allowed: false }] }, { rows: [{ allowed: true }] }])(
    "uses explicit episode approval %j",
    async ({ rows }) => {
        vi.mocked(db.$queryRaw).mockResolvedValueOnce(rows);
        expect(await podcastEpisodesAllowed(42)).toBe(
            rows[0]?.allowed === true,
        );
    },
);
it("propagates unavailable episode policy", async () => {
    vi.mocked(db.$queryRaw).mockRejectedValueOnce(new Error("unavailable"));
    await expect(podcastEpisodesAllowed(42)).rejects.toThrow("unavailable");
});
