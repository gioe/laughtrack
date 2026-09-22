/** Historical evidence only: all current show and performer eligibility stays live. */
export interface TouringHistorySnapshot {
    asOf: Date;
    nextShowAt: Date | null;
    historyCoverageStart: Date | null;
    historyCoverageShowCount: number;
    totals: {
        canonical_comedian_id: number;
        prior_local_appearance_count: number;
        last_local_appearance_at: string | null;
    }[];
}

interface Request {
    zipCode: string;
    radiusMiles?: number;
    nearbyZips: readonly string[];
    now: Date;
    version?: number;
}

interface CacheOptions {
    ttlMs?: number;
    maxEntries?: number;
    maxRows?: number;
    maxInFlight?: number;
    clock?: () => number;
}

export function createTouringHistoryCache({
    ttlMs = 5 * 60 * 1_000,
    maxEntries = 64,
    maxRows = 50_000,
    maxInFlight = 8,
    clock = Date.now,
}: CacheOptions = {}) {
    const entries = new Map<
        string,
        { snapshot: TouringHistorySnapshot; expires: number; rows: number }
    >();
    const inFlight = new Map<
        string,
        { now: number; promise: Promise<TouringHistorySnapshot | null> }
    >();
    let rowCount = 0;
    let generation = 0;
    const remove = (key: string) => {
        rowCount -= entries.get(key)?.rows ?? 0;
        entries.delete(key);
    };
    const usable = (snapshot: TouringHistorySnapshot, now: number) =>
        snapshot.asOf.getTime() <= now &&
        (snapshot.nextShowAt === null || snapshot.nextShowAt.getTime() >= now);

    return {
        async get(
            request: Request,
            load: () => Promise<TouringHistorySnapshot>,
        ): Promise<TouringHistorySnapshot | null> {
            const now = request.now.getTime();
            if (!Number.isFinite(now)) return null;
            const key = JSON.stringify([
                request.version ?? 1,
                request.zipCode,
                request.radiusMiles ?? 0,
                [...new Set(request.nearbyZips)].sort(),
            ]);
            const startedAt = clock();
            for (const [storedKey, entry] of entries) {
                if (entry.expires <= startedAt) remove(storedKey);
            }
            const existing = entries.get(key);
            if (existing && usable(existing.snapshot, now)) {
                entries.delete(key);
                entries.set(key, existing);
                return existing.snapshot;
            }
            const pending = inFlight.get(key);
            if (pending)
                return pending.promise.then((snapshot) =>
                    snapshot && usable(snapshot, now) ? snapshot : null,
                );
            if (inFlight.size >= maxInFlight) return null;
            const loadGeneration = generation;
            // Defer load so synchronous throws are consumed and the slot is installed first.
            const promise = Promise.resolve()
                .then(load)
                .then((snapshot) => {
                    const rows = snapshot.totals.length + 1; // includes market coverage
                    if (
                        generation !== loadGeneration ||
                        clock() >= startedAt + ttlMs ||
                        !usable(snapshot, now) ||
                        rows > maxRows ||
                        maxEntries < 1
                    )
                        return null;
                    remove(key);
                    while (
                        entries.size >= maxEntries ||
                        rowCount + rows > maxRows
                    ) {
                        const oldest = entries.keys().next().value;
                        if (oldest === undefined) break;
                        remove(oldest);
                    }
                    entries.set(key, {
                        snapshot,
                        expires: startedAt + ttlMs,
                        rows,
                    });
                    rowCount += rows;
                    return snapshot;
                })
                .catch(() => null)
                .finally(() => {
                    if (inFlight.get(key)?.promise === promise)
                        inFlight.delete(key);
                });
            inFlight.set(key, { now, promise });
            return promise;
        },
        clear() {
            entries.clear();
            rowCount = 0;
            generation++;
            // Keep live slots accounted for until their actual database work settles.
        },
    };
}

export const touringHistoryCache = createTouringHistoryCache();
