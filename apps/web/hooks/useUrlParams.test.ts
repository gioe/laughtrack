/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useUrlParams } from "./useUrlParams";

const { replaceMock, pushMock, searchState } = vi.hoisted(() => ({
    replaceMock: vi.fn(),
    pushMock: vi.fn(),
    searchState: { value: "" },
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ replace: replaceMock, push: pushMock }),
    useSearchParams: () => new URLSearchParams(searchState.value),
}));

beforeEach(() => {
    vi.clearAllMocks();
    searchState.value = "";
});

describe("useUrlParams page reset", () => {
    it("drops the page param when a filter param changes", () => {
        searchState.value = "page=3&comedian=mulaney";
        const { result } = renderHook(() => useUrlParams());

        act(() => {
            result.current.setTypedParam("comedian", "burnham");
        });

        expect(replaceMock).toHaveBeenCalledWith("?comedian=burnham");
    });

    it("keeps the page param when the page param itself is set", () => {
        searchState.value = "comedian=mulaney";
        const { result } = renderHook(() => useUrlParams());

        act(() => {
            result.current.setTypedParam("page", 2);
        });

        expect(replaceMock).toHaveBeenCalledWith("?comedian=mulaney&page=2");
    });

    it("drops the page param when multiple filter params change", () => {
        searchState.value = "page=5&zip=10001";
        const { result } = renderHook(() => useUrlParams());

        act(() => {
            result.current.setMultipleTypedParams({
                zip: "60601",
                comedian: "mulaney",
            });
        });

        expect(replaceMock).toHaveBeenCalledWith(
            "?zip=60601&comedian=mulaney",
        );
    });

    it("drops the page param when the page size changes", () => {
        searchState.value = "page=3";
        const { result } = renderHook(() => useUrlParams());

        act(() => {
            result.current.setTypedParam("size", 20);
        });

        expect(replaceMock).toHaveBeenCalledWith("?size=20");
    });

    it("keeps an explicitly batched page value", () => {
        searchState.value = "";
        const { result } = renderHook(() => useUrlParams());

        act(() => {
            result.current.setMultipleTypedParams({
                comedian: "mulaney",
                page: 4,
            });
        });

        expect(replaceMock).toHaveBeenCalledWith("?comedian=mulaney&page=4");
    });

    it("keeps the page param when the only batched update fails validation", () => {
        searchState.value = "page=3";
        const { result } = renderHook(() => useUrlParams());

        act(() => {
            // distance only accepts the predefined radius options
            result.current.setMultipleTypedParams({ distance: "999" });
        });

        expect(replaceMock).toHaveBeenCalledWith("?page=3");
    });
});
