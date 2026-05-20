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

    it("ignores legacy Google env names", () => {
        delete process.env.AUTH_GOOGLE_ID;
        delete process.env.AUTH_GOOGLE_SECRET;
        process.env.GOOGLE_CLIENT_ID = "legacy-google-id";
        process.env.GOOGLE_CLIENT_SECRET = "legacy-google-secret";
        process.env.GOOGLE_ID = "legacy-google-id-alt";
        process.env.GOOGLE_SECRET = "legacy-google-secret-alt";

        expect(googleProviderConfig()).toEqual({
            clientId: undefined,
            clientSecret: undefined,
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

    it("ignores legacy Apple env names", () => {
        delete process.env.AUTH_APPLE_ID;
        delete process.env.AUTH_APPLE_SECRET;
        process.env.APPLE_CLIENT_ID = "legacy-apple-id";
        process.env.APPLE_CLIENT_SECRET = "legacy-apple-secret";
        process.env.APPLE_ID = "legacy-apple-id-alt";
        process.env.APPLE_SECRET = "legacy-apple-secret-alt";

        expect(appleProviderConfig()).toEqual({
            clientId: undefined,
            clientSecret: undefined,
        });
    });
});
