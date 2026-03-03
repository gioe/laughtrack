import { useCallback, useEffect, useState } from 'react';
import { useUrlParams } from "@/hooks/useUrlParams";
import { QueryProperty } from "@/objects/enum";
import { SortOptionInterface } from "@/objects/interface";
import { getDefaultSortingOption } from "@/util/filter/util";

export function useSortParams(sortOptions: SortOptionInterface[]) {
    const { getTypedParam, setTypedParam } = useUrlParams();

    const getSortState = useCallback(() => {
        const sortParam = getTypedParam(QueryProperty.Sort);
        return getDefaultSortingOption(sortOptions, sortParam);
    }, [getTypedParam, sortOptions]);

    const [selectedOption, setSelectedOption] = useState(getSortState());

    // Sync with URL params on mount and when URL params change
    useEffect(() => {
        const currentSort = getSortState();
        if (currentSort.value !== selectedOption.value) {
            setSelectedOption(currentSort);
        }
    }, [getSortState, selectedOption.value]);

    const updateSort = useCallback((sortValue: SortOptionInterface) => {
        setTypedParam(QueryProperty.Sort, sortValue.value);
        setSelectedOption(sortValue);
    }, [setTypedParam]);

    const isSelected = useCallback((option: SortOptionInterface) => {
        return option.value === selectedOption.value;
    }, [selectedOption]);

    return {
        selectedOption,
        updateSort,
        isSelected
    };
}
