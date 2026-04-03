/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSortParams } from "./useSortParams";
import { SortParamValue, QueryProperty } from "@/objects/enum";
import { SortOptionInterface } from "@/objects/interface";

const mockGetTypedParam = vi.fn();
const mockSetTypedParam = vi.fn();
const mockReplace = vi.fn();
const mockSearchParamsGet = vi.fn();

vi.mock("@/hooks/useUrlParams", () => ({
    useUrlParams: () => ({
        getTypedParam: mockGetTypedParam,
        setTypedParam: mockSetTypedParam,
        setMultipleTypedParams: vi.fn(),
    }),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => ({ replace: mockReplace }),
    useSearchParams: () => ({
        get: mockSearchParamsGet,
        toString: () => "",
    }),
}));

const sortOptions: SortOptionInterface[] = [
    { name: "Date Asc", value: SortParamValue.DateAsc },
    { name: "Date Desc", value: SortParamValue.DateDesc },
    { name: "Most Popular", value: SortParamValue.PopularityDesc },
];

const adminSortOptions: SortOptionInterface[] = [
    ...sortOptions,
    { name: "Newest First", value: SortParamValue.InsertedAtDesc },
    { name: "Oldest First", value: SortParamValue.InsertedAtAsc },
];

beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParamsGet.mockReturnValue(null);
});

describe("useSortParams", () => {
    describe("reads sort value from URL", () => {
        it("initializes selectedOption from a valid URL param", () => {
            mockGetTypedParam.mockReturnValue(SortParamValue.DateDesc);

            const { result } = renderHook(() => useSortParams(sortOptions));

            expect(result.current.selectedOption.value).toBe(
                SortParamValue.DateDesc,
            );
        });

        it("reflects a different valid URL param", () => {
            mockGetTypedParam.mockReturnValue(SortParamValue.PopularityDesc);

            const { result } = renderHook(() => useSortParams(sortOptions));

            expect(result.current.selectedOption.value).toBe(
                SortParamValue.PopularityDesc,
            );
        });
    });

    describe("writes URL on change", () => {
        it("calls setTypedParam with the chosen option value", () => {
            mockGetTypedParam.mockReturnValue(SortParamValue.DateAsc);

            const { result } = renderHook(() => useSortParams(sortOptions));

            act(() => {
                result.current.updateSort(sortOptions[2]);
            });

            expect(mockSetTypedParam).toHaveBeenCalledWith(
                QueryProperty.Sort,
                SortParamValue.PopularityDesc,
            );
        });

        it("updates selectedOption after updateSort", () => {
            mockGetTypedParam.mockReturnValue(SortParamValue.DateAsc);

            const { result } = renderHook(() => useSortParams(sortOptions));

            act(() => {
                // Simulate URL being updated before the sync effect re-runs.
                mockGetTypedParam.mockReturnValue(SortParamValue.DateDesc);
                result.current.updateSort(sortOptions[1]);
            });

            expect(result.current.selectedOption.value).toBe(
                SortParamValue.DateDesc,
            );
        });
    });

    describe("defaults to sortOptions[0] when URL param is absent or invalid", () => {
        it("defaults to sortOptions[0] when getTypedParam returns undefined", () => {
            mockGetTypedParam.mockReturnValue(undefined);

            const { result } = renderHook(() => useSortParams(sortOptions));

            expect(result.current.selectedOption.value).toBe(
                SortParamValue.DateAsc,
            );
        });

        it("defaults to sortOptions[0] when getTypedParam returns an unrecognized value", () => {
            mockGetTypedParam.mockReturnValue("not_a_real_sort_value");

            const { result } = renderHook(() => useSortParams(sortOptions));

            expect(result.current.selectedOption.value).toBe(
                SortParamValue.DateAsc,
            );
        });

        it("returns undefined selectedOption when sortOptions array is empty", () => {
            mockGetTypedParam.mockReturnValue(undefined);

            const { result } = renderHook(() => useSortParams([]));

            // getDefaultSortingOption returns sortOptions[0] which is undefined for an
            // empty array — callers must ensure sortOptions is non-empty.
            expect(result.current.selectedOption).toBeUndefined();
        });
    });

    describe("isSelected", () => {
        it("returns true for the currently active option", () => {
            mockGetTypedParam.mockReturnValue(SortParamValue.DateDesc);

            const { result } = renderHook(() => useSortParams(sortOptions));

            expect(result.current.isSelected(sortOptions[1])).toBe(true);
        });

        it("returns false for options that are not active", () => {
            mockGetTypedParam.mockReturnValue(SortParamValue.DateDesc);

            const { result } = renderHook(() => useSortParams(sortOptions));

            expect(result.current.isSelected(sortOptions[0])).toBe(false);
            expect(result.current.isSelected(sortOptions[2])).toBe(false);
        });
    });

    describe("admin sort gating", () => {
        it("non-admin with admin sort in URL defaults to sortOptions[0]", () => {
            // getTypedParam returns undefined because inserted_at_desc is not in allSortOptions
            mockGetTypedParam.mockReturnValue(undefined);
            mockSearchParamsGet.mockReturnValue(SortParamValue.InsertedAtDesc);

            const { result } = renderHook(() =>
                useSortParams(sortOptions, false),
            );

            expect(result.current.selectedOption.value).toBe(
                SortParamValue.DateAsc,
            );
        });

        it("non-admin with admin sort in URL triggers URL strip", () => {
            mockGetTypedParam.mockReturnValue(undefined);
            mockSearchParamsGet.mockReturnValue(SortParamValue.InsertedAtDesc);

            renderHook(() => useSortParams(sortOptions, false));

            expect(mockReplace).toHaveBeenCalledWith("?");
        });

        it("admin with admin sort in URL resolves to the admin option", () => {
            // getTypedParam still returns undefined (admin sorts not in allSortOptions)
            mockGetTypedParam.mockReturnValue(undefined);
            mockSearchParamsGet.mockReturnValue(SortParamValue.InsertedAtDesc);

            const { result } = renderHook(() =>
                useSortParams(adminSortOptions, true),
            );

            expect(result.current.selectedOption.value).toBe(
                SortParamValue.InsertedAtDesc,
            );
        });

        it("admin with admin sort in URL does not trigger URL strip", () => {
            mockGetTypedParam.mockReturnValue(undefined);
            mockSearchParamsGet.mockReturnValue(SortParamValue.InsertedAtDesc);

            renderHook(() => useSortParams(adminSortOptions, true));

            expect(mockReplace).not.toHaveBeenCalled();
        });

        it("non-admin with a valid (non-admin) sort in URL does not trigger URL strip", () => {
            mockGetTypedParam.mockReturnValue(SortParamValue.PopularityDesc);
            mockSearchParamsGet.mockReturnValue(SortParamValue.PopularityDesc);

            renderHook(() => useSortParams(sortOptions, false));

            expect(mockReplace).not.toHaveBeenCalled();
        });
    });
});
