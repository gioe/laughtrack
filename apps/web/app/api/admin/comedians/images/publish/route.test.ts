import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("next/cache", () => ({
    revalidateTag: vi.fn(),
}));

vi.mock("@/lib/db", () => {
    const txClient = {
        comedianImageAsset: {
            findMany: vi.fn(),
            updateMany: vi.fn(),
            create: vi.fn(),
        },
        comedian: {
            update: vi.fn(),
        },
        adminActionAudit: {
            create: vi.fn(),
        },
    };
    return {
        db: {
            comedian: {
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

vi.mock("@/lib/admin/comedianImagePipeline", async () => {
    const actual = await vi.importActual<
        typeof import("@/lib/admin/comedianImagePipeline")
    >("@/lib/admin/comedianImagePipeline");
    return {
        ...actual,
        downloadComedianImage: vi.fn(),
        readUploadedComedianImage: vi.fn(),
        generateComedianImageVariants: vi.fn(),
    };
});

vi.mock("@/lib/admin/bunnyStorage", () => ({
    uploadToBunnyStorage: vi.fn(),
    deleteFromBunnyStorage: vi.fn(),
}));

import { auth } from "@/auth";
import { db } from "@/lib/db";
import { revalidateTag } from "next/cache";
import {
    ComedianImageDownloadError,
    downloadComedianImage,
    generateComedianImageVariants,
    readUploadedComedianImage,
} from "@/lib/admin/comedianImagePipeline";
import {
    deleteFromBunnyStorage,
    uploadToBunnyStorage,
} from "@/lib/admin/bunnyStorage";
import { POST } from "./route";

const mockAuth = vi.mocked(auth);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockFindComedian = vi.mocked(db.comedian.findUnique);
const mockTransaction = vi.mocked(db.$transaction);
const mockRevalidateTag = vi.mocked(revalidateTag);
const mockDownload = vi.mocked(downloadComedianImage);
const mockReadUploaded = vi.mocked(readUploadedComedianImage);
const mockGenerateVariants = vi.mocked(generateComedianImageVariants);
const mockUpload = vi.mocked(uploadToBunnyStorage);
const mockDelete = vi.mocked(deleteFromBunnyStorage);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const txClient: any = (db as any).__txClient;
const mockTxFindMany = vi.mocked(txClient.comedianImageAsset.findMany);
const mockTxUpdateMany = vi.mocked(txClient.comedianImageAsset.updateMany);
const mockTxCreate = vi.mocked(txClient.comedianImageAsset.create);
const mockTxUpdateComedian = vi.mocked(txClient.comedian.update);
const mockTxAuditCreate = vi.mocked(txClient.adminActionAudit.create);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makeRequest(body: unknown) {
    return new NextRequest(
        "http://localhost/api/admin/comedians/images/publish",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        },
    );
}

function makeFormRequest(formData: FormData) {
    return new NextRequest(
        "http://localhost/api/admin/comedians/images/publish",
        {
            method: "POST",
            body: formData,
        },
    );
}

function expectAvatarPathPattern(path: string, comedianId: number) {
    expect(path).toMatch(
        new RegExp(
            `^comedian-images/${comedianId}/[0-9a-f-]{36}/avatar\\.jpg$`,
        ),
    );
}
function expectHeroPathPattern(path: string, comedianId: number) {
    expect(path).toMatch(
        new RegExp(`^comedian-images/${comedianId}/[0-9a-f-]{36}/hero\\.jpg$`),
    );
}
function expectOriginalPathPattern(
    path: string,
    comedianId: number,
    ext: string,
) {
    expect(path).toMatch(
        new RegExp(
            `^comedian-images/${comedianId}/[0-9a-f-]{36}/original\\.${ext}$`,
        ),
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
        hasImage: false,
    } as never);
    mockDownload.mockResolvedValue({
        sourceUrl: "https://example.com/headshot.jpg",
        buffer: Buffer.from("original-bytes"),
        mimeType: "image/jpeg",
        width: 2400,
        height: 2400,
    });
    mockReadUploaded.mockResolvedValue({
        sourceUrl: "upload:headshot.jpg",
        buffer: Buffer.from("uploaded-original-bytes"),
        mimeType: "image/jpeg",
        width: 2400,
        height: 2400,
    });
    mockGenerateVariants.mockResolvedValue({
        avatarBuffer: Buffer.from("avatar-bytes"),
        heroBuffer: Buffer.from("hero-bytes"),
    });
    mockUpload.mockResolvedValue();
    mockDelete.mockResolvedValue();
    mockTxFindMany.mockResolvedValue([]);
    mockTxUpdateMany.mockResolvedValue({ count: 0 });
    mockTxCreate.mockImplementation(async (args: { data: unknown }) => {
        const data = args.data as {
            comedianId: number;
            sourceImageUrl: string;
            originalPath: string;
            avatarPath: string | null;
            heroPath: string | null;
            mimeType: string | null;
            width: number | null;
            height: number | null;
            isActive: boolean;
        };
        return {
            id: 42,
            ...data,
        };
    });
    mockTxUpdateComedian.mockResolvedValue({} as never);
    mockTxAuditCreate.mockResolvedValue({} as never);
    mockTransaction.mockImplementation(
        async (callback: (tx: typeof txClient) => unknown) =>
            callback(txClient),
    );
});

describe("POST /api/admin/comedians/images/publish", () => {
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
        expect(mockUpload).not.toHaveBeenCalled();
    });

    it("rejects invalid payloads", async () => {
        const res = await POST(
            makeRequest({ comedianId: 7, imageUrl: "not-a-url" }),
        );
        expect(res.status).toBe(400);
        expect(mockDownload).not.toHaveBeenCalled();
        expect(mockUpload).not.toHaveBeenCalled();
    });

    it("returns 404 when comedian not found", async () => {
        mockFindComedian.mockResolvedValue(null);
        const res = await POST(
            makeRequest({
                comedianId: 99,
                imageUrl: "https://example.com/h.jpg",
            }),
        );
        expect(res.status).toBe(404);
        expect(mockUpload).not.toHaveBeenCalled();
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("forwards pipeline errors as 400 and does not touch storage or DB", async () => {
        mockDownload.mockRejectedValue(
            new ComedianImageDownloadError(
                "BLOCKED_HOST",
                "Image host is not allowed",
            ),
        );
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "http://127.0.0.1/x.jpg",
            }),
        );
        expect(res.status).toBe(400);
        const body = await res.json();
        expect(body.code).toBe("BLOCKED_HOST");
        expect(mockUpload).not.toHaveBeenCalled();
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("uploads original, avatar, and hero to stable id-based Bunny paths", async () => {
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/headshot.jpg",
                sourcePageUrl: "https://example.com/press",
            }),
        );
        expect(res.status).toBe(200);
        expect(mockUpload).toHaveBeenCalledTimes(3);

        const calls = mockUpload.mock.calls.map((call) => call[0]);
        const originalCall = calls[0];
        const avatarCall = calls[1];
        const heroCall = calls[2];

        expectOriginalPathPattern(originalCall.path, 7, "jpg");
        expect(originalCall.contentType).toBe("image/jpeg");
        expect(Buffer.from(originalCall.body).toString()).toBe(
            "original-bytes",
        );

        expectAvatarPathPattern(avatarCall.path, 7);
        expect(avatarCall.contentType).toBe("image/jpeg");
        expect(Buffer.from(avatarCall.body).toString()).toBe("avatar-bytes");

        expectHeroPathPattern(heroCall.path, 7);
        expect(heroCall.contentType).toBe("image/jpeg");
        expect(Buffer.from(heroCall.body).toString()).toBe("hero-bytes");

        // All three uploads share the same slug directory
        const slug = originalCall.path.split("/")[2];
        expect(avatarCall.path).toContain(`/${slug}/`);
        expect(heroCall.path).toContain(`/${slug}/`);
    });

    it("uses a separate hero image url for the uploaded hero variant", async () => {
        mockDownload
            .mockResolvedValueOnce({
                sourceUrl: "https://example.com/headshot.jpg",
                buffer: Buffer.from("headshot-original"),
                mimeType: "image/jpeg",
                width: 2400,
                height: 2400,
            })
            .mockResolvedValueOnce({
                sourceUrl: "https://example.com/hero.jpg",
                buffer: Buffer.from("hero-original"),
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

        expect(mockDownload).toHaveBeenNthCalledWith(
            1,
            "https://example.com/headshot.jpg",
        );
        expect(mockDownload).toHaveBeenNthCalledWith(
            2,
            "https://example.com/hero.jpg",
        );

        expect(mockUpload).toHaveBeenCalledTimes(4);
        const calls = mockUpload.mock.calls.map((call) => call[0]);
        expect(Buffer.from(calls[0].body).toString()).toBe("headshot-original");
        expect(Buffer.from(calls[1].body).toString()).toBe(
            "avatar-from-headshot",
        );
        expect(Buffer.from(calls[2].body).toString()).toBe("hero-original");
        expect(Buffer.from(calls[3].body).toString()).toBe(
            "hero-from-hero-source",
        );

        const createArgs = mockTxCreate.mock.calls[0][0] as {
            data: Record<string, unknown>;
        };
        const metadata = createArgs.data.metadata as Record<string, unknown>;
        expect(createArgs.data.sourceImageUrl).toBe(
            "https://example.com/headshot.jpg",
        );
        expect(metadata.heroSourceImageUrl).toBe(
            "https://example.com/hero.jpg",
        );
    });

    it("can publish only a headshot URL without requiring a hero", async () => {
        const res = await POST(
            makeRequest({
                comedianId: 7,
                headshotImageUrl: "https://example.com/headshot.jpg",
            }),
        );
        expect(res.status).toBe(200);
        expect(mockUpload).toHaveBeenCalledTimes(2);

        const calls = mockUpload.mock.calls.map((call) => call[0]);
        expectOriginalPathPattern(calls[0].path, 7, "jpg");
        expectAvatarPathPattern(calls[1].path, 7);

        const createArgs = mockTxCreate.mock.calls[0][0] as {
            data: Record<string, unknown>;
        };
        expectAvatarPathPattern(createArgs.data.avatarPath as string, 7);
        expect(createArgs.data.heroPath).toBeNull();
    });

    it("can publish only a hero URL while preserving an existing headshot", async () => {
        mockDownload.mockResolvedValueOnce({
            sourceUrl: "https://example.com/hero.jpg",
            buffer: Buffer.from("hero-original"),
            mimeType: "image/jpeg",
            width: 2400,
            height: 1350,
        });
        mockGenerateVariants.mockResolvedValueOnce({
            avatarBuffer: Buffer.from("unused-avatar"),
            heroBuffer: Buffer.from("hero-from-url"),
        });
        mockTxFindMany.mockResolvedValueOnce([
            {
                id: 11,
                sourceImageUrl: "https://old.example.com/headshot.jpg",
                originalPath: "comedian-images/7/old-slug/original.jpg",
                avatarPath: "comedian-images/7/old-slug/avatar.jpg",
                heroPath: null,
                mimeType: "image/jpeg",
                width: 1800,
                height: 1800,
            },
        ]);

        const res = await POST(
            makeRequest({
                comedianId: 7,
                heroImageUrl: "https://example.com/hero.jpg",
            }),
        );
        expect(res.status).toBe(200);
        expect(mockUpload).toHaveBeenCalledTimes(2);

        const calls = mockUpload.mock.calls.map((call) => call[0]);
        expectOriginalPathPattern(calls[0].path, 7, "jpg");
        expectHeroPathPattern(calls[1].path, 7);

        const createArgs = mockTxCreate.mock.calls[0][0] as {
            data: Record<string, unknown>;
        };
        expect(createArgs.data.avatarPath).toBe(
            "comedian-images/7/old-slug/avatar.jpg",
        );
        expectHeroPathPattern(createArgs.data.heroPath as string, 7);
    });

    it("can publish a headshot from an uploaded file", async () => {
        const formData = new FormData();
        formData.set("comedianId", "7");
        formData.set(
            "headshotFile",
            new File([new Uint8Array([1, 2, 3])], "headshot.jpg", {
                type: "image/jpeg",
            }),
        );

        const res = await POST(makeFormRequest(formData));
        expect(res.status).toBe(200);

        expect(mockReadUploaded).toHaveBeenCalledTimes(1);
        expect(mockReadUploaded.mock.calls[0][0].name).toBe("headshot.jpg");
        expect(mockUpload).toHaveBeenCalledTimes(2);

        const createArgs = mockTxCreate.mock.calls[0][0] as {
            data: Record<string, unknown>;
        };
        expect(createArgs.data.sourceImageUrl).toBe("upload:headshot.jpg");
        expectAvatarPathPattern(createArgs.data.avatarPath as string, 7);
        expect(createArgs.data.heroPath).toBeNull();
    });

    it("rejects invalid source aspect ratios before uploading to Bunny", async () => {
        mockDownload.mockResolvedValueOnce({
            sourceUrl: "https://example.com/headshot.jpg",
            buffer: Buffer.from("headshot"),
            mimeType: "image/jpeg",
            width: 1200,
            height: 1600,
        });

        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/headshot.jpg",
                heroImageUrl: "https://example.com/hero.jpg",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.code).toBe("INVALID_ASPECT_RATIO");
        expect(body.error).toMatch(/Headshot source/);
        expect(mockUpload).not.toHaveBeenCalled();
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("returns 502 when bunny upload fails and never mutates DB", async () => {
        mockUpload.mockRejectedValueOnce(new Error("network down"));
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/h.jpg",
            }),
        );
        expect(res.status).toBe(502);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("cleans up the original upload when the avatar PUT fails mid-flight", async () => {
        // First upload (original) succeeds, second (avatar) throws.
        mockUpload
            .mockResolvedValueOnce()
            .mockRejectedValueOnce(new Error("avatar PUT failed"));
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/h.jpg",
            }),
        );
        expect(res.status).toBe(502);
        // Only the original was uploaded → only it should be cleaned up.
        expect(mockDelete).toHaveBeenCalledTimes(1);
        expectOriginalPathPattern(mockDelete.mock.calls[0][0], 7, "jpg");
    });

    it("cleans up all three uploads when the DB transaction fails", async () => {
        mockTransaction.mockRejectedValueOnce(new Error("db unavailable"));
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/h.jpg",
            }),
        );
        expect(res.status).toBe(500);
        expect(mockDelete).toHaveBeenCalledTimes(3);
        const deletedPaths = mockDelete.mock.calls
            .map((c) => c[0] as string)
            .sort();
        // Sort to make assertion order-independent; we already cover ordering
        // in the upload-path tests.
        expect(deletedPaths.some((p) => p.endsWith("/original.jpg"))).toBe(
            true,
        );
        expect(deletedPaths.some((p) => p.endsWith("/avatar.jpg"))).toBe(true);
        expect(deletedPaths.some((p) => p.endsWith("/hero.jpg"))).toBe(true);
    });

    it("swallows cleanup failures so the original error remains the response", async () => {
        mockTransaction.mockRejectedValueOnce(new Error("db unavailable"));
        mockDelete.mockRejectedValue(new Error("bunny delete failed"));
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/h.jpg",
            }),
        );
        expect(res.status).toBe(500);
        const body = await res.json();
        expect(body.error).toBe("Publish failed during DB update");
    });

    it("marks prior active assets inactive, activates the new asset, sets hasImage, audits, and revalidates", async () => {
        mockTxFindMany.mockResolvedValueOnce([
            {
                id: 11,
                sourceImageUrl: "https://old.example.com/h.jpg",
                originalPath: "comedian-images/7/old-slug/original.jpg",
                avatarPath: "comedian-images/7/old-slug/avatar.jpg",
                heroPath: "comedian-images/7/old-slug/hero.jpg",
                mimeType: "image/jpeg",
                width: 1800,
                height: 1800,
            },
        ]);

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
        expect(body.asset.id).toBe(42);
        expectAvatarPathPattern(body.asset.avatarPath, 7);
        expectHeroPathPattern(body.asset.heroPath, 7);

        expect(mockTxUpdateMany).toHaveBeenCalledWith({
            where: { comedianId: 7, isActive: true },
            data: { isActive: false },
        });

        expect(mockTxCreate).toHaveBeenCalledTimes(1);
        const createArgs = mockTxCreate.mock.calls[0][0] as {
            data: Record<string, unknown>;
        };
        expect(createArgs.data.comedianId).toBe(7);
        expect(createArgs.data.sourceImageUrl).toBe(
            "https://example.com/headshot.jpg",
        );
        expect(createArgs.data.isActive).toBe(true);
        expect(createArgs.data.mimeType).toBe("image/jpeg");
        expect(createArgs.data.width).toBe(2400);
        expect(createArgs.data.height).toBe(2400);
        expectAvatarPathPattern(createArgs.data.avatarPath as string, 7);
        expectHeroPathPattern(createArgs.data.heroPath as string, 7);
        const metadata = createArgs.data.metadata as Record<string, unknown>;
        expect(metadata.sourcePageUrl).toBe("https://example.com/press");
        expect(typeof metadata.assetSlug).toBe("string");

        expect(mockTxUpdateComedian).toHaveBeenCalledWith({
            where: { id: 7 },
            data: { hasImage: true },
        });

        expect(mockTxAuditCreate).toHaveBeenCalledTimes(1);
        const auditArgs = mockTxAuditCreate.mock.calls[0][0] as {
            data: Record<string, unknown>;
        };
        expect(auditArgs.data.action).toBe("comedian_image.publish");
        expect(auditArgs.data.entityType).toBe("comedian");
        expect(auditArgs.data.entityId).toBe("7");
        expect(auditArgs.data.actorProfileId).toBe("profile-1");
        const before = auditArgs.data.before as Record<string, unknown>;
        expect(before.hasImage).toBe(false);
        expect((before.activeAsset as { id: number }).id).toBe(11);
        const after = auditArgs.data.after as Record<string, unknown>;
        expect(after.hasImage).toBe(true);
        expect((after.activeAsset as { id: number }).id).toBe(42);

        expect(mockRevalidateTag).toHaveBeenCalledWith("comedian-search-data");
        expect(mockRevalidateTag).toHaveBeenCalledWith("comedian-detail-data");
        expect(mockRevalidateTag).toHaveBeenCalledWith("comedian-metadata");
        expect(mockRevalidateTag).toHaveBeenCalledWith("Alex Example");
    });

    it("publishes the first asset for a comedian with no prior active asset", async () => {
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/headshot.jpg",
            }),
        );
        expect(res.status).toBe(200);
        // findMany returns empty -> updateMany must not be called for inactivation
        expect(mockTxUpdateMany).not.toHaveBeenCalled();
        expect(mockTxCreate).toHaveBeenCalledTimes(1);
        expect(mockTxUpdateComedian).toHaveBeenCalledWith({
            where: { id: 7 },
            data: { hasImage: true },
        });
        const auditArgs = mockTxAuditCreate.mock.calls[0][0] as {
            data: Record<string, unknown>;
        };
        const before = auditArgs.data.before as Record<string, unknown>;
        expect(before.activeAsset).toBeNull();
        expect(before.previousAssetIds).toEqual([]);
    });

    it("does not revalidate if the DB transaction fails", async () => {
        mockTransaction.mockRejectedValueOnce(new Error("db unavailable"));
        const res = await POST(
            makeRequest({
                comedianId: 7,
                imageUrl: "https://example.com/h.jpg",
            }),
        );
        expect(res.status).toBe(500);
        expect(mockRevalidateTag).not.toHaveBeenCalled();
    });
});
