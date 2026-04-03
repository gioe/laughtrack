import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useUrlParams } from "@/hooks/useUrlParams";
import { QueryProperty } from "@/objects/enum";
import { adminSortOptions } from "@/objects/enum/sortParamValue";
import { SortOptionInterface } from "@/objects/interface";
import { getDefaultSortingOption } from "@/util/filter/util";

export function useSortParams(
    sortOptions: SortOptionInterface[],
    isAdmin = false,
) {
    const { getTypedParam, setTypedParam } = useUrlParams();
    const searchParams = useSearchParams();
    const router = useRouter();

    const getSortState = useCallback(() => {
        const sortParam = getTypedParam(QueryProperty.Sort);
        if (sortParam) return getDefaultSortingOption(sortOptions, sortParam);

        // For admin users: if the URL has an admin-only sort value that failed
        // the standard allSortOptions validation, resolve it directly.
        if (isAdmin) {
            const rawSort = searchParams.get(QueryProperty.Sort);
            if (rawSort && adminSortOptions.includes(rawSort)) {
                const adminOption = sortOptions.find(
                    (o) => o.value === rawSort,
                );
                if (adminOption) return adminOption;
            }
        }

        return getDefaultSortingOption(sortOptions, undefined);
    }, [getTypedParam, sortOptions, isAdmin, searchParams]);

    const [selectedOption, setSelectedOption] = useState(getSortState());

    // Strip admin-only sort params from the URL for non-admin users.
    useEffect(() => {
        if (isAdmin) return;
        const rawSort = searchParams.get(QueryProperty.Sort);
        if (rawSort && adminSortOptions.includes(rawSort)) {
            const current = new URLSearchParams(searchParams.toString());
            current.delete(QueryProperty.Sort);
            router.replace(`?${current.toString()}`);
        }
    }, [isAdmin, searchParams, router]);

    // Sync with URL params on mount and when URL params change
    useEffect(() => {
        const currentSort = getSortState();
        if (currentSort?.value !== selectedOption?.value) {
            setSelectedOption(currentSort);
        }
    }, [getSortState, selectedOption?.value]);

    const updateSort = useCallback(
        (sortValue: SortOptionInterface) => {
            setTypedParam(QueryProperty.Sort, sortValue.value);
            setSelectedOption(sortValue);
        },
        [setTypedParam],
    );

    const isSelected = useCallback(
        (option: SortOptionInterface) => {
            return option.value === selectedOption.value;
        },
        [selectedOption],
    );

    return {
        selectedOption,
        updateSort,
        isSelected,
    };
}
