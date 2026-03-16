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

vi.mock("@/hooks/useUrlParams", () => ({
    useUrlParams: () => ({
        getTypedParam: mockGetTypedParam,
        setTypedParam: mockSetTypedParam,
        setMultipleTypedParams: vi.fn(),
    }),
}));

const sortOptions: SortOptionInterface[] = [
    { name: "Date Asc", value: SortParamValue.DateAsc },
    { name: "Date Desc", value: SortParamValue.DateDesc },
    { name: "Most Popular", value: SortParamValue.PopularityDesc },
];

beforeEach(() => {
    vi.clearAllMocks();
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
});
