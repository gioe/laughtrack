import { beforeEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({
    query: vi.fn(),
    execute: vi.fn(),
    discover: vi.fn(),
}));
vi.mock("@/lib/db", () => ({
    db: { $queryRaw: mocks.query, $executeRaw: mocks.execute },
}));
vi.mock("./getPodcastEpisodeDiscovery", () => ({
    getPodcastEpisodeDiscovery: mocks.discover,
}));
import {
    readPodcastDiscoverySnapshot,
    refreshPodcastDiscoverySnapshot,
} from "./podcastDiscoverySnapshot";

beforeEach(() => vi.resetAllMocks());
describe("durable podcast snapshot", () => {
    it("never computes on a missing or invalidated cache read", async () => {
        for (const rows of [[], [{ payload: null }]]) {
            mocks.query.mockResolvedValueOnce(rows);
            expect(await readPodcastDiscoverySnapshot()).toEqual({
                generatedAt: null,
                episodes: [],
            });
        }
        expect(mocks.discover).not.toHaveBeenCalled();
        expect(mocks.execute).not.toHaveBeenCalled();
        expect(mocks.query.mock.calls[0][0].text).toContain(
            "INTERVAL '24 hours'",
        );
    });
    it("reads the stored selection without personalization or recomputation", async () => {
        const payload = {
            generatedAt: "2026-10-10T12:00:00Z",
            episodes: [{ id: 5 }],
        };
        mocks.query.mockResolvedValue([{ payload }]);
        expect(await readPodcastDiscoverySnapshot()).toEqual(payload);
        expect(mocks.discover).not.toHaveBeenCalled();
    });
    it("retains the last good snapshot when generation fails", async () => {
        mocks.query.mockResolvedValue([{ revision: 7 }]);
        mocks.discover.mockRejectedValue(new Error("database timeout"));
        await expect(refreshPodcastDiscoverySnapshot()).rejects.toThrow(
            "database timeout",
        );
        expect(mocks.execute).not.toHaveBeenCalled();
    });
    it("publishes only public recommendations and fences concurrent invalidation", async () => {
        mocks.query.mockResolvedValue([{ revision: 7 }]);
        mocks.discover.mockResolvedValue([]);
        mocks.execute.mockResolvedValue(0);
        expect(await refreshPodcastDiscoverySnapshot()).toEqual({
            published: false,
            episodeCount: 0,
        });
        expect(mocks.discover).toHaveBeenCalledWith(null, 5);
        const sql = mocks.execute.mock.calls[0][0];
        expect(sql.text).toContain("revision = revision + 1");
        expect(sql.values[1]).toBe(7);
    });
});
