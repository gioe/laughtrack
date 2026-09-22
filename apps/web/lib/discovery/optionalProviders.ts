export type OptionalProviderStatus =
    | "success"
    | "error"
    | "timeout"
    | "skipped";

/**
 * Bound optional work per server process, coalescing only while it is in flight.
 * Keys must include every input (including identity) that changes the result,
 * and a given key must always identify the same result type.
 */
export function createOptionalProviderRunner({ maxInFlight = 64 } = {}) {
    if (!Number.isInteger(maxInFlight) || maxInFlight < 1) {
        throw new RangeError("maxInFlight must be a positive integer");
    }
    type Outcome = { ok: true; value: unknown } | { ok: false };
    type Subscriber = (outcome: Outcome) => void;
    const inFlight = new Map<string, Set<Subscriber>>();

    return function run<T>(
        key: string,
        load: () => Promise<T>,
        fallback: T,
        deadlineMs: number,
        onOutcome?: (status: OptionalProviderStatus) => void,
    ): Promise<T> {
        const report = (status: OptionalProviderStatus) => {
            try {
                // A caller may provide an async callback despite the void type.
                // Telemetry failures must never affect results or become unhandled.
                void Promise.resolve(onOutcome?.(status)).catch(() => {});
            } catch {
                // Reporting is best effort.
            }
        };
        const remainingMs = deadlineMs - Date.now();
        if (remainingMs <= 0) {
            report("timeout");
            return Promise.resolve(fallback);
        }

        let subscribers = inFlight.get(key);
        if (!subscribers) {
            if (inFlight.size >= maxInFlight) {
                report("skipped");
                return Promise.resolve(fallback);
            }
            subscribers = new Set<Subscriber>();
            inFlight.set(key, subscribers);
            const listeners = subscribers;
            const settle = (outcome: Outcome) => {
                inFlight.delete(key);
                listeners.forEach((listener) => listener(outcome));
                listeners.clear();
            };
            // Start in a microtask so synchronous loader throws are also observed.
            // Attach one settlement handler per load, not one per caller: expired
            // callers must not be retained forever by a hung provider promise.
            void Promise.resolve()
                .then(load)
                .then(
                    (value) => settle({ ok: true, value }),
                    () => settle({ ok: false }),
                );
        }

        const listeners = subscribers;
        return new Promise<T>((resolve) => {
            let settled = false;
            const finish = (value: T, status: OptionalProviderStatus) => {
                if (settled) return;
                settled = true;
                clearTimeout(timer);
                listeners.delete(onSettlement);
                report(status);
                resolve(value);
            };
            const onSettlement: Subscriber = (outcome) => {
                if (Date.now() >= deadlineMs) {
                    finish(fallback, "timeout");
                } else if (outcome.ok) {
                    finish(outcome.value as T, "success");
                } else {
                    finish(fallback, "error");
                }
            };
            const timer = setTimeout(
                () => finish(fallback, "timeout"),
                remainingMs,
            );
            listeners.add(onSettlement);
            // Timeout removes this caller's listener, but retains the load's slot
            // until actual settlement. Late rejections are still observed above.
        });
    };
}

export const runOptionalProvider = createOptionalProviderRunner();
