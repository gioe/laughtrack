import { Filter } from "@/objects/class/filter/Filter";
import { Navigator } from "@/objects/class/navigate/Navigator";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { QueryProperty } from "@/objects/enum";
import { FilterDTO } from "@/objects/interface/filter.interface";
import { useState } from "react";

export const useFilters = (filters: FilterDTO[], paramsHelper: SearchParamsHelper, navigator: Navigator) => {

    const initialParamValue = paramsHelper.getParamValue(QueryProperty.Filters)

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

        paramsHelper.setParamValue(QueryProperty.Filters, paramValue);
        navigator.replaceRoute(paramsHelper.asParamsString());
        setSelectedFilters(newFilters);
    };

    const handleClose = () => {
        paramsHelper.setParamValue(QueryProperty.Filters, initialParamValue);
        navigator.replaceRoute(paramsHelper.asParamsString());
    };

    return { selectedFilters, handleFilterChange, handleClose };
};
