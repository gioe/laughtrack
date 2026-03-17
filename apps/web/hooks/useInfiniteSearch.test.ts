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

/** Fires the captured IntersectionObserver callback — fails fast if sentinelRef was never called. */
function fireIO(isIntersecting: boolean) {
    if (!capturedIOCallback) {
        throw new Error(
            "IO callback not captured — did you call result.current.sentinelRef(el)?",
        );
    }
    capturedIOCallback(
        [{ isIntersecting } as IntersectionObserverEntry],
        {} as IntersectionObserver,
    );
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
                fireIO(true);
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

        it("passes an AbortSignal to fetch", async () => {
            mockFetch.mockResolvedValue(makeJsonResponse([], 0));

            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData: [],
                    initialTotal: 5,
                }),
            );

            const sentinel = document.createElement("div");
            act(() => {
                result.current.sentinelRef(sentinel);
            });

            await act(async () => {
                fireIO(true);
            });

            await waitFor(() => {
                expect(mockFetch).toHaveBeenCalledOnce();
            });

            const fetchOptions = mockFetch.mock.calls[0][1] as RequestInit;
            expect(fetchOptions.signal).toBeInstanceOf(AbortSignal);
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
                fireIO(false);
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

        it("sets isLoading=true while fetch is in-flight and false after completion", async () => {
            let resolveFirstFetch!: (val: unknown) => void;
            const firstFetchPromise = new Promise(
                (resolve) => (resolveFirstFetch = resolve),
            );
            mockFetch.mockReturnValueOnce(firstFetchPromise);

            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData: [],
                    initialTotal: 5,
                }),
            );

            const sentinel = document.createElement("div");
            act(() => {
                result.current.sentinelRef(sentinel);
            });

            // Fire the observer — loadMore sets isLoading synchronously before the first await
            act(() => {
                fireIO(true);
            });

            expect(result.current.isLoading).toBe(true);

            // Resolve the fetch
            await act(async () => {
                resolveFirstFetch(makeJsonResponse([{ id: 1 }], 1));
            });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });
        });
    });

    describe("error handling", () => {
        it("sets isError=true and errorMessage when fetch returns a non-ok response", async () => {
            mockFetch.mockResolvedValue({ ok: false, status: 500 });

            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData: [],
                    initialTotal: 5,
                }),
            );

            const sentinel = document.createElement("div");
            act(() => {
                result.current.sentinelRef(sentinel);
            });

            await act(async () => {
                fireIO(true);
            });

            await waitFor(() => {
                expect(result.current.isError).toBe(true);
            });

            expect(result.current.errorMessage).toBe("500");
            expect(result.current.isLoading).toBe(false);
        });

        it("sets isError=true and errorMessage when fetch throws a network error", async () => {
            mockFetch.mockRejectedValue(new Error("Network failure"));

            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData: [],
                    initialTotal: 5,
                }),
            );

            const sentinel = document.createElement("div");
            act(() => {
                result.current.sentinelRef(sentinel);
            });

            await act(async () => {
                fireIO(true);
            });

            await waitFor(() => {
                expect(result.current.isError).toBe(true);
            });

            expect(result.current.errorMessage).toBe("Network failure");
            expect(result.current.isLoading).toBe(false);
        });

        it("retry() re-fires loadMore and clears isError on success", async () => {
            mockFetch
                .mockRejectedValueOnce(new Error("Network failure"))
                .mockResolvedValueOnce(makeJsonResponse([{ id: 1 }], 1));

            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData: [],
                    initialTotal: 5,
                }),
            );

            const sentinel = document.createElement("div");
            act(() => {
                result.current.sentinelRef(sentinel);
            });

            await act(async () => {
                fireIO(true);
            });

            await waitFor(() => {
                expect(result.current.isError).toBe(true);
            });

            // Call retry to re-trigger loadMore
            await act(async () => {
                result.current.retry();
            });

            await waitFor(() => {
                expect(result.current.isError).toBe(false);
            });

            expect(result.current.errorMessage).toBeUndefined();
            expect(result.current.data).toEqual([{ id: 1 }]);
            expect(mockFetch).toHaveBeenCalledTimes(2);
        });

        it("swallows AbortError without setting isError", async () => {
            const abortError = new Error("The user aborted a request.");
            abortError.name = "AbortError";
            mockFetch.mockRejectedValue(abortError);

            const { result } = renderHook(() =>
                useInfiniteSearch({
                    endpoint: "/api/search",
                    params: {},
                    initialData: [],
                    initialTotal: 5,
                }),
            );

            const sentinel = document.createElement("div");
            act(() => {
                result.current.sentinelRef(sentinel);
            });

            await act(async () => {
                fireIO(true);
            });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.isError).toBe(false);
            expect(result.current.errorMessage).toBeUndefined();
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
                fireIO(true);
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
                fireIO(true);
            });

            await waitFor(() => {
                expect(result.current.data).toHaveLength(4);
            });

            expect(result.current.hasMore).toBe(true);
        });
    });
});
