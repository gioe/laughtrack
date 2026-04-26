import { db } from "@/lib/db";
import {
    REFRESH_TOKEN_TTL_SECONDS,
    generateRefreshTokenString,
} from "@/util/token";

export interface IssuedRefreshToken {
    token: string;
    expiresAt: Date;
}

export async function issueRefreshToken(
    userId: string,
): Promise<IssuedRefreshToken> {
    const token = generateRefreshTokenString();
    const expiresAt = new Date(Date.now() + REFRESH_TOKEN_TTL_SECONDS * 1000);
    await db.refreshToken.create({
        data: { token, userId, expiresAt },
    });
    return { token, expiresAt };
}

export interface ResolvedRefreshToken {
    userId: string;
    userEmail: string;
}

export type RefreshTokenError = "not_found" | "expired" | "user_missing";

export interface RefreshTokenReuse {
    status: "revoked_reuse";
    userId: string;
    familyRevokedCount: number;
}

export type ConsumeRefreshTokenResult =
    | ResolvedRefreshToken
    | RefreshTokenReuse
    | RefreshTokenError;

/**
 * Atomically consume a refresh token: verify it is active, then mark it revoked.
 * Uses an interactive transaction so concurrent refresh attempts can't both succeed.
 *
 * If the presented token is already revoked, treat the call as a reuse attempt
 * (evidence of theft) and revoke the user's entire active refresh-token family
 * inside the same transaction — siblings can't outlive the detection window.
 */
export async function consumeRefreshToken(
    token: string,
): Promise<ConsumeRefreshTokenResult> {
    return db.$transaction(async (tx) => {
        const record = await tx.refreshToken.findUnique({
            where: { token },
            select: {
                id: true,
                userId: true,
                expiresAt: true,
                revokedAt: true,
                user: { select: { email: true } },
            },
        });
        if (!record) return "not_found" as const;
        if (record.revokedAt) {
            const { count } = await tx.refreshToken.updateMany({
                where: { userId: record.userId, revokedAt: null },
                data: { revokedAt: new Date() },
            });
            return {
                status: "revoked_reuse" as const,
                userId: record.userId,
                familyRevokedCount: count,
            };
        }
        if (record.expiresAt.getTime() <= Date.now()) return "expired" as const;
        if (!record.user?.email) return "user_missing" as const;

        await tx.refreshToken.update({
            where: { id: record.id },
            data: { revokedAt: new Date() },
        });

        return {
            userId: record.userId,
            userEmail: record.user.email,
        };
    });
}

/** Revoke every active refresh token for the given user. Used on sign-out. */
export async function revokeAllRefreshTokens(userId: string): Promise<number> {
    const result = await db.refreshToken.updateMany({
        where: { userId, revokedAt: null },
        data: { revokedAt: new Date() },
    });
    return result.count;
}

/** Default grace window before a revoked token is purged from the table. */
export const REFRESH_TOKEN_CLEANUP_REVOKED_GRACE_DAYS = 7;

export interface CleanupExpiredRefreshTokensResult {
    deleted: number;
}

/**
 * Delete refresh tokens that are no longer useful: expired by TTL, or revoked
 * more than `revokedRetentionDays` ago. The grace window keeps recently-revoked
 * rows around long enough that the reuse-detection path in `consumeRefreshToken`
 * can still trip when a stolen token shows up shortly after sign-out.
 */
export async function cleanupExpiredRefreshTokens(
    revokedRetentionDays: number = REFRESH_TOKEN_CLEANUP_REVOKED_GRACE_DAYS,
): Promise<CleanupExpiredRefreshTokensResult> {
    const now = new Date();
    const revokedCutoff = new Date(
        now.getTime() - revokedRetentionDays * 24 * 60 * 60 * 1000,
    );
    const result = await db.refreshToken.deleteMany({
        where: {
            OR: [
                { expiresAt: { lt: now } },
                { revokedAt: { lt: revokedCutoff } },
            ],
        },
    });
    return { deleted: result.count };
}
