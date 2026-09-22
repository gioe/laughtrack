import { describe, expect, it, vi } from "vitest";
import {
    createTouringHistoryCache,
    type TouringHistorySnapshot,
} from "./touringHistoryCache";

const now = new Date("2026-09-22T12:00:00Z");
const request = {
    zipCode: "10001",
    radiusMiles: 25,
    nearbyZips: ["10001", "10002"],
    now,
};
function snapshot(
    overrides: Partial<TouringHistorySnapshot> = {},
): TouringHistorySnapshot {
    return {
        asOf: now,
        nextShowAt: null,
        historyCoverageStart: new Date("2024-01-01T00:00:00Z"),
        historyCoverageShowCount: 10,
        totals: [
            {
                canonical_comedian_id: 1,
                prior_local_appearance_count: 2,
                last_local_appearance_at: "2025-01-01T00:00:00Z",
            },
        ],
        ...overrides,
    };
}
function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: Error) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return { promise, resolve, reject };
}

describe("touring history cache", () => {
    it("reuses equivalent ZIP sets but isolates requested market, radius, actual ZIP coverage and version", async () => {
        const cache = createTouringHistoryCache();
        const load = vi.fn(async () => snapshot());
        const first = await cache.get(request, load);
        expect(
            await cache.get(
                { ...request, nearbyZips: ["10002", "10001", "10001"] },
                load,
            ),
        ).toBe(first);
        expect(load).toHaveBeenCalledTimes(1);
        for (const changed of [
            { zipCode: "10002" },
            { radiusMiles: 5 },
            { nearbyZips: ["10001"] },
            { version: 2 },
        ])
            await cache.get({ ...request, ...changed }, load);
        expect(load).toHaveBeenCalledTimes(5);
        await cache.get({ ...request, radiusMiles: undefined }, load);
        await cache.get({ ...request, radiusMiles: 0 }, load);
        expect(load).toHaveBeenCalledTimes(6);
    });

    it("expires from load start and never caches a load that already exhausted its TTL", async () => {
        let clock = 0;
        const cache = createTouringHistoryCache({
            ttlMs: 100,
            clock: () => clock,
        });
        const load = vi.fn(async () => snapshot());
        await cache.get(request, load);
        clock = 99;
        await cache.get(request, load);
        expect(load).toHaveBeenCalledTimes(1);
        clock = 100;
        await cache.get(request, load);
        expect(load).toHaveBeenCalledTimes(2);
        cache.clear();
        const slow = deferred<TouringHistorySnapshot>();
        const pending = cache.get(request, () => slow.promise);
        clock = 200;
        slow.resolve(snapshot());
        expect(await pending).toBeNull();
        await cache.get(request, load);
        expect(load).toHaveBeenCalledTimes(3);
    });

    it("refreshes on historical clock rollback and when a local show enters history", async () => {
        const cache = createTouringHistoryCache();
        const nextShowAt = new Date(now.getTime() + 1000);
        const load = vi.fn(async () => snapshot({ nextShowAt }));
        await cache.get(request, load);
        await cache.get({ ...request, now: nextShowAt }, load);
        expect(load).toHaveBeenCalledTimes(1); // strict history date < request.now
        const after = new Date(nextShowAt.getTime() + 1);
        const refresh = vi.fn(async () =>
            snapshot({ asOf: after, nextShowAt: null }),
        );
        await cache.get({ ...request, now: after }, refresh);
        expect(refresh).toHaveBeenCalledTimes(1);
        const rollback = vi.fn(async () => snapshot());
        await cache.get(request, rollback);
        expect(rollback).toHaveBeenCalledTimes(1);
    });

    it("coalesces compatible in-flight requests while bounding distinct loads and refusing earlier clocks", async () => {
        const cache = createTouringHistoryCache({ maxInFlight: 1 });
        const result = deferred<TouringHistorySnapshot>();
        const load = vi.fn(() => result.promise);
        const first = cache.get(request, load);
        const second = cache.get(request, load);
        const later = cache.get(
            { ...request, now: new Date(now.getTime() + 1) },
            load,
        );
        const earlier = cache.get(
            { ...request, now: new Date(now.getTime() - 1) },
            load,
        );
        expect(
            await cache.get({ ...request, zipCode: "10002" }, load),
        ).toBeNull();
        expect(load).toHaveBeenCalledTimes(1);
        result.resolve(snapshot());
        expect(await first).toEqual(snapshot());
        expect(await second).toEqual(snapshot());
        expect(await later).toEqual(snapshot());
        expect(await earlier).toBeNull();
        const otherLoad = vi.fn(async () => snapshot());
        await cache.get({ ...request, zipCode: "10002" }, otherLoad);
        expect(otherLoad).toHaveBeenCalledTimes(1);
    });

    it("consumes asynchronous and synchronous failures and releases slots for retry", async () => {
        const cache = createTouringHistoryCache({ maxInFlight: 1 });
        const failed = deferred<TouringHistorySnapshot>();
        const result = cache.get(request, () => failed.promise);
        failed.reject(new Error("database unavailable"));
        expect(await result).toBeNull();
        expect(
            await cache.get(request, () => {
                throw new Error("sync failure");
            }),
        ).toBeNull();
        const load = vi.fn(async () => snapshot());
        expect(await cache.get(request, load)).toEqual(snapshot());
        expect(load).toHaveBeenCalledTimes(1);
    });

    it("evicts the least recently used market when entry capacity is reached", async () => {
        const cache = createTouringHistoryCache({ maxEntries: 2 });
        const load = vi.fn(async () => snapshot());
        const second = { ...request, zipCode: "10002" };
        const third = { ...request, zipCode: "10003" };
        await cache.get(request, load);
        await cache.get(second, load);
        await cache.get(request, load); // keep first hot
        await cache.get(third, load);
        await cache.get(request, load);
        expect(load).toHaveBeenCalledTimes(3);
        await cache.get(second, load);
        expect(load).toHaveBeenCalledTimes(4);
    });

    it("bounds aggregate row storage including market coverage and rejects oversized snapshots", async () => {
        const cache = createTouringHistoryCache({ maxRows: 3 });
        const load = vi.fn(async () => snapshot()); // two rows including market coverage
        await cache.get(request, load);
        await cache.get({ ...request, zipCode: "10002" }, load);
        await cache.get(request, load);
        expect(load).toHaveBeenCalledTimes(3);
        cache.clear();
        const huge = vi.fn(async () =>
            snapshot({
                totals: Array.from({ length: 3 }, () => snapshot().totals[0]),
            }),
        );
        expect(await cache.get(request, huge)).toBeNull();
        expect(await cache.get(request, huge)).toBeNull();
        expect(huge).toHaveBeenCalledTimes(2);
    });

    it("clearing cannot let an older load repopulate cache or exceed active query capacity", async () => {
        const cache = createTouringHistoryCache({ maxInFlight: 1 });
        const old = deferred<TouringHistorySnapshot>();
        const pending = cache.get(request, () => old.promise);
        cache.clear();
        const load = vi.fn(async () => snapshot());
        expect(
            await cache.get({ ...request, zipCode: "10002" }, load),
        ).toBeNull();
        expect(load).not.toHaveBeenCalled();
        old.resolve(snapshot());
        expect(await pending).toBeNull();
        await cache.get(request, load);
        expect(load).toHaveBeenCalledTimes(1);
    });

    it("rejects invalid request clocks and snapshots from the future without retaining them", async () => {
        const cache = createTouringHistoryCache();
        const load = vi.fn(async () =>
            snapshot({ asOf: new Date(now.getTime() + 1) }),
        );
        expect(
            await cache.get({ ...request, now: new Date(NaN) }, load),
        ).toBeNull();
        expect(load).not.toHaveBeenCalled();
        expect(await cache.get(request, load)).toBeNull();
        expect(await cache.get(request, load)).toBeNull();
        expect(load).toHaveBeenCalledTimes(2);
    });
});
