import { describe, it, expect } from "vitest";
import { NextRequest } from "next/server";
import { isValidTimezone, readTimezoneHeader } from "./timezoneHeader";

function makeRequest(headers: Record<string, string> = {}): NextRequest {
    return new NextRequest("http://localhost/test", { headers });
}

describe("isValidTimezone", () => {
    it("accepts canonical IANA zones", () => {
        expect(isValidTimezone("America/New_York")).toBe(true);
        expect(isValidTimezone("America/Los_Angeles")).toBe(true);
        expect(isValidTimezone("Europe/London")).toBe(true);
        expect(isValidTimezone("Asia/Tokyo")).toBe(true);
        expect(isValidTimezone("UTC")).toBe(true);
    });

    it("rejects malformed zone identifiers", () => {
        expect(isValidTimezone("Not/Real")).toBe(false);
        expect(isValidTimezone("America/Atlantis")).toBe(false);
        expect(isValidTimezone("garbage")).toBe(false);
        expect(isValidTimezone("")).toBe(false);
    });
});

describe("readTimezoneHeader", () => {
    it("defaults to UTC when the X-Timezone header is absent", () => {
        const result = readTimezoneHeader(makeRequest());
        expect(result).toEqual({ ok: true, timezone: "UTC" });
    });

    it("returns the validated timezone when the header is a real IANA zone", () => {
        const result = readTimezoneHeader(
            makeRequest({ "X-Timezone": "America/Chicago" }),
        );
        expect(result).toEqual({ ok: true, timezone: "America/Chicago" });
    });

    it("rejects an invalid IANA value with an actionable error message", () => {
        const result = readTimezoneHeader(
            makeRequest({ "X-Timezone": "Not/Real" }),
        );
        expect(result.ok).toBe(false);
        if (!result.ok) {
            expect(result.error).toMatch(/X-Timezone/);
            expect(result.error).toMatch(/IANA/);
        }
    });

    it("rejects an empty header value rather than treating it as 'absent'", () => {
        // fetch's Headers preserves an empty-string send as "" (not null), so an
        // empty header reaches the route as a present-but-invalid value.
        const result = readTimezoneHeader(makeRequest({ "X-Timezone": "" }));
        expect(result.ok).toBe(false);
    });
});
