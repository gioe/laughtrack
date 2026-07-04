import { describe, it, expect } from "vitest";
import {
    PUBLIC_READ_CACHE_CONTROL,
    PRIVATE_READ_CACHE_CONTROL,
    NO_STORE_CACHE_CONTROL,
    PUBLIC_READ_SHARED_MAX_AGE,
    TIMEZONE_HEADER,
    publicReadCacheHeaders,
    personalizedReadCacheHeaders,
} from "./httpCache";
import { CACHE } from "@/util/constants/cacheConstants";

describe("httpCache policies", () => {
    it("public read is shared-cacheable with an s-maxage tied to CACHE.detailPage", () => {
        expect(PUBLIC_READ_SHARED_MAX_AGE).toBe(CACHE.detailPage);
        expect(PUBLIC_READ_CACHE_CONTROL).toContain("public");
        expect(PUBLIC_READ_CACHE_CONTROL).toContain(
            `s-maxage=${CACHE.detailPage}`,
        );
        expect(PUBLIC_READ_CACHE_CONTROL).toContain("max-age=60");
        expect(PUBLIC_READ_CACHE_CONTROL).toContain(
            `stale-while-revalidate=${CACHE.detailPage}`,
        );
        // A shared-cacheable public read must never be marked private.
        expect(PUBLIC_READ_CACHE_CONTROL).not.toContain("private");
    });

    it("private read is client-only (never shared) with a short TTL", () => {
        expect(PRIVATE_READ_CACHE_CONTROL).toContain("private");
        expect(PRIVATE_READ_CACHE_CONTROL).toContain("max-age=60");
        // Must not leak into a shared CDN cache.
        expect(PRIVATE_READ_CACHE_CONTROL).not.toContain("public");
        expect(PRIVATE_READ_CACHE_CONTROL).not.toContain("s-maxage");
    });

    it("no-store opts a user-scoped route out of every cache tier", () => {
        expect(NO_STORE_CACHE_CONTROL).toContain("no-store");
        expect(NO_STORE_CACHE_CONTROL).toContain("private");
        expect(NO_STORE_CACHE_CONTROL).not.toContain("public");
    });

    it("publicReadCacheHeaders omits Vary by default", () => {
        const headers = publicReadCacheHeaders();
        expect(headers["Cache-Control"]).toBe(PUBLIC_READ_CACHE_CONTROL);
        expect(headers["Vary"]).toBeUndefined();
    });

    it("publicReadCacheHeaders adds Vary: X-Timezone for timezone-varying routes", () => {
        const headers = publicReadCacheHeaders({ varyOnTimezone: true });
        expect(headers["Cache-Control"]).toBe(PUBLIC_READ_CACHE_CONTROL);
        expect(headers["Vary"]).toBe(TIMEZONE_HEADER);
        expect(headers["Vary"]).toBe("X-Timezone");
    });

    it("personalizedReadCacheHeaders: authed request is private (never shared), no Vary by default", () => {
        const headers = personalizedReadCacheHeaders({ authed: true });
        expect(headers["Cache-Control"]).toBe(PRIVATE_READ_CACHE_CONTROL);
        // Personalized responses must never carry a shared-cache directive.
        expect(headers["Cache-Control"]).not.toContain("public");
        expect(headers["Cache-Control"]).not.toContain("s-maxage");
        expect(headers["Vary"]).toBeUndefined();
    });

    it("personalizedReadCacheHeaders: anonymous request is shared-cacheable, Varying on Authorization + Cookie", () => {
        const headers = personalizedReadCacheHeaders({ authed: false });
        expect(headers["Cache-Control"]).toBe(PUBLIC_READ_CACHE_CONTROL);
        expect(headers["Cache-Control"]).toContain("s-maxage");
        // The invariant: the CDN keys the anonymous entry on the auth-bearing
        // headers so an authed request can never be served it.
        expect(headers["Vary"]).toBe("Authorization, Cookie");
    });

    it("personalizedReadCacheHeaders: anonymous + timezone appends X-Timezone to the Vary", () => {
        const headers = personalizedReadCacheHeaders({
            authed: false,
            varyOnTimezone: true,
        });
        expect(headers["Cache-Control"]).toBe(PUBLIC_READ_CACHE_CONTROL);
        expect(headers["Vary"]).toBe(`Authorization, Cookie, ${TIMEZONE_HEADER}`);
        expect(headers["Vary"]).toBe("Authorization, Cookie, X-Timezone");
    });

    it("personalizedReadCacheHeaders: authed + timezone stays private and Varies only on X-Timezone", () => {
        const headers = personalizedReadCacheHeaders({
            authed: true,
            varyOnTimezone: true,
        });
        expect(headers["Cache-Control"]).toBe(PRIVATE_READ_CACHE_CONTROL);
        expect(headers["Cache-Control"]).not.toContain("s-maxage");
        // A private response is not shared, so it does not Vary on auth headers —
        // only on the timezone that changes the client-cached body.
        expect(headers["Vary"]).toBe(TIMEZONE_HEADER);
    });
});
