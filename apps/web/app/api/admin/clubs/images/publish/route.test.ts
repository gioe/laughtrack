import { auth } from "@/auth";
import {
    deleteFromBunnyStorage,
    uploadToBunnyStorage,
} from "@/lib/admin/bunnyStorage";
import {
    ComedianImageDownloadError,
    downloadComedianImage,
    generateClubImageVariants,
} from "@/lib/admin/comedianImagePipeline";
import { db } from "@/lib/db";
import { revalidateTag } from "next/cache";
import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";

vi.hoisted(() => {
    process.env.BUNNYCDN_CDN_HOST = "cdn.example.com";
});

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("next/cache", () => ({
    revalidateTag: vi.fn(),
}));

vi.mock("@/lib/db", () => {
    const txClient = {
        clubImageAsset: {
            findMany: vi.fn(),
            updateMany: vi.fn(),
            create: vi.fn(),
        },
        club: {
            update: vi.fn(),
        },
        adminActionAudit: {
            create: vi.fn(),
        },
    };
    return {
        db: {
            club: {
                findUnique: vi.fn(),
            },
            userProfile: {
                findFirst: vi.fn(),
            },
            $transaction: vi.fn(),
            __txClient: txClient,
        },
    };
});

vi.mock("@/lib/admin/comedianImagePipeline", () => {
    class ComedianImageDownloadError extends Error {
        code: string;
        constructor(code: string, message: string) {
            super(message);
            this.code = code;
        }
    }
    return {
        ComedianImageDownloadError,
        downloadComedianImage: vi.fn(),
        generateClubImageVariants: vi.fn(),
        getMimeExtension: vi.fn(() => "jpg"),
        validateClubImageAspectRatios: vi.fn(),
    };
});

vi.mock("@/lib/admin/bunnyStorage", () => ({
    uploadToBunnyStorage: vi.fn(),
    deleteFromBunnyStorage: vi.fn(),
}));

const mockAuth = vi.mocked(auth);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockFindClub = vi.mocked(db.club.findUnique);
const mockTransaction = vi.mocked(db.$transaction);
const mockRevalidateTag = vi.mocked(revalidateTag);
const mockDownload = vi.mocked(downloadComedianImage);
const mockGenerateVariants = vi.mocked(generateClubImageVariants);
const mockUpload = vi.mocked(uploadToBunnyStorage);
const mockDelete = vi.mocked(deleteFromBunnyStorage);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const txClient: any = (db as any).__txClient;
const mockTxFindMany = vi.mocked(txClient.clubImageAsset.findMany);
const mockTxUpdateMany = vi.mocked(txClient.clubImageAsset.updateMany);
const mockTxCreate = vi.mocked(txClient.clubImageAsset.create);
const mockTxUpdateClub = vi.mocked(txClient.club.update);
const mockTxAuditCreate = vi.mocked(txClient.adminActionAudit.create);

function makeRequest(body: unknown) {
    return new NextRequest("http://localhost/api/admin/clubs/images/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue({
        profile: { id: "profile-1", userid: "user-1", role: "admin" },
    } as never);
    mockFindUserProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
    mockFindClub.mockResolvedValue({
        id: 12,
        name: "Comedy Cellar",
        hasImage: false,
    } as never);
    mockDownload
        .mockResolvedValueOnce({
            sourceUrl: "https://example.com/icon.jpg",
            buffer: Buffer.from("icon-original"),
            mimeType: "image/jpeg",
            width: 1200,
            height: 1200,
        })
        .mockResolvedValueOnce({
            sourceUrl: "https://example.com/hero.jpg",
            buffer: Buffer.from("hero-original"),
            mimeType: "image/jpeg",
            width: 2000,
            height: 1125,
        });
    mockGenerateVariants.mockResolvedValue({
        iconBuffer: Buffer.from("icon-variant"),
        heroBuffer: Buffer.from("hero-variant"),
    });
    mockUpload.mockResolvedValue();
    mockDelete.mockResolvedValue();
    mockTxFindMany.mockResolvedValue([
        {
            id: 44,
            sourceImageUrl: "https://old.example.com/icon.jpg",
            originalPath: "club-images/12/old/original.jpg",
            iconPath: "clubs/Comedy%20Cellar.png",
            heroPath: "clubs/Comedy%20Cellar-hero.jpg",
            mimeType: "image/jpeg",
            width: 1000,
            height: 1000,
        },
    ]);
    mockTxUpdateMany.mockResolvedValue({ count: 1 });
    mockTxCreate.mockImplementation(async (args: { data: unknown }) => ({
        id: 45,
        ...(args.data as Record<string, unknown>),
    }));
    mockTxUpdateClub.mockResolvedValue({
        id: 12,
        name: "Comedy Cellar",
        city: "New York",
        state: "NY",
        website: "https://example.com",
        hasImage: true,
        visible: true,
        status: "active",
        clubType: "club",
        closedAt: null,
        totalShows: 10,
        chain: null,
        scrapingSources: [],
        shows: [],
        imageAssets: [{ heroPath: "clubs/Comedy%20Cellar-hero.jpg" }],
        _count: { shows: 10 },
    });
    mockTxAuditCreate.mockResolvedValue({} as never);
    mockTransaction.mockImplementation(
        async (callback: (tx: typeof txClient) => unknown) =>
            callback(txClient),
    );
});

describe("POST /api/admin/clubs/images/publish", () => {
    it("records a versioned active asset while keeping legacy club image paths", async () => {
        const res = await POST(
            makeRequest({
                clubId: 12,
                iconImageUrl: "https://example.com/icon.jpg",
                heroImageUrl: "https://example.com/hero.jpg",
            }),
        );

        expect(res.status).toBe(200);
        expect(mockUpload).toHaveBeenCalledTimes(3);
        const [originalUpload, iconUpload, heroUpload] =
            mockUpload.mock.calls.map((call) => call[0]);
        expect(originalUpload.path).toMatch(
            /^club-images\/12\/[0-9a-f-]{36}\/original\.jpg$/,
        );
        expect(Buffer.from(originalUpload.body).toString()).toBe(
            "icon-original",
        );
        expect(iconUpload.path).toBe("clubs/Comedy%20Cellar.png");
        expect(heroUpload.path).toBe("clubs/Comedy%20Cellar-hero.jpg");

        expect(mockTxUpdateMany).toHaveBeenCalledWith({
            where: { clubId: 12, isActive: true },
            data: { isActive: false },
        });
        expect(mockTxCreate).toHaveBeenCalledTimes(1);
        const createArgs = mockTxCreate.mock.calls[0][0] as {
            data: Record<string, unknown>;
        };
        expect(createArgs.data.clubId).toBe(12);
        expect(createArgs.data.sourceImageUrl).toBe(
            "https://example.com/icon.jpg",
        );
        expect(createArgs.data.iconPath).toBe("clubs/Comedy%20Cellar.png");
        expect(createArgs.data.heroPath).toBe("clubs/Comedy%20Cellar-hero.jpg");
        expect(createArgs.data.isActive).toBe(true);
        const metadata = createArgs.data.metadata as Record<string, unknown>;
        expect(metadata.heroSourceImageUrl).toBe(
            "https://example.com/hero.jpg",
        );

        expect(mockTxUpdateClub).toHaveBeenCalledWith({
            where: { id: 12 },
            data: { hasImage: true },
            select: expect.any(Object),
        });
        const auditArgs = mockTxAuditCreate.mock.calls[0][0] as {
            data: Record<string, unknown>;
        };
        expect(auditArgs.data.action).toBe("club_image.publish");
        expect(auditArgs.data.entityType).toBe("club");
        expect(auditArgs.data.entityId).toBe("12");
        expect(mockRevalidateTag).toHaveBeenCalledWith("club-detail-data");
        expect(mockRevalidateTag).toHaveBeenCalledWith("Comedy Cellar");
    });

    it("rejects an SVG candidate with a clear 400 and no upload or DB write", async () => {
        // Discovery surfaces SVG logo candidates; the pipeline rejects them at
        // download time, and the route must surface that as a clear 400 rather
        // than a generic 500 — and must not touch storage or the DB.
        mockDownload.mockReset();
        mockDownload.mockRejectedValueOnce(
            new ComedianImageDownloadError(
                "SVG_NOT_SUPPORTED",
                "SVG images are not supported; choose a PNG, JPG, WebP, or AVIF raster image",
            ),
        );

        const res = await POST(
            makeRequest({
                clubId: 12,
                iconImageUrl: "https://example.com/logo.svg",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.code).toBe("SVG_NOT_SUPPORTED");
        expect(body.error).toMatch(/svg/i);
        expect(mockUpload).not.toHaveBeenCalled();
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("publishes an icon-only asset without uploading or returning a hero URL", async () => {
        mockTxFindMany.mockResolvedValue([]);
        mockTxUpdateClub.mockResolvedValue({
            id: 12,
            name: "Comedy Cellar",
            city: "New York",
            state: "NY",
            website: "https://example.com",
            hasImage: true,
            visible: true,
            status: "active",
            clubType: "club",
            closedAt: null,
            totalShows: 10,
            chain: null,
            scrapingSources: [],
            shows: [],
            imageAssets: [{ heroPath: null }],
            _count: { shows: 10 },
        });
        mockDownload.mockReset();
        mockDownload.mockResolvedValueOnce({
            sourceUrl: "https://example.com/icon.jpg",
            buffer: Buffer.from("icon-original"),
            mimeType: "image/jpeg",
            width: 1600,
            height: 900,
        });
        mockGenerateVariants.mockResolvedValue({
            iconBuffer: Buffer.from("icon-variant"),
        } as never);

        const res = await POST(
            makeRequest({
                clubId: 12,
                iconImageUrl: "https://example.com/icon.jpg",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockDownload).toHaveBeenCalledTimes(1);
        expect(mockUpload).toHaveBeenCalledTimes(2);
        expect(mockUpload.mock.calls.map((call) => call[0].path)).toEqual([
            expect.stringMatching(
                /^club-images\/12\/[0-9a-f-]{36}\/original\.jpg$/,
            ),
            "clubs/Comedy%20Cellar.png",
        ]);
        const createArgs = mockTxCreate.mock.calls[0][0] as {
            data: Record<string, unknown>;
        };
        expect(createArgs.data.iconPath).toBe("clubs/Comedy%20Cellar.png");
        expect(createArgs.data.heroPath).toBeNull();
        expect(body.club.iconUrl).toBe(
            "https://cdn.example.com/clubs/Comedy%20Cellar.png",
        );
        expect(body.club.heroUrl).toBe("");
    });
});
