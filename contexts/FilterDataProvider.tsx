"use client";

import { useState, useEffect, useContext, createContext } from "react";
import { Filter } from "../objects/class/filter/Filter";
import { FilterDataDTO } from "../objects/interface/filter.interface";
import { useSearchParams } from "next/navigation";
import { usePageContext } from "./PageEntityProvider";
import { SearchParamsHelper } from "../objects/class/params/SearchParamsHelper";
import { APIRoutePath } from "../objects/enum";
import { makeRequest } from "../util/actions/makeRequest";
import { GetFiltersResponse } from "@/app/api/filter/interface";
import { Selectable } from "@/objects/interface";

interface FilterDataState {
    filters: Selectable[];
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
            console.log(filters);

            const parsedFilters = filters
                .map((dto: FilterDataDTO) => {
                    return new Filter(dto, paramsHelper);
                })
                .flatMap((filter) => filter.options);
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
