"use client";

import { useState, useEffect, useContext, createContext } from "react";
import axios from "axios";
import { EntityType } from "../objects/enum";
import { TagContainer } from "../objects/class/tag/TagContainer";
import { TagDataDTO } from "../objects/interface/tag.interface";
import { useSearchParams } from "next/navigation";

interface FilterList {
    containers: TagContainer[];
}

const defaultList: FilterList = {
    containers: [],
};

const FilterContext = createContext<FilterList>(defaultList);

export function FilterContextProvider({
    type,
    children,
}: {
    type: EntityType;
    children: React.ReactNode;
}) {
    const searchParams = useSearchParams();
    const [containers, setTagContainers] = useState(defaultList);

    const getFilters = async () => {
        axios
            .post(`/api/tag`, {
                type: `${type.valueOf()}`,
            })
            .then((response) => {
                return response.data;
            })
            .then((data) => {
                if (data) {
                    const containers = data.containers.map(
                        (dto: TagDataDTO) => {
                            return new TagContainer(
                                dto,
                                searchParams.get(dto.value),
                            );
                        },
                    );
                    setTagContainers({
                        containers,
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
        <FilterContext.Provider value={containers}>
            {children}
        </FilterContext.Provider>
    );
}

export function useFilterContext() {
    return useContext(FilterContext);
}
