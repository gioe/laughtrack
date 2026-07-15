import { describe, expect, it } from "vitest";
import { buildReviewCallbackUrl } from "./review-access";

describe("buildReviewCallbackUrl", () => {
    it("returns tokens to the native app with the original CSRF state", () => {
        const callback = buildReviewCallbackUrl(
            "https://laugh-track.com/api/v1/auth/native/callback?provider=email&state=state_123",
            {
                accessToken: "access.jwt",
                refreshToken: "refresh-token",
                expiresIn: 900,
            },
        );
        const url = new URL(callback);

        expect(url.protocol).toBe("laughtrack:");
        expect(url.host).toBe("auth");
        expect(url.pathname).toBe("/callback");
        expect(url.searchParams.get("provider")).toBe("email");
        expect(url.searchParams.get("state")).toBe("state_123");
        expect(url.searchParams.get("accessToken")).toBe("access.jwt");
        expect(url.searchParams.get("refreshToken")).toBe("refresh-token");
        expect(url.searchParams.get("expiresIn")).toBe("900");
    });

    it("refuses to build a callback without native state", () => {
        expect(() =>
            buildReviewCallbackUrl(
                "https://laugh-track.com/api/v1/auth/native/callback?provider=email",
                {
                    accessToken: "access.jwt",
                    refreshToken: "refresh-token",
                    expiresIn: 900,
                },
            ),
        ).toThrow("missing state");
    });
});
