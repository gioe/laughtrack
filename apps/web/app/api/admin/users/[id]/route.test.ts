import { describe, it, expect, vi, beforeEach } from "vitest";
import type { MockedFunction } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        userProfile: {
            findFirst: vi.fn(),
        },
        $transaction: vi.fn(
            async (callback: (tx: unknown) => Promise<unknown>) =>
                callback({
                    user: {
                        findUnique: vi.fn(),
                        update: vi.fn(),
                    },
                    userProfile: {
                        update: vi.fn(),
                    },
                    adminActionAudit: {
                        create: vi.fn(),
                    },
                }),
        ),
        user: {
            findUnique: vi.fn(),
            update: vi.fn(),
        },
    },
}));

vi.mock("@prisma/client", () => ({
    Prisma: {
        PrismaClientKnownRequestError: class PrismaClientKnownRequestError extends Error {
            code: string;
            constructor(message: string, opts: { code: string }) {
                super(message);
                this.code = opts.code;
            }
        },
        prismaVersion: { client: "test" },
    },
}));

import { PATCH } from "./route";
import { auth } from "@/auth";
import { db } from "@/lib/db";

type TxClient = {
    user: { findUnique: unknown; update: unknown };
    userProfile: { update: unknown };
    adminActionAudit: { create: unknown };
};
type TxCallback = (tx: TxClient) => Promise<unknown>;
type TxImpl = (callback: TxCallback) => Promise<unknown>;

const mockAuth = vi.mocked(auth);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockTransaction = db.$transaction as unknown as MockedFunction<TxImpl>;

const USER_ID = "user-123";

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function userSnapshot(overrides: Record<string, unknown> = {}) {
    return {
        id: USER_ID,
        name: "Old Name",
        image: null,
        profile: {
            id: "profile-target",
            role: "user",
            zipCode: null,
            nearbyDistanceMiles: null,
            emailShowNotifications: false,
            pushShowNotifications: false,
            comedianOnboardingCompleted: false,
        },
        ...overrides,
    };
}

function makeRequest(
    body: unknown,
    id: string = USER_ID,
): [NextRequest, { params: Promise<{ id: string }> }] {
    const req = new NextRequest(`http://localhost/api/admin/users/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: typeof body === "string" ? body : JSON.stringify(body),
    });
    return [req, { params: Promise.resolve({ id }) }];
}

type AnyFn = (...args: never[]) => unknown;

function installTxMock(
    findBefore: AnyFn,
    findAfter: AnyFn,
    userUpdate: AnyFn,
    profileUpdate: AnyFn,
    auditCreate: AnyFn,
) {
    let call = 0;
    const impl: TxImpl = async (callback) =>
        callback({
            user: {
                findUnique: vi.fn().mockImplementation(() => {
                    const fn = call === 0 ? findBefore : findAfter;
                    call += 1;
                    return fn();
                }),
                update: userUpdate,
            },
            userProfile: { update: profileUpdate },
            adminActionAudit: { create: auditCreate },
        });
    mockTransaction.mockImplementation(impl as never);
}

beforeEach(() => {
    vi.clearAllMocks();
    mockFindUserProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
});

describe("PATCH /api/admin/users/[id]", () => {
    it("returns 401 when auth() returns null", async () => {
        mockAuth.mockResolvedValue(null as never);

        const [req, ctx] = makeRequest({ name: "X" });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(401);
    });

    it("returns 422 when session has no profile", async () => {
        mockAuth.mockResolvedValue({ user: {} } as never);

        const [req, ctx] = makeRequest({ name: "X" });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(422);
    });

    it("returns 403 when profile.role !== 'admin'", async () => {
        mockAuth.mockResolvedValue({
            profile: { id: "p", userid: "u", role: "user" },
        } as never);
        mockFindUserProfile.mockResolvedValue({
            id: "p",
            userid: "u",
            role: "user",
        } as never);

        const [req, ctx] = makeRequest({ name: "X" });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(403);
    });

    it("returns 400 for non-JSON body", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const [req, ctx] = makeRequest("not-json-{{{");
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 for an empty patch", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const [req, ctx] = makeRequest({});
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 for invalid zipCode shape", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const [req, ctx] = makeRequest({ zipCode: "abcde" });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 for non-positive nearbyDistanceMiles", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const [req, ctx] = makeRequest({ nearbyDistanceMiles: 0 });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 for unknown field", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const [req, ctx] = makeRequest({ email: "x@y.com" });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 404 when the user does not exist", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        installTxMock(
            vi.fn().mockResolvedValue(null),
            vi.fn(),
            vi.fn(),
            vi.fn(),
            vi.fn(),
        );

        const [req, ctx] = makeRequest({ name: "X" });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(404);
    });

    it("returns 422 when profile fields are sent for a user with no profile", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        installTxMock(
            vi.fn().mockResolvedValue(userSnapshot({ profile: null })),
            vi.fn(),
            vi.fn(),
            vi.fn(),
            vi.fn(),
        );

        const [req, ctx] = makeRequest({ zipCode: "10001" });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(422);
    });

    it("updates user-level fields, writes audit, returns 200", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const before = userSnapshot();
        const after = userSnapshot({ name: "New Name" });
        const userUpdate = vi.fn();
        const profileUpdate = vi.fn();
        const auditCreate = vi.fn();

        installTxMock(
            vi.fn().mockResolvedValue(before),
            vi.fn().mockResolvedValue(after),
            userUpdate,
            profileUpdate,
            auditCreate,
        );

        const [req, ctx] = makeRequest({ name: "New Name" });
        const res = await PATCH(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.ok).toBe(true);
        expect(userUpdate).toHaveBeenCalledWith({
            where: { id: USER_ID },
            data: { name: "New Name" },
        });
        expect(profileUpdate).not.toHaveBeenCalled();
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                actorProfileId: "profile-1",
                action: "user.update",
                entityType: "user",
                entityId: USER_ID,
            }),
        });
    });

    it("updates profile-level fields without touching user", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const before = userSnapshot();
        const after = userSnapshot({
            profile: {
                ...before.profile,
                zipCode: "10001",
                nearbyDistanceMiles: 25,
                emailShowNotifications: true,
            },
        });
        const userUpdate = vi.fn();
        const profileUpdate = vi.fn();
        const auditCreate = vi.fn();

        installTxMock(
            vi.fn().mockResolvedValue(before),
            vi.fn().mockResolvedValue(after),
            userUpdate,
            profileUpdate,
            auditCreate,
        );

        const [req, ctx] = makeRequest({
            zipCode: "10001",
            nearbyDistanceMiles: 25,
            emailShowNotifications: true,
        });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(200);
        expect(userUpdate).not.toHaveBeenCalled();
        expect(profileUpdate).toHaveBeenCalledWith({
            where: { id: "profile-target" },
            data: {
                zipCode: "10001",
                nearbyDistanceMiles: 25,
                emailShowNotifications: true,
            },
        });
        expect(auditCreate).toHaveBeenCalled();
    });

    it("clears nullable fields when null is sent", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const before = userSnapshot({
            name: "Existing",
            profile: {
                ...userSnapshot().profile,
                zipCode: "94110",
                nearbyDistanceMiles: 10,
            },
        });
        const after = userSnapshot({
            name: null,
            profile: {
                ...before.profile,
                zipCode: null,
                nearbyDistanceMiles: null,
            },
        });
        const userUpdate = vi.fn();
        const profileUpdate = vi.fn();

        installTxMock(
            vi.fn().mockResolvedValue(before),
            vi.fn().mockResolvedValue(after),
            userUpdate,
            profileUpdate,
            vi.fn(),
        );

        const [req, ctx] = makeRequest({
            name: null,
            zipCode: null,
            nearbyDistanceMiles: null,
        });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(200);
        expect(userUpdate).toHaveBeenCalledWith({
            where: { id: USER_ID },
            data: { name: null },
        });
        expect(profileUpdate).toHaveBeenCalledWith({
            where: { id: "profile-target" },
            data: { zipCode: null, nearbyDistanceMiles: null },
        });
    });
});
