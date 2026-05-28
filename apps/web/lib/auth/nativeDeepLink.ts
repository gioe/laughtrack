// Canonical native deep link target for the iOS app's ASWebAuthenticationSession.
// Hard-coded and never built from user input — neither the token-bearing success
// redirect (app/api/v1/auth/native/callback) nor the OAuth-error bounce
// (ui/components/modals/login) may point it at a foreign scheme/host/path.
export const NATIVE_AUTH_DEEP_LINK = "laughtrack://auth/callback";

export const NATIVE_AUTH_PROVIDERS = new Set(["apple", "google", "email"]);

// Client-readable marker the login form drops just before redirecting to a
// social provider on a native attempt. The home page reads it to decide whether
// an OAuth handshake error should bounce back into the app instead of stranding
// the auth sheet on the web error page. Not httpOnly (the client must read it)
// and non-sensitive (only the provider name).
export const NATIVE_AUTH_MARKER_COOKIE = "lt_native_auth";

export function isNativeAuthProvider(
    raw: string | null | undefined,
): raw is "apple" | "google" | "email" {
    return !!raw && NATIVE_AUTH_PROVIDERS.has(raw);
}

// Builds laughtrack://auth/callback?provider=<p>&error=<code> so an OAuth
// handshake failure can be handed back to the iOS app (which only intercepts
// the laughtrack:// scheme). Returns null when the provider isn't a known
// native provider. The error code is reduced to a bounded charset so nothing
// arbitrary rides into the app through the deep link.
export function buildNativeAuthErrorDeepLink(
    provider: string | null | undefined,
    error: string | null | undefined,
): string | null {
    if (!isNativeAuthProvider(provider)) return null;

    const url = new URL(NATIVE_AUTH_DEEP_LINK);
    url.searchParams.set("provider", provider);
    const safeError = (error ?? "").replace(/[^A-Za-z0-9_]/g, "").slice(0, 64);
    url.searchParams.set("error", safeError || "signin_failed");
    return url.toString();
}
