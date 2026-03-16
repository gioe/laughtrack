import { useRef, useState } from "react";
import { QueryProperty } from "@/objects/enum";
import { FilterDTO } from "@/objects/interface";
import { useUrlParams } from "./useUrlParams";

export const useFilters = (filters: FilterDTO[]) => {
    const { setTypedParam } = useUrlParams();

    const [selections, setSelections] = useState<string[]>(() =>
        filters
            .filter((f: FilterDTO) => f.selected)
            .map((f: FilterDTO) => f.slug),
    );
    const savedSelections = useRef<string[]>(selections);

    const setFilterParamValue = (newFilters: string[]) => {
        const paramValue = newFilters.join(",");
        setTypedParam(QueryProperty.Filters, paramValue);
    };

    const handleOpen = () => {
        savedSelections.current = selections;
    };

    const handleFilterChange = (value: string) => {
        const newFilters = selections.includes(value)
            ? selections.filter((t: string) => t !== value)
            : [...selections, value];
        setSelections(newFilters);
        setFilterParamValue(newFilters);
    };

    const handleClose = () => {
        setSelections(savedSelections.current);
        setFilterParamValue(savedSelections.current);
    };

    return { handleOpen, handleFilterChange, handleClose, selections };
};
