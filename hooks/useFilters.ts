import { QueryProperty } from "@/objects/enum";
import { FilterDTO } from "@/objects/interface/filter.interface";
import { useUrlParams } from "./useUrlParams";

export const useFilters = (filters: FilterDTO[]) => {
    const { getTypedParam, setTypedParam } = useUrlParams();

    const setFilterParamValue = (newFilters: string[]) => {
        const paramValue = newFilters.join(",");
        setTypedParam(QueryProperty.Filters, paramValue);
    }

    const initialSelections = filters.filter((f: FilterDTO) => f.selected).map((f: FilterDTO) => f.value);
    const urlSelections = getTypedParam(QueryProperty.Filters).split(",")

    const handleFilterChange = (value: string) => {
        const newFilters = initialSelections.includes(value)
            ? initialSelections.filter((t: string) => t !== value)
            : [...initialSelections, value];
        setFilterParamValue(newFilters);
    };

    const handleClose = () => {
        setFilterParamValue(urlSelections);
    };
    return { handleFilterChange, handleClose };
};
