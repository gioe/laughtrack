"use client";

import { Input } from "@nextui-org/react";
import SearchIcon from "../../icons/SearchIcon";
import React, { useState } from "react";
import { useDebouncedCallback } from "use-debounce";
import { QueryProperty } from "../../../objects/enum";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { SearchParamsHelper } from "../../../objects/class/params/SearchParamsHelper";
import { Navigator } from "../../../objects/class/navigate/Navigator";

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
        <div className="w-full flex flex-item gap-2 max-w-[240px] m-5 bg-red-900">
            <Input
                placeholder={inputPlaceholder}
                value={value}
                onValueChange={handleInputChange}
                startContent={
                    <SearchIcon className="text-black/50 mb-0.5 dark:text-white/90 text-slate-400 pointer-events-none flex-shrink-0 mr-3" />
                }
            />
        </div>
    );
};

export default QueryParamComponent;
