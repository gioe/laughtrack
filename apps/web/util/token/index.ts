import { randomBytes } from "crypto";
import jwt from "jsonwebtoken";
import { AuthToken } from "../../objects/interface";

/**
 * Resolve SECRET_KEY lazily, at call time rather than module load.
 *
 * Throwing at import time breaks `next build`: routes that transitively import
 * this module (e.g. /api/cron/cleanup-refresh-tokens via lib/auth/refreshTokens)
 * are evaluated during page-data collection, where SECRET_KEY is not set. The
 * secret is only ever needed when a token is actually signed or verified, so
 * defer the check until then.
 */
const getSecret = (): string => {
    const secret = process.env.SECRET_KEY;
    if (!secret) throw new Error("SECRET_KEY environment variable is not set");
    return secret;
};

/** Short-lived access token lifetime, in seconds. */
export const ACCESS_TOKEN_TTL_SECONDS = 15 * 60;

/** Long-lived refresh token lifetime, in seconds. */
export const REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60;

export const generateAccessToken = (payload: object): string => {
    return jwt.sign(payload, getSecret(), {
        expiresIn: ACCESS_TOKEN_TTL_SECONDS,
    });
};

/** Opaque 64-char hex refresh token. Stored verbatim in refresh_tokens.token. */
export const generateRefreshTokenString = (): string => {
    return randomBytes(32).toString("hex");
};

export const verifyToken = (token: string) => {
    return jwt.verify(token, getSecret()) as AuthToken;
};
