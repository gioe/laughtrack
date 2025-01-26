"use client";

import { useState, useEffect, useContext, createContext } from "react";
import { Filter } from "../objects/class/filter/Filter";
import { FilterDTO } from "../objects/interface/filter.interface";
import { useSearchParams } from "next/navigation";
import { usePageContext } from "./PageEntityProvider";
import { SearchParamsHelper } from "../objects/class/params/SearchParamsHelper";
import { APIRoutePath, QueryProperty } from "../objects/enum";
import { makeRequest } from "../util/actions/makeRequest";
import { GetFiltersResponse } from "@/app/api/filter/interface";

interface FilterDataState {
    filters: Filter[];
}

const defaultState: FilterDataState = {
    filters: [],
};

const FilterDataContext = createContext<FilterDataState>(defaultState);

export function FilterDataProvider({
    children,
}: {
    children: React.ReactNode;
}) {
    const { primaryEntity } = usePageContext();

    const paramsHelper = new SearchParamsHelper(useSearchParams());

    const [state, setState] = useState<FilterDataState>({
        filters: [],
    });

    const getFilters = async () => {
        try {
            const { filters } = await makeRequest<GetFiltersResponse>(
                APIRoutePath.Filter + `/?entity=${primaryEntity}`,
            );

            const parsedFilters = filters.map(
                (dto: FilterDTO) =>
                    new Filter(
                        dto,
                        paramsHelper.getParamValue(QueryProperty.Filters),
                    ),
            );

            setState({
                filters: parsedFilters,
            });
        } catch (error) {
            console.log(error);
        }
    };

    useEffect(() => {
        getFilters();
    }, []);

    return (
        <FilterDataContext.Provider value={state}>
            {children}
        </FilterDataContext.Provider>
    );
}

export function useFilterProvider() {
    return useContext(FilterDataContext);
}
