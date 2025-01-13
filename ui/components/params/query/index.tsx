"use client";

import { Input } from "../../ui/input";
import SearchIcon from "../../icons/SearchIcon";
import React, { useState } from "react";
import { useDebouncedCallback } from "use-debounce";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { QueryProperty } from "@/objects/enum";
import { Navigator } from "@/objects/class/navigate/Navigator";

interface QueryParamComponentProps {
    inputPlaceholder: string;
}

const QueryParamComponent: React.FC<QueryParamComponentProps> = ({
    inputPlaceholder,
}) => {
    const paramsHelper = new SearchParamsHelper(useSearchParams());

    const navigator = new Navigator(usePathname(), useRouter());

    const [value, setValue] = useState(
        paramsHelper.getParamValue(QueryProperty.Query),
    );

    const handleInputChange = (value: string) => {
        handleSearch(value);
        setValue(value);
    };

    const handleSearch = useDebouncedCallback((term) => {
        paramsHelper.setParamValue(QueryProperty.Query, term);
        navigator.replaceRoute(paramsHelper.asParamsString());
    }, 300);

    return (
        <div className="flex items-center gap-2">
            <SearchIcon className="text-black/50 mb-0.5 dark:text-white/90 text-slate-400 pointer-events-none flex-shrink-0" />
            <Input
                className="font-inter text-copper rounded-lg 
                placeholder:text-copper placeholder:font-inter placeholder:text-sm"
                placeholder={inputPlaceholder}
                value={value}
                onChange={(e) => {
                    handleInputChange(e.target.value);
                }}
            />
        </div>
    );
};

export default QueryParamComponent;
