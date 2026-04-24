import { NextRequest, NextResponse } from "next/server";

const IOS_CALLBACK_URL = "laughtrack://auth/callback";

function buildCallbackURL(params: Record<string, string | null | undefined>) {
    const url = new URL(IOS_CALLBACK_URL);

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
    const provider = req.nextUrl.searchParams.get("provider");
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
