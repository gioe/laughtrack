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
        const logger = { error: vi.fn(), warn: vi.fn() };

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

    it("does not require Google OAuth vars in development mode", () => {
        expect(
            getMissingStartupEnv({
                NODE_ENV: "development",
                DATABASE_URL: "postgresql://example",
                AUTH_SECRET: "auth-secret",
            }),
        ).toEqual([]);
    });

    it("warns (without throwing) when OAuth vars are absent in development", () => {
        const logger = { error: vi.fn(), warn: vi.fn() };

        expect(() =>
            validateWebStartupEnv({
                env: {
                    NODE_ENV: "development",
                    DATABASE_URL: "postgresql://example",
                    AUTH_SECRET: "auth-secret",
                },
                logger,
            }),
        ).not.toThrow();

        expect(logger.error).not.toHaveBeenCalled();
        expect(logger.warn).toHaveBeenCalledWith(
            "OAuth env vars missing (AUTH_GOOGLE_ID or GOOGLE_CLIENT_ID, AUTH_GOOGLE_SECRET or GOOGLE_CLIENT_SECRET) — sign-in is disabled in this dev server. Production startup still requires them.",
        );
    });

    it("does not warn in development when OAuth vars are present", () => {
        const logger = { error: vi.fn(), warn: vi.fn() };

        expect(() =>
            validateWebStartupEnv({
                env: { NODE_ENV: "development", ...VALID_ENV },
                logger,
            }),
        ).not.toThrow();

        expect(logger.warn).not.toHaveBeenCalled();
    });

    it("still requires DATABASE_URL and AUTH_SECRET in development mode", () => {
        expect(getMissingStartupEnv({ NODE_ENV: "development" })).toEqual([
            "DATABASE_URL",
            "AUTH_SECRET or NEXTAUTH_SECRET",
        ]);
    });

    it("requires Google OAuth vars when NODE_ENV is production", () => {
        expect(
            getMissingStartupEnv({
                NODE_ENV: "production",
                DATABASE_URL: "postgresql://example",
                AUTH_SECRET: "auth-secret",
            }),
        ).toEqual([
            "AUTH_GOOGLE_ID or GOOGLE_CLIENT_ID",
            "AUTH_GOOGLE_SECRET or GOOGLE_CLIENT_SECRET",
        ]);
    });

    it("requires Google OAuth vars when NODE_ENV is unset (fail closed)", () => {
        expect(
            getMissingStartupEnv({
                DATABASE_URL: "postgresql://example",
                AUTH_SECRET: "auth-secret",
            }),
        ).toEqual([
            "AUTH_GOOGLE_ID or GOOGLE_CLIENT_ID",
            "AUTH_GOOGLE_SECRET or GOOGLE_CLIENT_SECRET",
        ]);
    });

    it("skips validation in fixture mode outside Vercel production", () => {
        const logger = { error: vi.fn(), warn: vi.fn() };

        expect(() =>
            validateWebStartupEnv({
                env: { E2E_FIXTURE_MODE: "1" },
                logger,
            }),
        ).not.toThrow();
        expect(logger.error).not.toHaveBeenCalled();
    });

    it("still validates in Vercel production even if fixture mode leaks in", () => {
        const logger = { error: vi.fn(), warn: vi.fn() };

        expect(() =>
            validateWebStartupEnv({
                env: { E2E_FIXTURE_MODE: "1", VERCEL_ENV: "production" },
                logger,
            }),
        ).toThrow(MissingStartupEnvError);
    });
});
