import { describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/metrics", () => ({
    withRequestMetrics: <T>(handler: T) => handler,
}));

import { GET } from "./route";

function makeGetRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL("http://localhost/api/webhooks/youtube");
    for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, value);
    }

    return new NextRequest(url.toString());
}

describe("GET /api/webhooks/youtube", () => {
    it("echoes the WebSub challenge when required parameters are present", async () => {
        const res = await GET(
            makeGetRequest({
                "hub.mode": "subscribe",
                "hub.topic":
                    "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC-live-channel",
                "hub.challenge": "challenge-token",
            }),
        );

        expect(res.status).toBe(200);
        expect(res.headers.get("content-type")).toContain("text/plain");
        expect(await res.text()).toBe("challenge-token");
    });

    it("rejects challenge requests missing the challenge parameter", async () => {
        const res = await GET(
            makeGetRequest({
                "hub.mode": "subscribe",
                "hub.topic":
                    "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC-live-channel",
            }),
        );

        expect(res.status).toBe(400);
        expect(await res.json()).toEqual({ error: "missing_challenge" });
    });
});
