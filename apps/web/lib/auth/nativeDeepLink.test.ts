import { describe, it, expect } from "vitest";
import {
    buildNativeAuthErrorDeepLink,
    isNativeAuthProvider,
    NATIVE_AUTH_DEEP_LINK,
} from "./nativeDeepLink";

describe("buildNativeAuthErrorDeepLink", () => {
    it("builds a canonical deep link for a known provider and error code", () => {
        expect(buildNativeAuthErrorDeepLink("google", "OAuthCallback")).toBe(
            "laughtrack://auth/callback?provider=google&error=OAuthCallback",
        );
        expect(buildNativeAuthErrorDeepLink("apple", "AccessDenied")).toBe(
            "laughtrack://auth/callback?provider=apple&error=AccessDenied",
        );
    });

    it("returns null for an unknown or missing provider", () => {
        expect(
            buildNativeAuthErrorDeepLink("evil", "OAuthCallback"),
        ).toBeNull();
        expect(buildNativeAuthErrorDeepLink(null, "OAuthCallback")).toBeNull();
        expect(
            buildNativeAuthErrorDeepLink(undefined, "OAuthCallback"),
        ).toBeNull();
    });

    it("strips non-alphanumeric characters from the error code", () => {
        expect(
            buildNativeAuthErrorDeepLink(
                "google",
                "OAuth Callback?x=1#frag/../evil",
            ),
        ).toBe(
            "laughtrack://auth/callback?provider=google&error=OAuthCallbackx1fragevil",
        );
    });

    it("falls back to signin_failed when the error code is empty or all stripped", () => {
        expect(buildNativeAuthErrorDeepLink("google", "")).toBe(
            "laughtrack://auth/callback?provider=google&error=signin_failed",
        );
        expect(buildNativeAuthErrorDeepLink("google", null)).toBe(
            "laughtrack://auth/callback?provider=google&error=signin_failed",
        );
        expect(buildNativeAuthErrorDeepLink("google", "!!!")).toBe(
            "laughtrack://auth/callback?provider=google&error=signin_failed",
        );
    });

    it("caps the error code length at 64 characters", () => {
        const longError = "A".repeat(200);
        const url = new URL(
            buildNativeAuthErrorDeepLink("google", longError) as string,
        );
        expect(url.searchParams.get("error")).toHaveLength(64);
    });

    it("never points the deep link at a foreign scheme/host/path", () => {
        const url = new URL(
            buildNativeAuthErrorDeepLink("google", "OAuthCallback") as string,
        );
        expect(`${url.protocol}//${url.host}${url.pathname}`).toBe(
            NATIVE_AUTH_DEEP_LINK,
        );
    });
});

describe("isNativeAuthProvider", () => {
    it("accepts the three known providers and rejects everything else", () => {
        expect(isNativeAuthProvider("google")).toBe(true);
        expect(isNativeAuthProvider("apple")).toBe(true);
        expect(isNativeAuthProvider("email")).toBe(true);
        expect(isNativeAuthProvider("github")).toBe(false);
        expect(isNativeAuthProvider(null)).toBe(false);
        expect(isNativeAuthProvider(undefined)).toBe(false);
    });
});
