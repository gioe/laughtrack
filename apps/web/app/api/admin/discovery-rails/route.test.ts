import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/metrics", () => ({
    withRequestMetrics: <T>(handler: T) => handler,
}));

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        userProfile: { findFirst: vi.fn() },
        discoveryRailCatalog: { findMany: vi.fn() },
        discoveryRailPlatformPolicy: {
            findMany: vi.fn(),
            findUnique: vi.fn(),
            updateMany: vi.fn(),
        },
        discoveryRailPolicyEntry: {
            deleteMany: vi.fn(),
            createMany: vi.fn(),
        },
        adminActionAudit: { create: vi.fn() },
        $transaction: vi.fn(),
    },
}));

vi.mock("@/lib/admin/audit", () => ({
    writeAdminActionAudit: vi.fn(() => Promise.resolve({})),
}));

import { auth } from "@/auth";
import { writeAdminActionAudit } from "@/lib/admin/audit";
import { db } from "@/lib/db";
import { GET, PATCH } from "./route";

const mockAuth = vi.mocked(auth);
const mockFindProfile = vi.mocked(db.userProfile.findFirst);
const mockCatalogFindMany = vi.mocked(db.discoveryRailCatalog.findMany);
const mockPolicyFindMany = vi.mocked(db.discoveryRailPlatformPolicy.findMany);
const mockPolicyFindUnique = vi.mocked(
    db.discoveryRailPlatformPolicy.findUnique,
);
const mockPolicyUpdateMany = vi.mocked(
    db.discoveryRailPlatformPolicy.updateMany,
);
const mockDeleteMany = vi.mocked(db.discoveryRailPolicyEntry.deleteMany);
const mockCreateMany = vi.mocked(db.discoveryRailPolicyEntry.createMany);
const mockTransaction = vi.mocked(db.$transaction);
const mockAudit = vi.mocked(writeAdminActionAudit);

function makeTransactionClient() {
    return {
        discoveryRailCatalog: { findMany: vi.fn() },
        discoveryRailPlatformPolicy: {
            findMany: vi.fn(),
            findUnique: vi.fn(),
            updateMany: vi.fn(),
        },
        discoveryRailPolicyEntry: {
            deleteMany: vi.fn(),
            createMany: vi.fn(),
        },
        adminActionAudit: { create: vi.fn() },
    };
}

function runTransactionWith(tx: ReturnType<typeof makeTransactionClient>) {
    mockTransaction.mockImplementationOnce(
        ((callback: (client: typeof tx) => unknown) => callback(tx)) as never,
    );
}

const adminSession = {
    profile: { id: "profile-1", userid: "user-1", role: "admin" },
};

const currentWebPolicy = {
    platform: "web",
    policyVersion: 1,
    catalogVersion: 1,
    cycleCadenceHours: 24,
    updatedByProfileId: null,
    createdAt: new Date("2026-08-06T00:00:00Z"),
    updatedAt: new Date("2026-08-06T00:00:00Z"),
    entries: [
        {
            platform: "web",
            railKey: "shows_tonight",
            enabled: true,
            position: 0,
            rotationPool: null,
            weight: 1,
        },
        {
            platform: "web",
            railKey: "trending_comedians",
            enabled: true,
            position: 1,
            rotationPool: null,
            weight: 1,
        },
    ],
};

const validUpdate = {
    platform: "web",
    catalogVersion: 1,
    expectedVersion: 1,
    cycleCadenceHours: 12,
    rails: [
        {
            railKey: "shows_tonight",
            enabled: true,
            position: 0,
            rotationPool: null,
            weight: 1,
        },
        {
            railKey: "trending_comedians",
            enabled: true,
            position: 1,
            rotationPool: "daily_mix",
            weight: 70,
        },
        {
            railKey: "popular_clubs",
            enabled: true,
            position: 1,
            rotationPool: "daily_mix",
            weight: 30,
        },
    ],
};

function makePatch(body: unknown) {
    return new NextRequest("http://localhost/api/admin/discovery-rails", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

function makeMalformedPatch() {
    return new NextRequest("http://localhost/api/admin/discovery-rails", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: "{not-json",
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    mockAuth.mockResolvedValue(adminSession as never);
    mockFindProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
});

describe("GET /api/admin/discovery-rails", () => {
    it("requires authentication, a profile, and the admin role", async () => {
        mockAuth.mockResolvedValueOnce(null as never);
        expect((await GET()).status).toBe(401);

        mockAuth.mockResolvedValueOnce({ user: {} } as never);
        expect((await GET()).status).toBe(422);

        mockFindProfile.mockResolvedValueOnce({
            id: "profile-1",
            userid: "user-1",
            role: "user",
        } as never);
        expect((await GET()).status).toBe(403);
        expect(mockCatalogFindMany).not.toHaveBeenCalled();
    });

    it("returns the complete catalog and independent platform policies", async () => {
        const tx = makeTransactionClient();
        const catalog = [
            {
                key: "shows_tonight",
                label: "Shows tonight",
                contentKind: "show",
                requiresAuth: false,
                supportedPlatforms: ["web", "ios", "android"],
                catalogVersion: 1,
            },
        ];
        tx.discoveryRailCatalog.findMany.mockResolvedValueOnce(catalog);
        tx.discoveryRailPlatformPolicy.findMany.mockResolvedValueOnce([
            currentWebPolicy,
        ]);
        runTransactionWith(tx);

        const response = await GET();
        const body = await response.json();

        expect(response.status).toBe(200);
        expect(body.catalogVersion).toBe(1);
        expect(body.catalog).toEqual(catalog);
        expect(
            body.platforms.map(
                (policy: { platform: string }) => policy.platform,
            ),
        ).toEqual(["web", "ios", "android"]);
        expect(body.platforms[0]).toMatchObject({
            platform: "web",
            version: 1,
            cycleCadenceHours: 24,
        });
        expect(body.platforms[1].rails).toHaveLength(6);
        expect(body.platforms[2].rails).toHaveLength(6);
        expect(mockTransaction).toHaveBeenCalledWith(expect.any(Function), {
            isolationLevel: "RepeatableRead",
        });
        expect(mockCatalogFindMany).not.toHaveBeenCalled();
        expect(mockPolicyFindMany).not.toHaveBeenCalled();
    });

    it("returns 500 when policy storage cannot be read", async () => {
        const tx = makeTransactionClient();
        tx.discoveryRailCatalog.findMany.mockRejectedValueOnce(
            new Error("database down"),
        );
        tx.discoveryRailPlatformPolicy.findMany.mockResolvedValueOnce([]);
        runTransactionWith(tx);

        const response = await GET();

        expect(response.status).toBe(500);
        expect(await response.json()).toEqual({
            error: "Unable to load discovery rail policies",
        });
    });
});

describe("PATCH /api/admin/discovery-rails", () => {
    it("requires authentication, a profile, and the admin role", async () => {
        mockAuth.mockResolvedValueOnce(null as never);
        expect((await PATCH(makePatch(validUpdate))).status).toBe(401);

        mockAuth.mockResolvedValueOnce({ user: {} } as never);
        expect((await PATCH(makePatch(validUpdate))).status).toBe(422);

        mockFindProfile.mockResolvedValueOnce({
            id: "profile-1",
            userid: "user-1",
            role: "user",
        } as never);
        expect((await PATCH(makePatch(validUpdate))).status).toBe(403);

        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("rejects malformed, unknown, and platform-incompatible rails", async () => {
        expect((await PATCH(makeMalformedPatch())).status).toBe(400);
        expect(
            (
                await PATCH(
                    makePatch({
                        ...validUpdate,
                        extra: true,
                    }),
                )
            ).status,
        ).toBe(400);
        expect(
            (
                await PATCH(
                    makePatch({
                        ...validUpdate,
                        rails: [
                            {
                                ...validUpdate.rails[0],
                                railKey: "trending_podcasts",
                            },
                        ],
                    }),
                )
            ).status,
        ).toBe(400);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it.each([
        ["unknown platform", { ...validUpdate, platform: "windows" }],
        [
            "unknown rail key",
            {
                ...validUpdate,
                rails: [
                    {
                        ...validUpdate.rails[0],
                        railKey: "made_up",
                    },
                ],
            },
        ],
        [
            "ordering conflict",
            {
                ...validUpdate,
                rails: [
                    validUpdate.rails[0],
                    {
                        ...validUpdate.rails[1],
                        position: 0,
                        rotationPool: null,
                        weight: 1,
                    },
                ],
            },
        ],
        [
            "invalid weight",
            {
                ...validUpdate,
                rails: [{ ...validUpdate.rails[0], weight: 0 }],
            },
        ],
    ])("rejects %s before opening a transaction", async (_label, body) => {
        const response = await PATCH(makePatch(body));

        expect(response.status).toBe(400);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("atomically replaces a policy, increments its version, and audits it", async () => {
        const tx = makeTransactionClient();
        tx.discoveryRailPlatformPolicy.findUnique.mockResolvedValueOnce(
            currentWebPolicy,
        );
        tx.discoveryRailPlatformPolicy.updateMany.mockResolvedValueOnce({
            count: 1,
        });
        tx.discoveryRailPolicyEntry.deleteMany.mockResolvedValueOnce({
            count: 2,
        });
        tx.discoveryRailPolicyEntry.createMany.mockResolvedValueOnce({
            count: 3,
        });
        runTransactionWith(tx);

        const response = await PATCH(makePatch(validUpdate));
        const body = await response.json();

        expect(response.status).toBe(200);
        expect(body).toEqual({
            ok: true,
            policy: {
                platform: "web",
                catalogVersion: 1,
                version: 2,
                cycleCadenceHours: 12,
                rails: validUpdate.rails,
            },
        });
        expect(tx.discoveryRailPlatformPolicy.updateMany).toHaveBeenCalledWith({
            where: { platform: "web", policyVersion: 1 },
            data: {
                policyVersion: { increment: 1 },
                catalogVersion: 1,
                cycleCadenceHours: 12,
                updatedByProfileId: "profile-1",
            },
        });
        expect(tx.discoveryRailPolicyEntry.deleteMany).toHaveBeenCalledWith({
            where: { platform: "web" },
        });
        expect(tx.discoveryRailPolicyEntry.createMany).toHaveBeenCalledWith({
            data: validUpdate.rails.map((rail) => ({
                platform: "web",
                ...rail,
            })),
        });
        expect(mockAudit).toHaveBeenCalledWith(
            tx,
            expect.objectContaining({
                actorProfileId: "profile-1",
                action: "discovery_rail_policy.update",
                entityType: "discovery_rail_policy",
                entityId: "web",
                before: expect.objectContaining({ version: 1 }),
                after: expect.objectContaining({ version: 2 }),
            }),
        );
    });

    it("returns 409 without writing when the supplied version is stale", async () => {
        mockPolicyFindUnique.mockResolvedValueOnce({
            ...currentWebPolicy,
            policyVersion: 2,
        } as never);
        mockTransaction.mockImplementationOnce(
            (callback: (tx: typeof db) => unknown) => callback(db) as never,
        );

        const response = await PATCH(makePatch(validUpdate));
        const body = await response.json();

        expect(response.status).toBe(409);
        expect(body).toMatchObject({
            platform: "web",
            expectedVersion: 1,
            currentVersion: 2,
        });
        expect(mockPolicyUpdateMany).not.toHaveBeenCalled();
        expect(mockDeleteMany).not.toHaveBeenCalled();
    });

    it("detects a concurrent compare-and-swap loss before replacing entries", async () => {
        mockPolicyFindUnique
            .mockResolvedValueOnce(currentWebPolicy as never)
            .mockResolvedValueOnce({ policyVersion: 2 } as never);
        mockPolicyUpdateMany.mockResolvedValueOnce({ count: 0 } as never);
        mockTransaction.mockImplementationOnce(
            (callback: (tx: typeof db) => unknown) => callback(db) as never,
        );

        const response = await PATCH(makePatch(validUpdate));

        expect(response.status).toBe(409);
        expect(await response.json()).toMatchObject({ currentVersion: 2 });
        expect(mockDeleteMany).not.toHaveBeenCalled();
        expect(mockAudit).not.toHaveBeenCalled();
    });

    it("returns 500 when an audited transaction fails", async () => {
        mockPolicyFindUnique.mockResolvedValueOnce(currentWebPolicy as never);
        mockPolicyUpdateMany.mockResolvedValueOnce({ count: 1 } as never);
        mockDeleteMany.mockResolvedValueOnce({ count: 2 } as never);
        mockCreateMany.mockResolvedValueOnce({ count: 3 } as never);
        mockAudit.mockRejectedValueOnce(new Error("audit failed"));
        mockTransaction.mockImplementationOnce(
            (callback: (tx: typeof db) => unknown) => callback(db) as never,
        );

        const response = await PATCH(makePatch(validUpdate));

        expect(response.status).toBe(500);
        expect(await response.json()).toEqual({
            error: "Unable to update discovery rail policy",
        });
    });
});
