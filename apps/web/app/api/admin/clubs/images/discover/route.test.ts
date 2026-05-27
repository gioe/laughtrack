import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        club: {
            findUnique: vi.fn(),
            update: vi.fn(),
        },
        userProfile: {
            findFirst: vi.fn(),
        },
    },
}));

vi.mock("@/lib/admin/clubImageDiscovery", () => ({
    discoverClubImageCandidates: vi.fn(),
}));

import { auth } from "@/auth";
import { db } from "@/lib/db";
import { discoverClubImageCandidates } from "@/lib/admin/clubImageDiscovery";
import { POST } from "./route";

const mockAuth = vi.mocked(auth);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockFindClub = vi.mocked(db.club.findUnique);
const mockUpdateClub = vi.mocked(db.club.update);
const mockDiscover = vi.mocked(discoverClubImageCandidates);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makeRequest(body: unknown) {
    return new NextRequest("http://localhost/api/admin/clubs/images/discover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue(adminSession as never);
    mockFindUserProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
    mockFindClub.mockResolvedValue({
        id: 12,
        name: "Laffs Comedy",
        website: "https://club.example/",
    } as never);
    mockDiscover.mockResolvedValue({
        seedPages: ["https://club.example/"],
        crawledPages: ["https://club.example/"],
        candidates: [
            {
                imageUrl: "https://club.example/assets/logo.png",
                sourcePage: "https://club.example/",
                width: 600,
                height: 240,
                mimeType: "image/png",
                score: 160,
                reasons: ["logo / wordmark signal", "landscape orientation"],
            },
        ],
    });
});

describe("POST /api/admin/clubs/images/discover", () => {
    it("requires admin access", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await POST(makeRequest({ clubId: 12 }));

        expect(res.status).toBe(401);
        expect(mockDiscover).not.toHaveBeenCalled();
    });

    it("returns 404 when the club is not found", async () => {
        mockFindClub.mockResolvedValue(null as never);

        const res = await POST(makeRequest({ clubId: 999 }));

        expect(res.status).toBe(404);
        expect(mockDiscover).not.toHaveBeenCalled();
    });

    it("returns ranked candidate evidence without mutating image assets", async () => {
        const res = await POST(makeRequest({ clubId: 12 }));
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockFindClub).toHaveBeenCalledWith({
            where: { id: 12 },
            select: {
                id: true,
                name: true,
                website: true,
            },
        });
        expect(mockDiscover).toHaveBeenCalledWith({
            clubName: "Laffs Comedy",
            website: "https://club.example/",
            websiteScrapingUrl: null,
        });
        expect(body).toEqual({
            ok: true,
            clubId: 12,
            seedPages: ["https://club.example/"],
            crawledPages: ["https://club.example/"],
            candidates: [
                {
                    imageUrl: "https://club.example/assets/logo.png",
                    sourcePage: "https://club.example/",
                    width: 600,
                    height: 240,
                    mimeType: "image/png",
                    score: 160,
                    reasons: [
                        "logo / wordmark signal",
                        "landscape orientation",
                    ],
                },
            ],
        });
        expect(mockUpdateClub).not.toHaveBeenCalled();
    });
});
