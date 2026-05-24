import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        comedian: {
            findUnique: vi.fn(),
            update: vi.fn(),
        },
        userProfile: {
            findFirst: vi.fn(),
        },
    },
}));

vi.mock("@/lib/admin/comedianImageDiscovery", () => ({
    discoverComedianImageCandidates: vi.fn(),
}));

import { auth } from "@/auth";
import { db } from "@/lib/db";
import { discoverComedianImageCandidates } from "@/lib/admin/comedianImageDiscovery";
import { POST } from "./route";

const mockAuth = vi.mocked(auth);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockFindComedian = vi.mocked(db.comedian.findUnique);
const mockUpdateComedian = vi.mocked(db.comedian.update);
const mockDiscover = vi.mocked(discoverComedianImageCandidates);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makeRequest(body: unknown) {
    return new NextRequest(
        "http://localhost/api/admin/comedians/images/discover",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        },
    );
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue(adminSession as never);
    mockFindUserProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
    mockFindComedian.mockResolvedValue({
        id: 7,
        name: "Alex Example",
        website: "https://comic.example/",
        websiteScrapingUrl: "https://comic.example/press",
    } as never);
    mockDiscover.mockResolvedValue({
        seedPages: ["https://comic.example/", "https://comic.example/press"],
        crawledPages: ["https://comic.example/", "https://comic.example/press"],
        candidates: [
            {
                imageUrl: "https://comic.example/headshot.jpg",
                sourcePage: "https://comic.example/press",
                width: 1200,
                height: 1600,
                mimeType: "image/jpeg",
                score: 145,
                reasons: ["headshot signal", "large portrait"],
            },
        ],
    });
});

describe("POST /api/admin/comedians/images/discover", () => {
    it("requires admin access", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await POST(makeRequest({ comedianId: 7 }));

        expect(res.status).toBe(401);
        expect(mockDiscover).not.toHaveBeenCalled();
    });

    it("returns ranked candidate evidence without mutating image assets", async () => {
        const res = await POST(makeRequest({ comedianId: 7 }));
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockFindComedian).toHaveBeenCalledWith({
            where: { id: 7 },
            select: {
                id: true,
                name: true,
                website: true,
                websiteScrapingUrl: true,
            },
        });
        expect(mockDiscover).toHaveBeenCalledWith({
            comedianName: "Alex Example",
            website: "https://comic.example/",
            websiteScrapingUrl: "https://comic.example/press",
        });
        expect(body).toEqual({
            ok: true,
            comedianId: 7,
            seedPages: [
                "https://comic.example/",
                "https://comic.example/press",
            ],
            crawledPages: [
                "https://comic.example/",
                "https://comic.example/press",
            ],
            candidates: [
                {
                    imageUrl: "https://comic.example/headshot.jpg",
                    sourcePage: "https://comic.example/press",
                    width: 1200,
                    height: 1600,
                    mimeType: "image/jpeg",
                    score: 145,
                    reasons: ["headshot signal", "large portrait"],
                },
            ],
        });
        expect(mockUpdateComedian).not.toHaveBeenCalled();
    });
});
