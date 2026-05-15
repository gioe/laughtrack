import { afterEach, describe, expect, it } from "vitest";
import { appleProviderConfig, googleProviderConfig } from "./providerConfig";

const ORIGINAL_ENV = { ...process.env };

afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
});

describe("auth provider config", () => {
    it("reads canonical Auth.js Google env vars", () => {
        process.env.AUTH_GOOGLE_ID = "auth-google-id";
        process.env.AUTH_GOOGLE_SECRET = "auth-google-secret";

        expect(googleProviderConfig()).toEqual({
            clientId: "auth-google-id",
            clientSecret: "auth-google-secret",
        });
    });

    it("falls back to legacy Google env names", () => {
        delete process.env.AUTH_GOOGLE_ID;
        delete process.env.AUTH_GOOGLE_SECRET;
        process.env.GOOGLE_CLIENT_ID = "legacy-google-id";
        process.env.GOOGLE_CLIENT_SECRET = "legacy-google-secret";

        expect(googleProviderConfig()).toEqual({
            clientId: "legacy-google-id",
            clientSecret: "legacy-google-secret",
        });
    });

    it("reads canonical Auth.js Apple env vars", () => {
        process.env.AUTH_APPLE_ID = "auth-apple-id";
        process.env.AUTH_APPLE_SECRET = "auth-apple-secret";

        expect(appleProviderConfig()).toEqual({
            clientId: "auth-apple-id",
            clientSecret: "auth-apple-secret",
        });
    });

    it("falls back to legacy Apple env names", () => {
        delete process.env.AUTH_APPLE_ID;
        delete process.env.AUTH_APPLE_SECRET;
        process.env.APPLE_CLIENT_ID = "legacy-apple-id";
        process.env.APPLE_CLIENT_SECRET = "legacy-apple-secret";

        expect(appleProviderConfig()).toEqual({
            clientId: "legacy-apple-id",
            clientSecret: "legacy-apple-secret",
        });
    });
});
