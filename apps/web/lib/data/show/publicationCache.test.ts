import { beforeEach, expect, it, vi } from "vitest";
const { query, cache } = vi.hoisted(() => ({
    query: vi.fn(),
    cache: vi.fn((fn: any, _keys: string[], _options?: unknown) => fn),
}));
vi.mock("@/lib/db", () => ({ db: { $queryRaw: query } }));
vi.mock("next/cache", () => ({ unstable_cache: cache, unstable_noStore: vi.fn() }));
import { publicationCache } from "./publicationCache";
beforeEach(() => {
    vi.clearAllMocks();
});
it("changes the cache key after worker suppression and forwards arguments", async () => {
    query
        .mockResolvedValueOnce([{ revision: BigInt(1) }])
        .mockResolvedValueOnce([{ revision: BigInt(2) }]);
    const fn = vi.fn(async (id: number) => id);
    const read = publicationCache(fn, ["shows"], { revalidate: 3600 });
    expect(await read(42)).toBe(42);
    expect(await read(43)).toBe(43);
    expect(cache.mock.calls.map((c) => c[1])).toEqual([
        ["shows", "publication:1"],
        ["shows", "publication:2"],
    ]);
    expect(query).toHaveBeenCalledTimes(2);
});
it("does not serve cached data when the authoritative revision is unavailable", async () => {
    query.mockResolvedValue([]);
    const read = publicationCache(async () => "cached");
    await expect(read()).rejects.toThrow(/unavailable/);
    expect(cache).not.toHaveBeenCalled();
});
