/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useInfiniteSearch } from "./useInfiniteSearch";

type IOCallback = (
    entries: IntersectionObserverEntry[],
    observer: IntersectionObserver,
) => void;

let capturedIOCallback: IOCallback | null = null;
const mockObserve = vi.fn();
const mockDisconnect = vi.fn();
const mockFetch = vi.fn();

function makeMockObserver(cb: IOCallback) {
    capturedIOCallback = cb;
    return {
        observe: mockObserve,
        disconnect: mockDisconnect,
        unobserve: vi.fn(),
    };
}

beforeEach(() => {
    capturedIOCallback = null;
    vi.clearAllMocks();
    vi.stubGlobal("IntersectionObserver", makeMockObserver);
    vi.stubGlobal("fetch", mockFetch);
});

afterEach(() => {
    vi.unstubAllGlobals();
});

function makeJsonResponse(data: unknown[], total: number) {
    return {
        ok: true,
        json: async () => ({ data, total }),
    };
}

describe("useInfiniteSearch", () => {
    describe("initial render", () => {
        it("returns initialData without fetching on mount", () => {
            const initialData = [{ id: 1 }, { id: 2 }];

            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: { q: "comedy" },
                    initialData,
                    initialTotal: 2,
                }),
            );

            expect(result.current.data).toEqual(initialData);
            expect(result.current.total).toBe(2);
            expect(result.current.isLoading).toBe(false);
            expect(mockFetch).not.toHaveBeenCalled();
        });

        it("sets hasMore=false when initialData length equals initialTotal", () => {
            const initialData = [{ id: 1 }, { id: 2 }];

            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData,
                    initialTotal: 2,
                }),
            );

            expect(result.current.hasMore).toBe(false);
        });

        it("sets hasMore=true when initialData length is less than initialTotal", () => {
            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData: [{ id: 1 }],
                    initialTotal: 10,
                }),
            );

            expect(result.current.hasMore).toBe(true);
        });
    });

    describe("param change", () => {
        it("resets accumulated results and re-fetches from page 0 when params change", async () => {
            mockFetch.mockResolvedValue(makeJsonResponse([{ id: 99 }], 5));

            const { result, rerender } = renderHook(
                ({ params }: { params: Record<string, string> }) =>
                    useInfiniteSearch({
                        endpoint: "/api/search",
                        params,
                        initialData: [{ id: 1 }, { id: 2 }],
                        initialTotal: 10,
                    }),
                { initialProps: { params: { q: "comedy" } } },
            );

            expect(mockFetch).not.toHaveBeenCalled();

            await act(async () => {
                rerender({ params: { q: "improv" } });
            });

            expect(mockFetch).toHaveBeenCalledOnce();
            const url: string = mockFetch.mock.calls[0][0] as string;
            expect(url).toContain("page=0");

            await waitFor(() => {
                expect(result.current.data).toEqual([{ id: 99 }]);
            });
        });

        it("does not re-fetch when params reference changes but values are identical", () => {
            const { rerender } = renderHook(
                ({ params }: { params: Record<string, string> }) =>
                    useInfiniteSearch({
                        endpoint: "/api/search",
                        params,
                        initialData: [],
                        initialTotal: 0,
                    }),
                { initialProps: { params: { q: "comedy" } } },
            );

            act(() => {
                rerender({ params: { q: "comedy" } }); // same values, new object reference
            });

            expect(mockFetch).not.toHaveBeenCalled();
        });
    });

    describe("IntersectionObserver / loadMore", () => {
        it("triggers loadMore when sentinel enters the viewport and appends results", async () => {
            const page1Data = [{ id: 3 }, { id: 4 }];
            mockFetch.mockResolvedValue(makeJsonResponse(page1Data, 4));

            const initialData = [{ id: 1 }, { id: 2 }];
            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData,
                    initialTotal: 4,
                }),
            );

            const sentinel = document.createElement("div");
            act(() => {
                result.current.sentinelRef(sentinel);
            });

            expect(mockObserve).toHaveBeenCalledWith(sentinel);

            await act(async () => {
                capturedIOCallback!(
                    [{ isIntersecting: true } as IntersectionObserverEntry],
                    {} as IntersectionObserver,
                );
            });

            await waitFor(() => {
                expect(result.current.data).toEqual([
                    ...initialData,
                    ...page1Data,
                ]);
            });

            expect(mockFetch).toHaveBeenCalledOnce();
            const url: string = mockFetch.mock.calls[0][0] as string;
            expect(url).toContain("page=1");
        });

        it("does not call fetch when sentinel is not intersecting", async () => {
            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData: [],
                    initialTotal: 10,
                }),
            );

            const sentinel = document.createElement("div");
            act(() => {
                result.current.sentinelRef(sentinel);
            });

            act(() => {
                capturedIOCallback!(
                    [{ isIntersecting: false } as IntersectionObserverEntry],
                    {} as IntersectionObserver,
                );
            });

            expect(mockFetch).not.toHaveBeenCalled();
        });

        it("disconnects the previous observer when sentinelRef is called again", () => {
            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData: [],
                    initialTotal: 0,
                }),
            );

            const sentinel1 = document.createElement("div");
            const sentinel2 = document.createElement("div");

            act(() => {
                result.current.sentinelRef(sentinel1);
            });
            act(() => {
                result.current.sentinelRef(sentinel2);
            });

            expect(mockDisconnect).toHaveBeenCalledOnce();
        });
    });

    describe("hasMore", () => {
        it("sets hasMore=false when loaded count reaches total", async () => {
            // initialData has 2 items, page 1 has 1 item, total is 3 → 2+1=3 >= 3
            mockFetch.mockResolvedValue(makeJsonResponse([{ id: 3 }], 3));

            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData: [{ id: 1 }, { id: 2 }],
                    initialTotal: 3,
                }),
            );

            expect(result.current.hasMore).toBe(true);

            const sentinel = document.createElement("div");
            act(() => {
                result.current.sentinelRef(sentinel);
            });

            await act(async () => {
                capturedIOCallback!(
                    [{ isIntersecting: true } as IntersectionObserverEntry],
                    {} as IntersectionObserver,
                );
            });

            await waitFor(() => {
                expect(result.current.hasMore).toBe(false);
            });

            expect(result.current.data).toHaveLength(3);
        });

        it("keeps hasMore=true when more items remain after a page load", async () => {
            // initialData has 2, page 1 has 2, total is 10 → 4 < 10
            mockFetch.mockResolvedValue(
                makeJsonResponse([{ id: 3 }, { id: 4 }], 10),
            );

            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData: [{ id: 1 }, { id: 2 }],
                    initialTotal: 10,
                }),
            );

            const sentinel = document.createElement("div");
            act(() => {
                result.current.sentinelRef(sentinel);
            });

            await act(async () => {
                capturedIOCallback!(
                    [{ isIntersecting: true } as IntersectionObserverEntry],
                    {} as IntersectionObserver,
                );
            });

            await waitFor(() => {
                expect(result.current.data).toHaveLength(4);
            });

            expect(result.current.hasMore).toBe(true);
        });
    });
});
