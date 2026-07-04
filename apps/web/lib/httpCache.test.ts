import { describe, it, expect } from "vitest";
import {
    PUBLIC_READ_CACHE_CONTROL,
    PRIVATE_READ_CACHE_CONTROL,
    NO_STORE_CACHE_CONTROL,
    PUBLIC_READ_SHARED_MAX_AGE,
    TIMEZONE_HEADER,
    publicReadCacheHeaders,
    privateReadCacheHeaders,
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

    it("privateReadCacheHeaders carries only the private Cache-Control", () => {
        const headers = privateReadCacheHeaders();
        expect(headers["Cache-Control"]).toBe(PRIVATE_READ_CACHE_CONTROL);
        expect(headers["Vary"]).toBeUndefined();
    });
});
