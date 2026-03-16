/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useFilters } from "./useFilters";
import { QueryProperty } from "@/objects/enum";
import { FilterDTO } from "@/objects/interface";

const mockSetTypedParam = vi.fn();

vi.mock("@/hooks/useUrlParams", () => ({
    useUrlParams: () => ({
        getTypedParam: vi.fn(),
        setTypedParam: mockSetTypedParam,
        setMultipleTypedParams: vi.fn(),
    }),
}));

function makeFilters(
    slugs: string[],
    selectedSlugs: string[] = [],
): FilterDTO[] {
    return slugs.map((slug, i) => ({
        id: i,
        slug,
        name: slug,
        selected: selectedSlugs.includes(slug),
    }));
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("useFilters", () => {
    describe("toggle adds/removes", () => {
        it("adds a filter when it is not yet selected", () => {
            const { result } = renderHook(() =>
                useFilters(makeFilters(["comedy", "improv"])),
            );

            act(() => {
                result.current.handleFilterChange("comedy");
            });

            expect(mockSetTypedParam).toHaveBeenCalledWith(
                QueryProperty.Filters,
                "comedy",
            );
        });

        it("removes a filter on second toggle (toggle off)", () => {
            const { result } = renderHook(() =>
                useFilters(makeFilters(["comedy", "improv"], ["comedy"])),
            );

            act(() => {
                result.current.handleFilterChange("comedy");
            });

            expect(mockSetTypedParam).toHaveBeenCalledWith(
                QueryProperty.Filters,
                "",
            );
        });
    });

    describe("sequential toggles accumulate correctly", () => {
        it("accumulates selections when different filters are toggled in sequence", () => {
            const { result } = renderHook(() =>
                useFilters(makeFilters(["a", "b", "c"])),
            );

            act(() => {
                result.current.handleFilterChange("a");
            });
            act(() => {
                result.current.handleFilterChange("b");
            });
            act(() => {
                result.current.handleFilterChange("c");
            });

            expect(mockSetTypedParam).toHaveBeenLastCalledWith(
                QueryProperty.Filters,
                "a,b,c",
            );
        });

        it("de-selects mid-stream without losing other selections", () => {
            const { result } = renderHook(() =>
                useFilters(makeFilters(["a", "b", "c"])),
            );

            act(() => {
                result.current.handleFilterChange("a");
            });
            act(() => {
                result.current.handleFilterChange("b");
            });
            act(() => {
                result.current.handleFilterChange("a");
            }); // remove a

            expect(mockSetTypedParam).toHaveBeenLastCalledWith(
                QueryProperty.Filters,
                "b",
            );
        });
    });

    describe("handleClose reverts to pre-modal-open state", () => {
        it("reverts to empty selections saved by handleOpen", () => {
            const { result } = renderHook(() =>
                useFilters(makeFilters(["a", "b"])),
            );

            act(() => {
                result.current.handleOpen();
            }); // save empty
            act(() => {
                result.current.handleFilterChange("a");
            });
            act(() => {
                result.current.handleFilterChange("b");
            });
            act(() => {
                result.current.handleClose();
            }); // revert

            expect(mockSetTypedParam).toHaveBeenLastCalledWith(
                QueryProperty.Filters,
                "",
            );
        });

        it("reverts to the non-empty selections present when handleOpen was called", () => {
            const { result } = renderHook(() =>
                useFilters(makeFilters(["a", "b", "c"], ["a"])),
            );

            act(() => {
                result.current.handleOpen();
            }); // save ["a"]
            act(() => {
                result.current.handleFilterChange("b");
            }); // add b
            act(() => {
                result.current.handleClose();
            }); // revert to ["a"]

            expect(mockSetTypedParam).toHaveBeenLastCalledWith(
                QueryProperty.Filters,
                "a",
            );
        });

        it("reverts to selections accumulated via handleFilterChange before handleOpen was called", () => {
            const { result } = renderHook(() =>
                useFilters(makeFilters(["a", "b", "c"])),
            );

            // Build up selections before opening the modal
            act(() => {
                result.current.handleFilterChange("a");
            });
            act(() => {
                result.current.handleFilterChange("b");
            });
            act(() => {
                result.current.handleOpen();
            }); // save ["a", "b"]
            act(() => {
                result.current.handleFilterChange("c");
            }); // add c
            act(() => {
                result.current.handleClose();
            }); // revert to ["a", "b"]

            expect(mockSetTypedParam).toHaveBeenLastCalledWith(
                QueryProperty.Filters,
                "a,b",
            );
        });
    });
});
