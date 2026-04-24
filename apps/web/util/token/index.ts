import { randomBytes } from "crypto";
import jwt from "jsonwebtoken";
import { AuthToken } from "../../objects/interface";

const secret = process.env.SECRET_KEY;
if (!secret) throw new Error("SECRET_KEY environment variable is not set");

/** Short-lived access token lifetime, in seconds. */
export const ACCESS_TOKEN_TTL_SECONDS = 15 * 60;

/** Long-lived refresh token lifetime, in seconds. */
export const REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60;

export const generateAccessToken = (payload: object): string => {
    return jwt.sign(payload, secret, {
        expiresIn: ACCESS_TOKEN_TTL_SECONDS,
    });
};

/** Opaque 64-char hex refresh token. Stored verbatim in refresh_tokens.token. */
export const generateRefreshTokenString = (): string => {
    return randomBytes(32).toString("hex");
};

export const verifyToken = (token: string) => {
    return jwt.verify(token, secret) as AuthToken;
};
