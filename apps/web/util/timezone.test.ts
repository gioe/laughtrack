import { describe, it, expect, vi } from "vitest";
import { NextRequest } from "next/server";
import {
    isValidTimezone,
    readTimezoneCookie,
    readTimezoneHeader,
} from "./timezone";

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

describe("readTimezoneCookie", () => {
    it("returns UTC when the cookie is undefined", () => {
        expect(readTimezoneCookie(undefined)).toBe("UTC");
    });

    it("returns UTC for an empty string without warning", () => {
        // cookieStore.get('timezone')?.value can plausibly produce '' under
        // edge cases — treat it the same as 'absent' rather than a corrupted
        // value worth logging.
        const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
        try {
            expect(readTimezoneCookie("")).toBe("UTC");
            expect(warn).not.toHaveBeenCalled();
        } finally {
            warn.mockRestore();
        }
    });

    it("returns the cookie value when it is a real IANA zone", () => {
        expect(readTimezoneCookie("America/Chicago")).toBe("America/Chicago");
    });

    it("falls back to UTC and warns when the cookie is invalid", () => {
        const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
        try {
            expect(readTimezoneCookie("Not/Real")).toBe("UTC");
            expect(warn).toHaveBeenCalledTimes(1);
            const message = warn.mock.calls[0][0];
            expect(message).toMatch(/timezone/);
            expect(message).toMatch(/Not\/Real/);
        } finally {
            warn.mockRestore();
        }
    });
});
