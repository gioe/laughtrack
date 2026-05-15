import { NextRequest, NextResponse } from "next/server";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitResponse,
} from "@/lib/rateLimit";

// The redirect base is hard-coded — `deep_link` / `callbackUrl` query params
// are ignored entirely so an attacker cannot smuggle a foreign host, extra
// query params, a fragment, or userinfo into the token-bearing redirect.
const CANONICAL_DEEP_LINK = "laughtrack://auth/callback";
const ALLOWED_PROVIDERS = new Set(["apple", "google", "email"]);

function safeProvider(raw: string | null): string | null {
    return raw && ALLOWED_PROVIDERS.has(raw) ? raw : null;
}

function buildCallbackURL(params: Record<string, string | null | undefined>) {
    const url = new URL(CANONICAL_DEEP_LINK);

    Object.entries(params).forEach(([key, value]) => {
        if (value) {
            url.searchParams.set(key, value);
        }
    });

    return url;
}

/**
 * GET /api/v1/auth/native/callback
 *
 * Final hop for native iOS auth. Apple/Google complete OAuth here, and email
 * reuses the existing NextAuth magic-link provider instead of adding a new
 * password credential surface. In every case, this route exchanges the
 * authenticated NextAuth session for the same mobile access + refresh token
 * pair, then redirects back into the app's URL scheme.
 */
export async function GET(req: NextRequest) {
    const rl = await checkRateLimit(
        `auth-native-callback:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    const provider = safeProvider(req.nextUrl.searchParams.get("provider"));
    if (!provider) {
        return NextResponse.redirect(
            buildCallbackURL({
                error: "unsupported_provider",
            }),
        );
    }

    const oauthError = req.nextUrl.searchParams.get("error");

    if (oauthError) {
        return NextResponse.redirect(
            buildCallbackURL({
                provider,
                error: oauthError,
            }),
        );
    }

    try {
        const response = await fetch(
            `${req.nextUrl.origin}/api/v1/auth/token`,
            {
                method: "POST",
                headers: {
                    cookie: req.headers.get("cookie") ?? "",
                    origin: req.nextUrl.origin,
                },
                cache: "no-store",
            },
        );

        if (!response.ok) {
            return NextResponse.redirect(
                buildCallbackURL({
                    provider,
                    error: `token_exchange_failed_${response.status}`,
                }),
            );
        }

        const body = (await response.json()) as {
            accessToken?: string;
            refreshToken?: string;
            expiresIn?: number;
        };
        if (!body.accessToken || !body.refreshToken) {
            return NextResponse.redirect(
                buildCallbackURL({
                    provider,
                    error: "missing_token",
                }),
            );
        }

        return NextResponse.redirect(
            buildCallbackURL({
                provider,
                accessToken: body.accessToken,
                refreshToken: body.refreshToken,
                expiresIn: body.expiresIn?.toString(),
            }),
        );
    } catch {
        return NextResponse.redirect(
            buildCallbackURL({
                provider,
                error: "token_exchange_failed",
            }),
        );
    }
}
