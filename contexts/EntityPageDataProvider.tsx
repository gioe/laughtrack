"use client";

import { useState, useEffect, useContext, createContext } from "react";
import axios from "axios";
import { Filter } from "../objects/class/filter/Filter";
import { FilterDataDTO } from "../objects/interface/filter.interface";
import { useSearchParams } from "next/navigation";
import { SortOptionInterface } from "../objects/interface";
import { getSortOptionsForEntityType } from "../util/sort";
import { usePageContext } from "./PageEntityProvider";
import { SearchParamsHelper } from "../objects/class/params/SearchParamsHelper";

interface EntityDataState {
    filters: Filter[];
    sortOptions: SortOptionInterface[];
}

const defaultState: EntityDataState = {
    filters: [],
    sortOptions: [],
};

const EntityPageDataContext = createContext<EntityDataState>(defaultState);

export function EntityPageDataProvider({
    children,
}: {
    children: React.ReactNode;
}) {
    const { primaryEntity } = usePageContext();
    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const [state, setState] = useState<EntityDataState>({
        filters: [],
        sortOptions: getSortOptionsForEntityType(primaryEntity),
    });

    const getFilters = async () => {
        axios
            .get(`/api/tag`)
            .then((response) => response.data)
            .then((data) => {
                if (data) {
                    const filters = data.containers.map(
                        (dto: FilterDataDTO) => {
                            return new Filter(dto, paramsHelper);
                        },
                    );
                    setState({
                        ...state,
                        filters: filters,
                    });
                }
            })
            .catch((error: Error) => {
                console.log(error);
            });
    };

    useEffect(() => {
        getFilters();
    }, []);

    return (
        <EntityPageDataContext.Provider value={state}>
            {children}
        </EntityPageDataContext.Provider>
    );
}

export function useDataProvider() {
    return useContext(EntityPageDataContext);
}
