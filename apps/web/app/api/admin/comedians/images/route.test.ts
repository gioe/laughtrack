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
            updateMany: vi.fn(),
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

import { auth } from "@/auth";
import { db } from "@/lib/db";
import { revalidateTag } from "next/cache";
import { DELETE } from "./route";

const mockAuth = vi.mocked(auth);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockFindComedian = vi.mocked(db.comedian.findUnique);
const mockTransaction = vi.mocked(db.$transaction);
const mockRevalidateTag = vi.mocked(revalidateTag);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const txClient: any = (db as any).__txClient;
const mockTxUpdateMany = vi.mocked(txClient.comedianImageAsset.updateMany);
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
    return new NextRequest("http://localhost/api/admin/comedians/images", {
        method: "DELETE",
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
    mockFindComedian.mockResolvedValue({
        id: 7,
        name: "Alex Example",
        hasImage: true,
        imageAssets: [
            {
                id: 42,
                sourceImageUrl: "https://example.com/headshot.jpg",
                originalPath: "comedian-images/7/original.jpg",
                avatarPath: "comedian-images/7/avatar.jpg",
                heroPath: "comedian-images/7/hero.jpg",
            },
        ],
    } as never);
    mockTxUpdateMany.mockResolvedValue({ count: 1 });
    mockTxUpdateComedian.mockResolvedValue({} as never);
    mockTxAuditCreate.mockResolvedValue({} as never);
    mockTransaction.mockImplementation(
        async (callback: (tx: typeof txClient) => unknown) =>
            callback(txClient),
    );
});

describe("DELETE /api/admin/comedians/images", () => {
    it("requires admin access", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await DELETE(makeRequest({ comedianId: 7 }));

        expect(res.status).toBe(401);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("rejects invalid payloads", async () => {
        const res = await DELETE(makeRequest({ comedianId: 0 }));

        expect(res.status).toBe(400);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("returns 404 when comedian not found", async () => {
        mockFindComedian.mockResolvedValue(null);

        const res = await DELETE(makeRequest({ comedianId: 99 }));

        expect(res.status).toBe(404);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("deactivates active image assets and clears hasImage", async () => {
        const res = await DELETE(makeRequest({ comedianId: 7 }));
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ ok: true, comedianId: 7, hasImage: false });
        expect(mockTxUpdateMany).toHaveBeenCalledWith({
            where: { comedianId: 7, isActive: true },
            data: { isActive: false },
        });
        expect(mockTxUpdateComedian).toHaveBeenCalledWith({
            where: { id: 7 },
            data: { hasImage: false },
        });
        expect(mockTxAuditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                actorProfileId: "profile-1",
                action: "comedian_image.remove",
                entityType: "comedian",
                entityId: "7",
                after: { hasImage: false, activeAssets: [] },
            }),
        });
        expect(mockRevalidateTag).toHaveBeenCalledWith("comedian-search-data");
        expect(mockRevalidateTag).toHaveBeenCalledWith("comedian-detail-data");
        expect(mockRevalidateTag).toHaveBeenCalledWith("comedian-metadata");
        expect(mockRevalidateTag).toHaveBeenCalledWith("Alex Example");
    });
});
