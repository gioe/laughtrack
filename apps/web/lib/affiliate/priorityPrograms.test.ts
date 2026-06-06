import { afterEach, describe, expect, it, vi } from "vitest";
import {
    PRIORITY_AFFILIATE_PROVIDERS,
    affiliateRulesFromEnv,
    getPriorityAffiliatePrograms,
} from "./affiliateRouting";

const ORIGINAL_ENV = { ...process.env };

afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllEnvs();
});

describe("priority affiliate program configuration", () => {
    it("lists the 10 priority programs with launch metadata and safe defaults", () => {
        const programs = getPriorityAffiliatePrograms();

        expect(programs.map((program) => program.provider)).toEqual(
            PRIORITY_AFFILIATE_PROVIDERS,
        );
        expect(programs).toHaveLength(10);
        expect(
            programs.every(
                (program) =>
                    program.networkName &&
                    program.envVars.length > 0 &&
                    program.launchStatus,
            ),
        ).toBe(true);
    });

    it("does not activate any priority program when credentials are absent", () => {
        for (const key of Object.keys(process.env)) {
            if (key.includes("AFFILIATE")) {
                vi.stubEnv(key, "");
            }
        }

        expect(affiliateRulesFromEnv()).toEqual({});
    });

    it("activates configured programs from environment variables", () => {
        vi.stubEnv("TICKETMASTER_AFFILIATE_CAMEFROM", "CFC_LAUGHTRACK");
        vi.stubEnv("VIATOR_AFFILIATE_PID", "P12345");
        vi.stubEnv("VIATOR_AFFILIATE_MCID", "M67890");
        vi.stubEnv(
            "SEATGEEK_AFFILIATE_REDIRECT_BASE_URL",
            "https://seatgeek.test/track",
        );

        expect(Object.keys(affiliateRulesFromEnv()).sort()).toEqual([
            "seatgeek",
            "ticketmaster",
            "viator",
        ]);
    });
});
