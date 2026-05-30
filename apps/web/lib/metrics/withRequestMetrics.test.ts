import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { NextRequest } from "next/server";

// Capture every promise handed to waitUntil so tests can await the off-path
// write, and stub Prisma's raw executor so no real DB is touched.
const { scheduled, executeRawMock } = vi.hoisted(() => ({
    scheduled: [] as Promise<unknown>[],
    executeRawMock: vi.fn().mockResolvedValue(1),
}));

vi.mock("@vercel/functions", () => ({
    waitUntil: (promise: Promise<unknown>) => {
        scheduled.push(promise);
    },
}));

vi.mock("@/lib/db", () => ({
    db: { $executeRaw: executeRawMock },
    prisma: { $executeRaw: executeRawMock },
}));

import { withRequestMetrics } from "./withRequestMetrics";
import {
    normalizeRoutePattern,
    recordRequestMetric,
    startOfHour,
    toStatusClass,
} from "./requestMetrics";

/** Drain everything registered with waitUntil during the current test. */
async function flushScheduled() {
    await Promise.all(scheduled);
}

function fakeRequest(
    pathname: string,
    method = "GET",
): { method: string; nextUrl: { pathname: string }; url: string } {
    return {
        method,
        nextUrl: { pathname },
        url: `http://localhost${pathname}`,
    };
}

beforeEach(() => {
    scheduled.length = 0;
    executeRawMock.mockClear();
});

afterEach(() => {
    vi.useRealTimers();
});

describe("normalizeRoutePattern", () => {
    it("collapses a single dynamic segment to its [param] placeholder", () => {
        expect(
            normalizeRoutePattern("/api/v1/comedians/123", { id: "123" }),
        ).toBe("/api/v1/comedians/[id]");
    });

    it("collapses a named dynamic segment regardless of the resolved value", () => {
        expect(
            normalizeRoutePattern("/api/v1/comedian/nate-bargatze", {
                name: "nate-bargatze",
            }),
        ).toBe("/api/v1/comedian/[name]");
    });

    it("leaves a static path untouched when there are no params", () => {
        expect(normalizeRoutePattern("/api/health")).toBe("/api/health");
        expect(normalizeRoutePattern("/api/health", {})).toBe("/api/health");
    });

    it("anchors substitution to whole segments, not substrings", () => {
        // The literal "12" must not be rewritten inside the static "/v12/" segment.
        expect(normalizeRoutePattern("/api/v12/items/12", { id: "12" })).toBe(
            "/api/v12/items/[id]",
        );
    });

    it("collapses catch-all segments to [...param]", () => {
        expect(
            normalizeRoutePattern("/api/files/a/b/c", { path: ["a", "b", "c"] }),
        ).toBe("/api/files/[...path]");
    });
});

describe("toStatusClass", () => {
    it.each([
        [200, "2xx"],
        [201, "2xx"],
        [301, "3xx"],
        [404, "4xx"],
        [429, "4xx"],
        [500, "5xx"],
        [503, "5xx"],
    ])("maps %i to %s", (status, expected) => {
        expect(toStatusClass(status)).toBe(expected);
    });

    it("falls back to 5xx for out-of-range codes", () => {
        expect(toStatusClass(0)).toBe("5xx");
        expect(toStatusClass(999)).toBe("5xx");
    });
});

describe("startOfHour", () => {
    it("truncates minutes, seconds, and millis in UTC", () => {
        const bucket = startOfHour(new Date("2026-05-30T14:37:42.512Z"));
        expect(bucket.toISOString()).toBe("2026-05-30T14:00:00.000Z");
    });
});

describe("recordRequestMetric", () => {
    it("issues an UPSERT that increments count and sets updated_at = NOW()", async () => {
        await recordRequestMetric({
            routePattern: "/api/v1/comedians/[id]",
            method: "GET",
            status: 200,
            now: new Date("2026-05-30T14:37:00.000Z"),
        });

        expect(executeRawMock).toHaveBeenCalledTimes(1);
        const [strings, ...values] = executeRawMock.mock.calls[0];
        const sql = (strings as string[]).join("?");

        // Bucketed UPSERT keyed on the composite PK, incrementing the counter.
        expect(sql).toContain("INSERT INTO api_request_metrics");
        expect(sql).toContain(
            "ON CONFLICT (route_pattern, method, status_class, hour_bucket)",
        );
        expect(sql).toContain("count = api_request_metrics.count + 1");
        // @updatedAt does not fire on raw SQL — must be set explicitly.
        expect(sql).toContain("updated_at = NOW()");

        // Bound parameters: routePattern, method, statusClass, hourBucket.
        expect(values[0]).toBe("/api/v1/comedians/[id]");
        expect(values[1]).toBe("GET");
        expect(values[2]).toBe("2xx");
        expect((values[3] as Date).toISOString()).toBe(
            "2026-05-30T14:00:00.000Z",
        );
    });
});

describe("withRequestMetrics", () => {
    it("returns the handler's response unchanged", async () => {
        const handler = withRequestMetrics(async (_req: NextRequest) =>
            Response.json({ ok: true }, { status: 200 }),
        );

        const res = await handler(fakeRequest("/api/health") as never);

        expect(res.status).toBe(200);
        await expect(res.json()).resolves.toEqual({ ok: true });
    });

    it("records the route pattern, method, and status class for a dynamic route", async () => {
        const handler = withRequestMetrics(
            async (_req: NextRequest, _ctx?: unknown) =>
                new Response(null, { status: 200 }),
        );

        await handler(fakeRequest("/api/v1/comedians/123") as never, {
            params: Promise.resolve({ id: "123" }),
        });
        await flushScheduled();

        expect(executeRawMock).toHaveBeenCalledTimes(1);
        const values = executeRawMock.mock.calls[0].slice(1);
        expect(values[0]).toBe("/api/v1/comedians/[id]");
        expect(values[1]).toBe("GET");
        expect(values[2]).toBe("2xx");
    });

    it("records the method from the request", async () => {
        const handler = withRequestMetrics(
            async (_req: NextRequest) => new Response(null, { status: 201 }),
        );

        await handler(fakeRequest("/api/admin/clubs", "POST") as never);
        await flushScheduled();

        const values = executeRawMock.mock.calls[0].slice(1);
        expect(values[0]).toBe("/api/admin/clubs");
        expect(values[1]).toBe("POST");
        expect(values[2]).toBe("2xx");
    });

    it("records the error status class when the handler returns a non-2xx response", async () => {
        const handler = withRequestMetrics(
            async (_req: NextRequest, _ctx?: unknown) =>
                new Response(null, { status: 404 }),
        );

        await handler(fakeRequest("/api/v1/comedians/999") as never, {
            params: Promise.resolve({ id: "999" }),
        });
        await flushScheduled();

        const values = executeRawMock.mock.calls[0].slice(1);
        expect(values[0]).toBe("/api/v1/comedians/[id]");
        expect(values[2]).toBe("4xx");
    });

    it("records a 5xx and re-throws when the handler throws", async () => {
        const boom = new Error("handler exploded");
        const handler = withRequestMetrics(async (_req: NextRequest) => {
            throw boom;
        });

        await expect(
            handler(fakeRequest("/api/health") as never),
        ).rejects.toThrow(boom);
        await flushScheduled();

        const values = executeRawMock.mock.calls[0].slice(1);
        expect(values[0]).toBe("/api/health");
        expect(values[2]).toBe("5xx");
    });

    it("never lets a recording failure surface to the caller", async () => {
        executeRawMock.mockRejectedValueOnce(new Error("db down"));
        const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

        const handler = withRequestMetrics(
            async (_req: NextRequest) => new Response(null, { status: 200 }),
        );

        const res = await handler(fakeRequest("/api/health") as never);
        expect(res.status).toBe(200);
        await flushScheduled();

        expect(errorSpy).toHaveBeenCalled();
        errorSpy.mockRestore();
    });
});
