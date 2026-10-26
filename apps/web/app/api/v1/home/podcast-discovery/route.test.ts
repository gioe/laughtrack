import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";
const mocks = vi.hoisted(() => ({ read: vi.fn(), limit: vi.fn() }));
vi.mock("@/lib/data/home/podcastDiscoverySnapshot", () => ({
    readPodcastDiscoverySnapshot: mocks.read,
}));
vi.mock("@/lib/rateLimit", () => ({
    applyPublicReadRateLimit: mocks.limit,
    rateLimitHeaders: () => ({}),
}));
vi.mock("@/lib/metrics", () => ({ withRequestMetrics: (fn: unknown) => fn }));
import { GET } from "./route";
const request = (etag?: string) =>
    new NextRequest("http://localhost/api/v1/home/podcast-discovery", {
        headers: etag ? { "If-None-Match": etag } : {},
    });
beforeEach(() => {
    vi.resetAllMocks();
    mocks.limit.mockResolvedValue({ allowed: true });
    mocks.read.mockResolvedValue({ generatedAt: null, episodes: [] });
});
it("revalidates a public cached response and changes its ETag after invalidation", async () => {
    mocks.read.mockResolvedValueOnce({
        generatedAt: "2026-10-10T12:00:00Z",
        episodes: [{ id: 1 }],
    });
    const first = await GET(request());
    const etag = first.headers.get("etag")!;
    expect(first.headers.get("cache-control")).toBe(
        "public, no-cache, must-revalidate",
    );
    const invalidated = await GET(request(etag));
    expect(invalidated.status).toBe(200);
    expect((await invalidated.json()).data.episodes).toEqual([]);
    const unchanged = await GET(request(invalidated.headers.get("etag")!));
    expect(unchanged.status).toBe(304);
    expect(await unchanged.text()).toBe("");
});
it("does not cache failures or bypass rate limiting", async () => {
    mocks.limit.mockResolvedValueOnce(NextResponse.json({}, { status: 429 }));
    expect((await GET(request())).status).toBe(429);
    expect(mocks.read).not.toHaveBeenCalled();
    mocks.read.mockRejectedValue(new Error("offline"));
    const response = await GET(request());
    expect(response.status).toBe(503);
    expect(response.headers.get("cache-control")).toBe("no-store");
});
