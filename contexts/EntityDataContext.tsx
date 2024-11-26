"use client";

import { useState, useEffect, useContext, createContext } from "react";
import axios from "axios";
import { Filter } from "../objects/class/tag/Filter";
import { TagDataDTO } from "../objects/interface/tag.interface";
import { useSearchParams } from "next/navigation";
import { SortOptionInterface } from "../objects/interface";
import { getSortOptionsForEntityType } from "../util/sort";
import { useEntityTypeContext } from "./EntityContext";

interface EntityDataState {
    filters: Filter[];
    sortOptions: SortOptionInterface[];
}

const defaultState: EntityDataState = {
    filters: [],
    sortOptions: [],
};

const EntityDataContext = createContext<EntityDataState>(defaultState);

export function EntityDataProvider({
    children,
}: {
    children: React.ReactNode;
}) {
    const { currentEntityContext } = useEntityTypeContext();
    const searchParams = useSearchParams();
    const [state, setState] = useState<EntityDataState>({
        filters: [],
        sortOptions: getSortOptionsForEntityType(currentEntityContext),
    });

    const getFilters = async () => {
        axios
            .get(`/api/tag`)
            .then((response) => response.data)
            .then((data) => {
                if (data) {
                    const filters = data.containers.map((dto: TagDataDTO) => {
                        return new Filter(dto, searchParams.get(dto.value));
                    });
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
        <EntityDataContext.Provider value={state}>
            {children}
        </EntityDataContext.Provider>
    );
}

export function useDataProvider() {
    return useContext(EntityDataContext);
}
