import { describe, expect, it, vi } from "vitest";
import {
    getMissingStartupEnv,
    MissingStartupEnvError,
    validateWebStartupEnv,
} from "./startup";

const VALID_ENV = {
    DATABASE_URL: "postgresql://example",
    AUTH_SECRET: "auth-secret",
    AUTH_GOOGLE_ID: "google-id",
    AUTH_GOOGLE_SECRET: "google-secret",
};

describe("startup env validation", () => {
    it("passes when required canonical env vars are present", () => {
        expect(getMissingStartupEnv(VALID_ENV)).toEqual([]);
    });

    it("accepts supported legacy aliases", () => {
        expect(
            getMissingStartupEnv({
                DATABASE_URL: "postgresql://example",
                NEXTAUTH_SECRET: "nextauth-secret",
                GOOGLE_CLIENT_ID: "google-client-id",
                GOOGLE_CLIENT_SECRET: "google-client-secret",
            }),
        ).toEqual([]);
    });

    it("throws a distinguishable startup error and logs missing config", () => {
        const logger = { error: vi.fn() };

        expect(() =>
            validateWebStartupEnv({
                env: {
                    DATABASE_URL: "postgresql://example",
                    AUTH_GOOGLE_SECRET: "google-secret",
                },
                logger,
            }),
        ).toThrow(MissingStartupEnvError);

        expect(logger.error).toHaveBeenCalledWith(
            "Missing required web startup environment variables: AUTH_SECRET or NEXTAUTH_SECRET, AUTH_GOOGLE_ID or GOOGLE_CLIENT_ID",
        );
    });

    it("skips validation in fixture mode outside Vercel production", () => {
        const logger = { error: vi.fn() };

        expect(() =>
            validateWebStartupEnv({
                env: { E2E_FIXTURE_MODE: "1" },
                logger,
            }),
        ).not.toThrow();
        expect(logger.error).not.toHaveBeenCalled();
    });

    it("still validates in Vercel production even if fixture mode leaks in", () => {
        const logger = { error: vi.fn() };

        expect(() =>
            validateWebStartupEnv({
                env: { E2E_FIXTURE_MODE: "1", VERCEL_ENV: "production" },
                logger,
            }),
        ).toThrow(MissingStartupEnvError);
    });
});
