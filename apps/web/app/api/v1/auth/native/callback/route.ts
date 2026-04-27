import { NextRequest, NextResponse } from "next/server";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitResponse,
} from "@/lib/rateLimit";

const CANONICAL_DEEP_LINK = "laughtrack://auth/callback";
const ALLOWED_PROVIDERS = new Set(["apple", "google"]);

function safeProvider(raw: string | null): string | null {
    return raw && ALLOWED_PROVIDERS.has(raw) ? raw : null;
}

// Restricts the redirect base to the exact canonical host+path so an
// attacker-supplied laughtrack://other-host cannot exfiltrate the token.
function resolveDeepLinkBase(req: NextRequest): URL {
    const raw =
        req.nextUrl.searchParams.get("deep_link") ??
        req.nextUrl.searchParams.get("callbackUrl");
    if (raw) {
        try {
            const candidate = new URL(raw);
            if (
                candidate.protocol === "laughtrack:" &&
                candidate.host === "auth" &&
                candidate.pathname === "/callback"
            ) {
                return candidate;
            }
        } catch {
            // malformed URL — fall through to canonical
        }
    }
    return new URL(CANONICAL_DEEP_LINK);
}

function buildCallbackURL(
    base: URL,
    params: Record<string, string | null | undefined>,
) {
    const url = new URL(base.toString());

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
 * Final hop for native iOS OAuth. NextAuth redirects here after Apple/Google
 * sign-in; this route exchanges the authenticated session for a JWT through
 * /api/v1/auth/token, then redirects back into the app's URL scheme.
 */
export async function GET(req: NextRequest) {
    const rl = await checkRateLimit(
        `auth-native-callback:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    const base = resolveDeepLinkBase(req);
    const provider = safeProvider(req.nextUrl.searchParams.get("provider"));
    const oauthError = req.nextUrl.searchParams.get("error");

    if (oauthError) {
        return NextResponse.redirect(
            buildCallbackURL(base, {
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
                buildCallbackURL(base, {
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
                buildCallbackURL(base, {
                    provider,
                    error: "missing_token",
                }),
            );
        }

        return NextResponse.redirect(
            buildCallbackURL(base, {
                provider,
                accessToken: body.accessToken,
                refreshToken: body.refreshToken,
                expiresIn: body.expiresIn?.toString(),
            }),
        );
    } catch {
        return NextResponse.redirect(
            buildCallbackURL(base, {
                provider,
                error: "token_exchange_failed",
            }),
        );
    }
}
