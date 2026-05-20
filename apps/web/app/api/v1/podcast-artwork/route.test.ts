import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const { mockFindFirst } = vi.hoisted(() => ({
    mockFindFirst: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        podcast: {
            findFirst: mockFindFirst,
        },
    },
}));
vi.mock("@/lib/rateLimit", () => ({
    applyPublicReadRateLimit: vi.fn(() =>
        Promise.resolve({
            allowed: true,
            limit: 60,
            remaining: 59,
            resetAt: 0,
        }),
    ),
    rateLimitHeaders: vi.fn(() => ({
        "X-RateLimit-Limit": "60",
        "X-RateLimit-Remaining": "59",
        "X-RateLimit-Reset": "1",
    })),
}));

import { GET } from "./route";
import { applyPublicReadRateLimit } from "@/lib/rateLimit";

const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);

function makeRequest(url: string): NextRequest {
    return new NextRequest(
        `http://localhost/api/v1/podcast-artwork?url=${encodeURIComponent(url)}`,
    );
}

beforeEach(() => {
    vi.clearAllMocks();
    mockFindFirst.mockResolvedValue(null);
    vi.stubGlobal(
        "fetch",
        vi.fn(() =>
            Promise.resolve(
                new Response("image-bytes", {
                    status: 200,
                    headers: { "content-type": "image/jpeg" },
                }),
            ),
        ),
    );
});

describe("GET /api/v1/podcast-artwork", () => {
    it("rejects URLs that are not exact podcast image rows", async () => {
        const res = await GET(makeRequest("https://internal.example/art.jpg"));

        expect(res.status).toBe(400);
        expect(fetch).not.toHaveBeenCalled();
    });

    it("rejects non-HTTPS artwork URLs before querying upstream", async () => {
        const res = await GET(makeRequest("http://cdn.example.com/art.jpg"));

        expect(res.status).toBe(400);
        expect(mockFindFirst).not.toHaveBeenCalled();
        expect(fetch).not.toHaveBeenCalled();
    });

    it("proxies exact DB-owned podcast artwork and preserves image content type", async () => {
        mockFindFirst.mockResolvedValue({ id: 42 });

        const res = await GET(makeRequest("https://cdn.example.com/art.jpg"));

        expect(res.status).toBe(200);
        expect(res.headers.get("content-type")).toBe("image/jpeg");
        expect(res.headers.get("cache-control")).toContain("s-maxage=604800");
        expect(await res.text()).toBe("image-bytes");
        expect(mockFindFirst).toHaveBeenCalledWith({
            where: { imageUrl: "https://cdn.example.com/art.jpg" },
            select: { id: true },
        });
        expect(fetch).toHaveBeenCalledWith(
            "https://cdn.example.com/art.jpg",
            expect.objectContaining({
                headers: expect.objectContaining({
                    Accept: expect.stringContaining("image/"),
                }),
            }),
        );
    });

    it("rejects DB-owned URLs that do not return image content", async () => {
        mockFindFirst.mockResolvedValue({ id: 42 });
        vi.mocked(fetch).mockResolvedValue(
            new Response("html", {
                status: 200,
                headers: { "content-type": "text/html" },
            }),
        );

        const res = await GET(makeRequest("https://cdn.example.com/art.jpg"));

        expect(res.status).toBe(415);
    });

    it("applies the public read rate limit with a podcast-artwork bucket", async () => {
        mockFindFirst.mockResolvedValue({ id: 42 });

        await GET(makeRequest("https://cdn.example.com/art.jpg"));

        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "podcast-artwork",
        );
    });
});
