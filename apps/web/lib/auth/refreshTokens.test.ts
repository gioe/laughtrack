import { describe, it, expect, vi, beforeEach } from "vitest";

const {
    mockFindUnique,
    mockUpdate,
    mockUpdateMany,
    mockCreate,
    mockDeleteMany,
} = vi.hoisted(() => ({
    mockFindUnique: vi.fn(),
    mockUpdate: vi.fn(),
    mockUpdateMany: vi.fn(),
    mockCreate: vi.fn(),
    mockDeleteMany: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        $transaction: vi.fn(
            async (
                cb: (tx: {
                    refreshToken: {
                        findUnique: typeof mockFindUnique;
                        update: typeof mockUpdate;
                        updateMany: typeof mockUpdateMany;
                    };
                }) => unknown,
            ) =>
                cb({
                    refreshToken: {
                        findUnique: mockFindUnique,
                        update: mockUpdate,
                        updateMany: mockUpdateMany,
                    },
                }),
        ),
        refreshToken: {
            create: mockCreate,
            updateMany: mockUpdateMany,
            deleteMany: mockDeleteMany,
        },
    },
}));

vi.mock("@/util/token", () => ({
    REFRESH_TOKEN_TTL_SECONDS: 2_592_000,
    generateRefreshTokenString: vi.fn(() => "new-token"),
}));

import {
    cleanupExpiredRefreshTokens,
    consumeRefreshToken,
    REFRESH_TOKEN_CLEANUP_REVOKED_GRACE_DAYS,
    revokeAllRefreshTokens,
} from "@/lib/auth/refreshTokens";

beforeEach(() => {
    vi.clearAllMocks();
});

describe("consumeRefreshToken", () => {
    it("returns 'not_found' when the token does not exist", async () => {
        mockFindUnique.mockResolvedValue(null);

        const result = await consumeRefreshToken("missing");

        expect(result).toBe("not_found");
        expect(mockUpdate).not.toHaveBeenCalled();
        expect(mockUpdateMany).not.toHaveBeenCalled();
    });

    it("detects reuse, revokes the user's sibling tokens, returns revoked_reuse", async () => {
        mockFindUnique.mockResolvedValue({
            id: "rt-1",
            userId: "user-9",
            expiresAt: new Date(Date.now() + 60_000),
            revokedAt: new Date(Date.now() - 60_000),
            user: { email: "u@example.com" },
        });
        mockUpdateMany.mockResolvedValue({ count: 2 });

        const result = await consumeRefreshToken("reused");

        expect(result).toEqual({
            status: "revoked_reuse",
            userId: "user-9",
            familyRevokedCount: 2,
        });
        expect(mockUpdateMany).toHaveBeenCalledTimes(1);
        expect(mockUpdateMany).toHaveBeenCalledWith({
            where: { userId: "user-9", revokedAt: null },
            data: { revokedAt: expect.any(Date) },
        });
        expect(mockUpdate).not.toHaveBeenCalled();
    });

    it("returns revoked_reuse with count=0 when no sibling tokens are active", async () => {
        mockFindUnique.mockResolvedValue({
            id: "rt-1",
            userId: "user-9",
            expiresAt: new Date(Date.now() + 60_000),
            revokedAt: new Date(Date.now() - 60_000),
            user: { email: "u@example.com" },
        });
        mockUpdateMany.mockResolvedValue({ count: 0 });

        const result = await consumeRefreshToken("reused");

        expect(result).toEqual({
            status: "revoked_reuse",
            userId: "user-9",
            familyRevokedCount: 0,
        });
    });

    it("returns 'expired' when the token is past expiry", async () => {
        mockFindUnique.mockResolvedValue({
            id: "rt-1",
            userId: "user-9",
            expiresAt: new Date(Date.now() - 60_000),
            revokedAt: null,
            user: { email: "u@example.com" },
        });

        const result = await consumeRefreshToken("old");

        expect(result).toBe("expired");
        expect(mockUpdate).not.toHaveBeenCalled();
        expect(mockUpdateMany).not.toHaveBeenCalled();
    });

    it("returns 'user_missing' when the user relation has no email", async () => {
        mockFindUnique.mockResolvedValue({
            id: "rt-1",
            userId: "user-9",
            expiresAt: new Date(Date.now() + 60_000),
            revokedAt: null,
            user: { email: null },
        });

        const result = await consumeRefreshToken("tok");

        expect(result).toBe("user_missing");
        expect(mockUpdate).not.toHaveBeenCalled();
    });

    it("revokes only the presented token and returns user details on success", async () => {
        mockFindUnique.mockResolvedValue({
            id: "rt-1",
            userId: "user-9",
            expiresAt: new Date(Date.now() + 60_000),
            revokedAt: null,
            user: { email: "u@example.com" },
        });

        const result = await consumeRefreshToken("valid");

        expect(result).toEqual({
            userId: "user-9",
            userEmail: "u@example.com",
        });
        expect(mockUpdate).toHaveBeenCalledTimes(1);
        expect(mockUpdate).toHaveBeenCalledWith({
            where: { id: "rt-1" },
            data: { revokedAt: expect.any(Date) },
        });
        expect(mockUpdateMany).not.toHaveBeenCalled();
    });
});

describe("revokeAllRefreshTokens", () => {
    it("revokes every active refresh token for the given user", async () => {
        mockUpdateMany.mockResolvedValue({ count: 4 });

        const count = await revokeAllRefreshTokens("user-9");

        expect(count).toBe(4);
        expect(mockUpdateMany).toHaveBeenCalledWith({
            where: { userId: "user-9", revokedAt: null },
            data: { revokedAt: expect.any(Date) },
        });
    });
});

describe("cleanupExpiredRefreshTokens", () => {
    it("deletes tokens past expiry or revoked beyond the default grace window", async () => {
        mockDeleteMany.mockResolvedValue({ count: 12 });

        const before = Date.now();
        const result = await cleanupExpiredRefreshTokens();
        const after = Date.now();

        expect(result).toEqual({ deleted: 12 });
        expect(mockDeleteMany).toHaveBeenCalledTimes(1);

        const args = mockDeleteMany.mock.calls[0][0];
        expect(args.where.OR).toHaveLength(2);

        const expiresClause = args.where.OR[0].expiresAt.lt as Date;
        const revokedClause = args.where.OR[1].revokedAt.lt as Date;
        const expectedRevokedCutoffMin =
            before -
            REFRESH_TOKEN_CLEANUP_REVOKED_GRACE_DAYS * 24 * 60 * 60 * 1000;
        const expectedRevokedCutoffMax =
            after -
            REFRESH_TOKEN_CLEANUP_REVOKED_GRACE_DAYS * 24 * 60 * 60 * 1000;

        expect(expiresClause.getTime()).toBeGreaterThanOrEqual(before);
        expect(expiresClause.getTime()).toBeLessThanOrEqual(after);
        expect(revokedClause.getTime()).toBeGreaterThanOrEqual(
            expectedRevokedCutoffMin,
        );
        expect(revokedClause.getTime()).toBeLessThanOrEqual(
            expectedRevokedCutoffMax,
        );
    });

    it("honors a custom revoked retention window", async () => {
        mockDeleteMany.mockResolvedValue({ count: 0 });

        const before = Date.now();
        await cleanupExpiredRefreshTokens(30);
        const after = Date.now();

        const args = mockDeleteMany.mock.calls[0][0];
        const revokedClause = args.where.OR[1].revokedAt.lt as Date;
        const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000;

        expect(revokedClause.getTime()).toBeGreaterThanOrEqual(
            before - thirtyDaysMs,
        );
        expect(revokedClause.getTime()).toBeLessThanOrEqual(
            after - thirtyDaysMs,
        );
    });
});
