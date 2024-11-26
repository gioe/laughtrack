"use client";

import { useState, useEffect, useContext, createContext } from "react";
import axios from "axios";
import { EntityType } from "../objects/enum";
import { FilterContainer } from "../objects/class/tag/FilterContainer";
import { TagDataDTO } from "../objects/interface/tag.interface";
import { useSearchParams } from "next/navigation";

interface FilterContextState {
    type: EntityType;
    filters: FilterContainer[];
}

const defaultState: FilterContextState = {
    type: EntityType.Show,
    filters: [],
};

const FilterContext = createContext<FilterContextState>(defaultState);

export function FilterContextProvider({
    children,
    type,
}: {
    type: EntityType;
    children: React.ReactNode;
}) {
    const searchParams = useSearchParams();
    const [state, setState] = useState<FilterContextState>(defaultState);

    const getFilters = async () => {
        axios
            .get(`/api/tag`)
            .then((response) => {
                return response.data;
            })
            .then((data) => {
                if (data) {
                    const filters = data.containers.map((dto: TagDataDTO) => {
                        return new FilterContainer(
                            dto,
                            searchParams.get(dto.value),
                        );
                    });
                    setState({
                        type: type,
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
        <FilterContext.Provider value={state}>
            {children}
        </FilterContext.Provider>
    );
}

export function useFilterContext() {
    return useContext(FilterContext);
}
