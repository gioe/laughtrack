import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createOptionalProviderRunner } from "./optionalProviders";

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: Error) => void;
    const promise = new Promise<T>((yes, no) => {
        resolve = yes;
        reject = no;
    });
    return { promise, resolve, reject };
}

describe("optional providers", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-09-22T15:00:00Z"));
    });
    afterEach(() => vi.useRealTimers());

    it("returns fast results and clears their deadline timers without caching results", async () => {
        const run = createOptionalProviderRunner();
        const load = vi
            .fn()
            .mockResolvedValueOnce(["first"])
            .mockResolvedValueOnce(["second"]);
        expect(
            await run("podcast:anonymous", load, [], Date.now() + 100),
        ).toEqual(["first"]);
        expect(vi.getTimerCount()).toBe(0);
        expect(
            await run("podcast:anonymous", load, [], Date.now() + 100),
        ).toEqual(["second"]);
        expect(load).toHaveBeenCalledTimes(2);
        expect(vi.getTimerCount()).toBe(0);
    });

    it("returns fallback at the absolute deadline and ignores late results", async () => {
        const run = createOptionalProviderRunner();
        const work = deferred<string[]>();
        const fallback: string[] = [];
        const result = run(
            "slow",
            () => work.promise,
            fallback,
            Date.now() + 100,
        );
        await vi.advanceTimersByTimeAsync(100);
        expect(await result).toBe(fallback);
        work.resolve(["late"]);
        await Promise.resolve();
        expect(await result).toEqual([]);
        expect(fallback).toEqual([]);
        expect(vi.getTimerCount()).toBe(0);
    });

    it("coalesces timed-out work while giving each caller its own deadline", async () => {
        const run = createOptionalProviderRunner();
        const work = deferred<string>();
        const load = vi.fn(() => work.promise);
        const first = run("same", load, "first fallback", Date.now() + 100);
        const second = run("same", load, "second fallback", Date.now() + 300);
        await vi.advanceTimersByTimeAsync(100);
        expect(await first).toBe("first fallback");
        const third = run("same", load, "third fallback", Date.now() + 100);
        await vi.advanceTimersByTimeAsync(100);
        expect(await third).toBe("third fallback");
        expect(load).toHaveBeenCalledTimes(1);
        work.resolve("ready");
        expect(await second).toBe("ready");
        expect(vi.getTimerCount()).toBe(0);
    });

    it("cleans up repeated caller deadlines while retaining one hung load", async () => {
        const run = createOptionalProviderRunner();
        const work = deferred<string>();
        const load = vi.fn(() => work.promise);
        for (let index = 0; index < 20; index++) {
            const result = run("hung", load, "expired", Date.now() + 10);
            await vi.advanceTimersByTimeAsync(10);
            expect(await result).toBe("expired");
            expect(vi.getTimerCount()).toBe(0);
        }
        const live = run("hung", load, "fallback", Date.now() + 100);
        work.resolve("recovered");
        expect(await live).toBe("recovered");
        expect(load).toHaveBeenCalledTimes(1);
        expect(vi.getTimerCount()).toBe(0);
    });

    it("keeps distinct identities isolated", async () => {
        const run = createOptionalProviderRunner();
        const first = deferred<string>();
        const second = deferred<string>();
        const a = run(
            "provider:profile-a",
            () => first.promise,
            "",
            Date.now() + 100,
        );
        const b = run(
            "provider:profile-b",
            () => second.promise,
            "",
            Date.now() + 100,
        );
        first.resolve("a");
        second.resolve("b");
        expect(await a).toBe("a");
        expect(await b).toBe("b");
    });

    it("bounds outstanding work after timeout and frees capacity only on settlement", async () => {
        const run = createOptionalProviderRunner({ maxInFlight: 1 });
        const work = deferred<string>();
        const blocked = vi.fn().mockResolvedValue("next");
        const first = run(
            "stuck",
            () => work.promise,
            "fallback",
            Date.now() + 100,
        );
        await vi.advanceTimersByTimeAsync(100);
        expect(await first).toBe("fallback");
        expect(await run("new", blocked, "busy", Date.now() + 100)).toBe(
            "busy",
        );
        expect(blocked).not.toHaveBeenCalled();
        work.resolve("late");
        await Promise.resolve();
        await Promise.resolve();
        expect(await run("new", blocked, "busy", Date.now() + 100)).toBe(
            "next",
        );
        expect(blocked).toHaveBeenCalledTimes(1);
    });

    it("observes late rejections and releases their capacity", async () => {
        const run = createOptionalProviderRunner({ maxInFlight: 1 });
        const work = deferred<string>();
        const result = run(
            "rejects",
            () => work.promise,
            "fallback",
            Date.now() + 100,
        );
        await vi.advanceTimersByTimeAsync(100);
        expect(await result).toBe("fallback");
        work.reject(new Error("late failure"));
        await vi.advanceTimersByTimeAsync(0);
        expect(
            await run(
                "next",
                async () => "ready",
                "fallback",
                Date.now() + 100,
            ),
        ).toBe("ready");
        expect(vi.getTimerCount()).toBe(0);
    });

    it("returns fallback for synchronous throws and immediate rejections", async () => {
        const run = createOptionalProviderRunner({ maxInFlight: 1 });
        expect(
            await run(
                "sync",
                () => {
                    throw new Error("sync");
                },
                "fallback",
                Date.now() + 100,
            ),
        ).toBe("fallback");
        expect(
            await run(
                "async",
                async () => {
                    throw new Error("async");
                },
                "fallback",
                Date.now() + 100,
            ),
        ).toBe("fallback");
        expect(vi.getTimerCount()).toBe(0);
    });

    it("does not start work after the request deadline has elapsed", async () => {
        const run = createOptionalProviderRunner();
        const load = vi.fn().mockResolvedValue("unexpected");
        expect(await run("expired", load, "fallback", Date.now())).toBe(
            "fallback",
        );
        expect(load).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });
});

describe("optional provider outcome reporting", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-09-22T15:00:00Z"));
    });
    afterEach(() => vi.useRealTimers());

    it("reports successful null results as success", async () => {
        const report = vi.fn();
        const run = createOptionalProviderRunner();
        expect(
            await run(
                "empty",
                async () => null,
                null,
                Date.now() + 100,
                report,
            ),
        ).toBeNull();
        expect(report.mock.calls).toEqual([["success"]]);
    });

    it("reports errors separately for every coalesced caller", async () => {
        const run = createOptionalProviderRunner();
        const work = deferred<string>();
        const load = vi.fn(() => work.promise);
        const firstReport = vi.fn();
        const secondReport = vi.fn();
        const first = run("same", load, "first", Date.now() + 100, firstReport);
        const second = run(
            "same",
            load,
            "second",
            Date.now() + 100,
            secondReport,
        );
        await Promise.resolve();
        work.reject(new Error("provider failed"));
        expect(await first).toBe("first");
        expect(await second).toBe("second");
        expect(load).toHaveBeenCalledTimes(1);
        expect(firstReport.mock.calls).toEqual([["error"]]);
        expect(secondReport.mock.calls).toEqual([["error"]]);
    });

    it("reports synchronous loader throws as errors", async () => {
        const report = vi.fn();
        const run = createOptionalProviderRunner();
        expect(
            await run(
                "throws",
                () => {
                    throw new Error("sync");
                },
                "fallback",
                Date.now() + 100,
                report,
            ),
        ).toBe("fallback");
        expect(report.mock.calls).toEqual([["error"]]);
    });

    it("reports expired deadlines without starting loaders", async () => {
        const report = vi.fn();
        const load = vi.fn();
        const run = createOptionalProviderRunner();
        await run("expired", load, null, Date.now(), report);
        expect(report.mock.calls).toEqual([["timeout"]]);
        expect(load).not.toHaveBeenCalled();
    });

    it("reports capacity refusal as skipped", async () => {
        const run = createOptionalProviderRunner({ maxInFlight: 1 });
        const work = deferred<string>();
        const firstReport = vi.fn();
        const report = vi.fn();
        const load = vi.fn();
        const first = run(
            "busy",
            () => work.promise,
            "fallback",
            Date.now() + 100,
            firstReport,
        );
        await run("new", load, null, Date.now() + 100, report);
        expect(report.mock.calls).toEqual([["skipped"]]);
        expect(load).not.toHaveBeenCalled();
        work.resolve("done");
        expect(await first).toBe("done");
        expect(firstReport.mock.calls).toEqual([["success"]]);
    });

    it.each(["resolve", "reject"] as const)(
        "reports one timeout despite late %s",
        async (settlement) => {
            const run = createOptionalProviderRunner();
            const work = deferred<string>();
            const report = vi.fn();
            const result = run(
                "slow",
                () => work.promise,
                "fallback",
                Date.now() + 100,
                report,
            );
            await vi.advanceTimersByTimeAsync(100);
            expect(await result).toBe("fallback");
            if (settlement === "resolve") work.resolve("late");
            else work.reject(new Error("late"));
            await vi.advanceTimersByTimeAsync(0);
            expect(report.mock.calls).toEqual([["timeout"]]);
        },
    );

    it.each(["resolve", "reject"] as const)(
        "reports settlement after deadline as timeout even before the timer runs: %s",
        async (settlement) => {
            const run = createOptionalProviderRunner();
            const work = deferred<string>();
            const report = vi.fn();
            const result = run(
                "late",
                () => work.promise,
                "fallback",
                Date.now() + 100,
                report,
            );
            await Promise.resolve();
            vi.setSystemTime(Date.now() + 100);
            if (settlement === "resolve") work.resolve("late");
            else work.reject(new Error("late"));
            expect(await result).toBe("fallback");
            expect(report.mock.calls).toEqual([["timeout"]]);
            expect(vi.getTimerCount()).toBe(0);
        },
    );

    it("isolates throwing and rejecting reporters from shared results", async () => {
        const run = createOptionalProviderRunner();
        const work = deferred<string>();
        const first = run(
            "same",
            () => work.promise,
            "fallback",
            Date.now() + 100,
            () => {
                throw new Error("reporter");
            },
        );
        const second = run(
            "same",
            () => work.promise,
            "fallback",
            Date.now() + 100,
            async () => {
                throw new Error("async reporter");
            },
        );
        work.resolve("ready");
        expect(await first).toBe("ready");
        expect(await second).toBe("ready");
        await vi.advanceTimersByTimeAsync(0);
        expect(vi.getTimerCount()).toBe(0);
    });
});
