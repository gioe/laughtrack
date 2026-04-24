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

export type RefreshTokenError =
    | "not_found"
    | "revoked"
    | "expired"
    | "user_missing";

/**
 * Atomically consume a refresh token: verify it is active, then mark it revoked.
 * Uses an interactive transaction so concurrent refresh attempts can't both succeed.
 */
export async function consumeRefreshToken(
    token: string,
): Promise<ResolvedRefreshToken | RefreshTokenError> {
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
        if (record.revokedAt) return "revoked" as const;
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
