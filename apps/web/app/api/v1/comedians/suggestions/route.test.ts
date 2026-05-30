import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/data/comedian/suggestions/getOnboardingComedianSuggestions", () => ({
    getOnboardingComedianSuggestions: vi.fn(),
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
    rateLimitHeaders: vi.fn(),
}));

import { GET } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { getOnboardingComedianSuggestions } from "@/lib/data/comedian/suggestions/getOnboardingComedianSuggestions";
import { rateLimitHeaders } from "@/lib/rateLimit";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockGetSuggestions = vi.mocked(getOnboardingComedianSuggestions);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/comedians/suggestions");
}

const sampleComedian = {
    id: 1,
    uuid: "comedian-uuid",
    name: "Taylor Tomlinson",
    imageUrl: "https://cdn.example.com/taylor.jpg",
    hasImage: true,
    isAlias: false,
    isFavorite: false,
    showCount: 4,
    socialData: {
        id: 1,
        instagramAccount: "taylortomlinson",
        instagramFollowers: 1_000_000,
        tiktokAccount: null,
        tiktokFollowers: null,
        youtubeAccount: null,
        youtubeFollowers: null,
        website: null,
        popularity: 0.95,
        linktree: null,
    },
} as never;

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
    mockResolveAuth.mockResolvedValue(null);
    mockGetSuggestions.mockResolvedValue([sampleComedian]);
});

describe("GET /api/v1/comedians/suggestions", () => {
    it("returns the camelCase comedian wire shape for anonymous callers", async () => {
        const res = await GET(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.data[0].imageUrl).toBe(
            "https://cdn.example.com/taylor.jpg",
        );
        expect(body.data[0].socialData.popularity).toBe(0.95);
        // Anonymous → no profileId passed, so favorites are not requested.
        expect(mockGetSuggestions).toHaveBeenCalledWith(undefined);
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });

    it("forwards the profileId when the caller is authenticated", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-99",
            userId: "user-99",
        });

        const res = await GET(makeRequest());

        expect(res.status).toBe(200);
        expect(mockGetSuggestions).toHaveBeenCalledWith("profile-99");
    });

    it("treats PROFILE_MISSING as anonymous", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING" as never);

        const res = await GET(makeRequest());

        expect(res.status).toBe(200);
        expect(mockGetSuggestions).toHaveBeenCalledWith(undefined);
    });

    it("returns 500 with rate-limit headers when the data layer rejects", async () => {
        mockGetSuggestions.mockRejectedValue(new Error("DB unavailable"));

        const res = await GET(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch comedian suggestions" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
