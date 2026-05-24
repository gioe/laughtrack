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
        comedianImageAsset: {
            create: vi.fn(),
            updateMany: vi.fn(),
            findMany: vi.fn(),
        },
    },
}));

vi.mock("@/lib/admin/comedianImagePipeline", async () => {
    const actual = await vi.importActual<
        typeof import("@/lib/admin/comedianImagePipeline")
    >("@/lib/admin/comedianImagePipeline");
    return {
        ...actual,
        downloadComedianImage: vi.fn(),
        generateComedianImageVariants: vi.fn(),
    };
});

import { auth } from "@/auth";
import { db } from "@/lib/db";
import {
    ComedianImageDownloadError,
    downloadComedianImage,
    generateComedianImageVariants,
} from "@/lib/admin/comedianImagePipeline";
import { POST } from "./route";

const mockAuth = vi.mocked(auth);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockFindComedian = vi.mocked(db.comedian.findUnique);
const mockUpdateComedian = vi.mocked(db.comedian.update);
const mockComedianImageAssetCreate = vi.mocked(db.comedianImageAsset.create);
const mockComedianImageAssetUpdateMany = vi.mocked(
    db.comedianImageAsset.updateMany,
);
const mockDownload = vi.mocked(downloadComedianImage);
const mockGenerateVariants = vi.mocked(generateComedianImageVariants);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makeRequest(body: unknown) {
    return new NextRequest(
        "http://localhost/api/admin/comedians/images/preview",
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
    mockFindComedian.mockResolvedValue({ id: 7 } as never);
    mockDownload.mockResolvedValue({
        sourceUrl: "https://example.com/headshot.jpg",
        buffer: Buffer.from([1, 2, 3]),
        mimeType: "image/jpeg",
        width: 2400,
        height: 2400,
    });
    mockGenerateVariants.mockResolvedValue({
        avatarBuffer: Buffer.from("avatar"),
        heroBuffer: Buffer.from("hero"),
    });
});

describe("POST /api/admin/comedians/images/preview", () => {
    it("requires admin access", async () => {
        mockAuth.mockResolvedValue(null as never);
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/h.jpg",
            }),
        );
        expect(res.status).toBe(401);
        expect(mockDownload).not.toHaveBeenCalled();
    });

    it("rejects payloads without a valid imageUrl", async () => {
        const res = await POST(
            makeRequest({ comedianId: 7, imageUrl: "not-a-url" }),
        );
        expect(res.status).toBe(400);
        expect(mockDownload).not.toHaveBeenCalled();
    });

    it("returns 404 when comedian does not exist", async () => {
        mockFindComedian.mockResolvedValue(null);
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/h.jpg",
            }),
        );
        expect(res.status).toBe(404);
        expect(mockDownload).not.toHaveBeenCalled();
    });

    it("forwards pipeline download errors as 400 with the error code", async () => {
        mockDownload.mockRejectedValue(
            new ComedianImageDownloadError("TOO_SMALL", "Image is 200x200"),
        );
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/h.jpg",
            }),
        );
        expect(res.status).toBe(400);
        const body = await res.json();
        expect(body).toEqual({ error: "Image is 200x200", code: "TOO_SMALL" });
    });

    it("returns base64 avatar and hero data URLs without mutating image asset state", async () => {
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/headshot.jpg",
                sourcePageUrl: "https://example.com/press",
            }),
        );
        expect(res.status).toBe(200);
        const body = await res.json();

        expect(body.ok).toBe(true);
        expect(body.comedianId).toBe(7);
        expect(body.source).toEqual({
            imageUrl: "https://example.com/headshot.jpg",
            sourcePageUrl: "https://example.com/press",
            mimeType: "image/jpeg",
            width: 2400,
            height: 2400,
        });
        expect(body.avatarDataUrl).toBe(
            `data:image/jpeg;base64,${Buffer.from("avatar").toString("base64")}`,
        );
        expect(body.heroDataUrl).toBe(
            `data:image/jpeg;base64,${Buffer.from("hero").toString("base64")}`,
        );
        expect(body.warnings).toEqual([]);

        expect(mockUpdateComedian).not.toHaveBeenCalled();
        expect(mockComedianImageAssetCreate).not.toHaveBeenCalled();
        expect(mockComedianImageAssetUpdateMany).not.toHaveBeenCalled();
    });

    it("uses a separate hero image url when one is provided", async () => {
        mockDownload
            .mockResolvedValueOnce({
                sourceUrl: "https://example.com/headshot.jpg",
                buffer: Buffer.from("headshot"),
                mimeType: "image/jpeg",
                width: 2400,
                height: 2400,
            })
            .mockResolvedValueOnce({
                sourceUrl: "https://example.com/hero.jpg",
                buffer: Buffer.from("hero-source"),
                mimeType: "image/jpeg",
                width: 2400,
                height: 1350,
            });
        mockGenerateVariants
            .mockResolvedValueOnce({
                avatarBuffer: Buffer.from("avatar-from-headshot"),
                heroBuffer: Buffer.from("unused-hero-from-headshot"),
            })
            .mockResolvedValueOnce({
                avatarBuffer: Buffer.from("unused-avatar-from-hero"),
                heroBuffer: Buffer.from("hero-from-hero-source"),
            });

        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/headshot.jpg",
                heroImageUrl: "https://example.com/hero.jpg",
            }),
        );
        expect(res.status).toBe(200);
        const body = await res.json();

        expect(mockDownload).toHaveBeenNthCalledWith(
            1,
            "https://example.com/headshot.jpg",
        );
        expect(mockDownload).toHaveBeenNthCalledWith(
            2,
            "https://example.com/hero.jpg",
        );
        expect(body.source.imageUrl).toBe("https://example.com/headshot.jpg");
        expect(body.source.heroImageUrl).toBe("https://example.com/hero.jpg");
        expect(body.avatarDataUrl).toBe(
            `data:image/jpeg;base64,${Buffer.from("avatar-from-headshot").toString("base64")}`,
        );
        expect(body.heroDataUrl).toBe(
            `data:image/jpeg;base64,${Buffer.from("hero-from-hero-source").toString("base64")}`,
        );
        expect(body.warnings).toEqual([]);
    });

    it("surfaces a low-resolution warning when source is below preferred hero size", async () => {
        mockDownload.mockResolvedValue({
            sourceUrl: "https://example.com/small.jpg",
            buffer: Buffer.from([1, 2, 3]),
            mimeType: "image/jpeg",
            width: 1200,
            height: 800,
        });
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/small.jpg",
            }),
        );
        const body = await res.json();
        expect(res.status).toBe(200);
        expect(body.warnings).toHaveLength(1);
        expect(body.warnings[0]).toMatch(/below preferred hero/);
    });
});
