import { NextRequest, NextResponse } from "next/server";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitResponse,
} from "@/lib/rateLimit";
import { sanitizeAuthError } from "@/lib/auth/authErrorLogging";
import { withRequestMetrics } from "@/lib/metrics";
import {
    NATIVE_AUTH_DEEP_LINK,
    NATIVE_AUTH_PROVIDERS,
} from "@/lib/auth/nativeDeepLink";

// The redirect base is hard-coded — `deep_link` / `callbackUrl` query params
// are ignored entirely so an attacker cannot smuggle a foreign host, extra
// query params, a fragment, or userinfo into the token-bearing redirect.
const CANONICAL_DEEP_LINK = NATIVE_AUTH_DEEP_LINK;
const ALLOWED_PROVIDERS = NATIVE_AUTH_PROVIDERS;

function safeProvider(raw: string | null): string | null {
    return raw && ALLOWED_PROVIDERS.has(raw) ? raw : null;
}

// The native app mints a per-flow CSRF nonce in buildSignInUrl and verifies it
// on the returned deep link. We only round-trip it — never trust it — so it is
// reduced to the app's base64url alphabet and bounded, matching the
// "nothing arbitrary rides into the app" rule the rest of this route follows.
function safeState(raw: string | null): string | null {
    if (!raw) return null;
    const cleaned = raw.replace(/[^A-Za-z0-9_-]/g, "").slice(0, 128);
    return cleaned || null;
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

function logNativeAuthCallbackError(details: Record<string, unknown>) {
    console.error(
        "Native auth callback error",
        JSON.stringify(sanitizeAuthError(details)),
    );
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
export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const rl = await checkRateLimit(
        `auth-native-callback:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    // Round-tripped back to the app on every redirect so it can match the
    // pending per-flow nonce (login-CSRF / session-fixation guard).
    const state = safeState(req.nextUrl.searchParams.get("state"));

    const provider = safeProvider(req.nextUrl.searchParams.get("provider"));
    if (!provider) {
        return NextResponse.redirect(
            buildCallbackURL({
                state,
                error: "unsupported_provider",
            }),
        );
    }

    const oauthError = req.nextUrl.searchParams.get("error");

    if (oauthError) {
        return NextResponse.redirect(
            buildCallbackURL({
                provider,
                state,
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
            const responseBody = await readDiagnosticResponseBody(response);
            logNativeAuthCallbackError({
                provider,
                stage: "token_exchange_response",
                status: response.status,
                responseBody,
            });
            return NextResponse.redirect(
                buildCallbackURL({
                    provider,
                    state,
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
            logNativeAuthCallbackError({
                provider,
                stage: "token_exchange_missing_token",
                responseKeys: Object.keys(body),
            });
            return NextResponse.redirect(
                buildCallbackURL({
                    provider,
                    state,
                    error: "missing_token",
                }),
            );
        }

        return NextResponse.redirect(
            buildCallbackURL({
                provider,
                state,
                accessToken: body.accessToken,
                refreshToken: body.refreshToken,
                expiresIn: body.expiresIn?.toString(),
            }),
        );
    } catch (error) {
        logNativeAuthCallbackError({
            provider,
            stage: "token_exchange_exception",
            error,
        });
        return NextResponse.redirect(
            buildCallbackURL({
                provider,
                state,
                error: "token_exchange_failed",
            }),
        );
    }
});

async function readDiagnosticResponseBody(response: Response) {
    const contentType = response.headers.get("content-type") ?? "";
    try {
        if (contentType.includes("application/json")) {
            return await response.json();
        }
        const text = await response.text();
        return text ? { text } : null;
    } catch (error) {
        return {
            readError: sanitizeAuthError(error),
        };
    }
}
