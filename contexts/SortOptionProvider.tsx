"use client";

import { useState, useContext, createContext } from "react";
import { useSearchParams } from "next/navigation";
import { SortOptionInterface } from "../objects/interface";
import { getSortOptionsForEntityType } from "../util/sort";
import { usePageContext } from "./PageEntityProvider";
import { SearchParamsHelper } from "../objects/class/params/SearchParamsHelper";

interface SortOptionState {
    sortOptions: SortOptionInterface[];
}

const defaultState: SortOptionState = {
    sortOptions: [],
};

const SortOptionContext = createContext<SortOptionState>(defaultState);

export function SortOptionProvider({
    children,
}: {
    children: React.ReactNode;
}) {
    const { primaryEntity } = usePageContext();
    const paramsHelper = new SearchParamsHelper(useSearchParams());

    const [state, setState] = useState<SortOptionState>({
        sortOptions: getSortOptionsForEntityType(primaryEntity),
    });

    return (
        <SortOptionContext.Provider value={state}>
            {children}
        </SortOptionContext.Provider>
    );
}

export function useSortOptionProvider() {
    return useContext(SortOptionContext);
}
