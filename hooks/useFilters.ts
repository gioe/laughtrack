import { Filter } from "@/objects/class/filter/Filter";
import { Navigator } from "@/objects/class/navigate/Navigator";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { QueryProperty } from "@/objects/enum";
import { DEFAULT_ERROR } from "@/objects/enum/queryProperty";
import { FilterDTO } from "@/objects/interface/filter.interface";
import { ReadonlyURLSearchParams } from "next/navigation";
import { useState } from "react";

export const useFilters = (filters: FilterDTO[], searchParams: ReadonlyURLSearchParams, navigator: Navigator) => {

    const initialParamValue = searchParams.get(QueryProperty.Filters) as string

    const [selectedFilters, setSelectedFilters] = useState(
        filters.map(dto => new Filter(dto, initialParamValue))
            .filter(filter => filter.selected)
            .map(filter => filter.id)
    );

    const handleFilterChange = (option: Filter) => {
        const newFilters = selectedFilters.includes(option.id)
            ? selectedFilters.filter(t => t !== option.id)
            : [...selectedFilters, option.id];

        const paramValue = filters
            .filter(f => newFilters.includes(f.id))
            .map(f => f.display)
            .join(",");

        // searchParams.setParamValue(QueryProperty.Filters, paramValue);
        // navigator.replaceRoute(paramsHelper.asParamsString());
        setSelectedFilters(newFilters);
    };

    const handleClose = () => {
        let resetValue = initialParamValue == DEFAULT_ERROR ? '' : initialParamValue
        // paramsHelper.setParamValue(QueryProperty.Filters, resetValue);
        // navigator.replaceRoute(paramsHelper.asParamsString());
    };

    return { selectedFilters, handleFilterChange, handleClose };
};
