import { describe, expect, it, vi } from "vitest";
import { denyPodcastsHostedByComedianName } from "./podcastDenyList";

describe("denyPodcastsHostedByComedianName", () => {
    it("upserts active podcast deny-list rows for accepted host/cohost podcasts", async () => {
        const queryRaw = vi.fn().mockResolvedValue([
            {
                podcast_id: 5441,
                title: "The Jimmy Dore Show",
                source: "podcast_index",
                source_podcast_id: "1073736",
                feed_url: "https://thejimmydoreshow.libsyn.com/rss",
            },
        ]);
        const tx = { $queryRaw: queryRaw };

        const result = await denyPodcastsHostedByComedianName(tx, {
            comedianName: " Jimmy Dore ",
            reason: "Host comedian was added to comedian deny list: Jimmy Dore",
            deniedBy: "profile-1",
        });

        expect(queryRaw).toHaveBeenCalledTimes(1);
        const query = queryRaw.mock.calls[0][0];
        const sqlText = Array.from(query as TemplateStringsArray).join("?");
        expect(sqlText).toContain("FROM comedian_podcasts cp");
        expect(sqlText).toContain("cp.review_status = 'accepted'");
        expect(sqlText).toContain("cp.association_type IN ('host', 'cohost')");
        expect(sqlText).toContain("INSERT INTO podcast_deny_list");
        expect(sqlText).toContain("ON CONFLICT (podcast_id) DO UPDATE");
        expect(result).toEqual([
            {
                podcastId: 5441,
                title: "The Jimmy Dore Show",
                source: "podcast_index",
                sourcePodcastId: "1073736",
                feedUrl: "https://thejimmydoreshow.libsyn.com/rss",
            },
        ]);
    });

    it("does not query for blank comedian names", async () => {
        const tx = { $queryRaw: vi.fn() };

        await expect(
            denyPodcastsHostedByComedianName(tx, {
                comedianName: " ",
                reason: "ignored",
                deniedBy: "profile-1",
            }),
        ).resolves.toEqual([]);
        expect(tx.$queryRaw).not.toHaveBeenCalled();
    });
});
