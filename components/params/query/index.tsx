"use client";

import { Input } from "@nextui-org/react";
import { useSearchParams } from "next/navigation";
import SearchIcon from "../../icons/SearchIcon";
import React, { useState } from "react";
import { useDebouncedCallback } from "use-debounce";
import { URLParam } from "../../../objects/enum";
import { usePathname, useRouter } from "next/navigation";
import { ParamsWrapper } from "../../../objects/class/params/ParamsWrapper";
import { Navigator } from "../../../objects/class/navigate/Navigator";

interface QueryParamComponentProps {
    inputPlaceholder: string;
}

const QueryParamComponent: React.FC<QueryParamComponentProps> = ({
    inputPlaceholder,
}) => {
    const paramsWrapper = ParamsWrapper.fromClientSideParams(
        usePathname(),
        new URLSearchParams(useSearchParams()),
    );
    const navigator = new Navigator(usePathname(), useRouter());

    const [value, setValue] = useState(
        paramsWrapper.getParamValue(URLParam.Query) as string,
    );

    const handleInputChange = (value: string) => {
        handleSearch(value);
        setValue(value);
    };

    const handleSearch = useDebouncedCallback((term) => {
        paramsWrapper.setParamValue(URLParam.Query, term);
        navigator.replaceRoute(paramsWrapper.asParamsString());
    }, 300);

    return (
        <div className="w-full flex flex-col gap-2 max-w-[240px] m-5">
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
