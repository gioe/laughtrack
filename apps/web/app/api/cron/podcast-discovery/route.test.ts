import { afterEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
const refresh = vi.hoisted(() => vi.fn());
vi.mock("@/lib/data/home/podcastDiscoverySnapshot", () => ({
    refreshPodcastDiscoverySnapshot: refresh,
}));
vi.mock("@/lib/metrics", () => ({ withRequestMetrics: (fn: unknown) => fn }));
import { GET, POST } from "./route";
afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetAllMocks();
});
const request = (token?: string) =>
    new NextRequest("http://localhost/api/cron/podcast-discovery", {
        headers: token ? { authorization: `Bearer ${token}` } : {},
    });
it("rejects absent, incorrect, and unconfigured credentials before any work", async () => {
    vi.stubEnv("CRON_SECRET", "secret");
    expect((await GET(request())).status).toBe(401);
    expect((await POST(request("wrong!"))).status).toBe(401);
    vi.stubEnv("CRON_SECRET", "");
    expect((await GET(request("secret"))).status).toBe(401);
    expect(refresh).not.toHaveBeenCalled();
});
it("runs authorized refreshes and reports failures", async () => {
    vi.stubEnv("CRON_SECRET", "secret");
    refresh.mockResolvedValueOnce({ published: true, episodeCount: 5 });
    expect((await POST(request("secret"))).status).toBe(200);
    refresh.mockRejectedValueOnce(new Error("offline"));
    expect((await GET(request("secret"))).status).toBe(500);
});
