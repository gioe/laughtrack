import { useCallback, useState } from 'react';
import { useUrlParams } from "@/hooks/useUrlParams";
import { QueryProperty } from "@/objects/enum";
import { SortOptionInterface } from "@/objects/interface";
import { getDefaultSortingOption } from "@/util/filter/util";

export function useSortParams(sortOptions: SortOptionInterface[]) {
    const { getTypedParam, setMultipleTypedParams } = useUrlParams();

    const getSortState = useCallback(() => {
        const sortParam = getTypedParam(QueryProperty.Sort);
        const directionParam = getTypedParam(QueryProperty.Direction);
        return getDefaultSortingOption(sortOptions, sortParam, directionParam);
    }, [getTypedParam, sortOptions]);

    const [selectedOption, setSelectedOption] = useState(getSortState());

    const updateSort = useCallback((sortValue: SortOptionInterface) => {
        setMultipleTypedParams({
            sort: sortValue.value,
            direction: sortValue.direction,
        });
        setSelectedOption(sortValue);
    }, [setMultipleTypedParams]);

    const isSelected = useCallback((option: SortOptionInterface) => {
        return option.value === selectedOption.value &&
               option.direction === selectedOption.direction;
    }, [selectedOption]);

    return {
        selectedOption,
        updateSort,
        isSelected
    };
}
