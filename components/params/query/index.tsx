"use client";

import { Input } from "@nextui-org/react";
import { useSearchParams } from "next/navigation";
import SearchIcon from "../../icons/SearchIcon";
import React, { useState } from "react";
import { useDebouncedCallback } from "use-debounce";
import { URLParam } from "../../../util/enum";
import { usePathname, useRouter } from "next/navigation";
import { LaughtrackSearchParams } from "../../../objects/classes/searchParams/LaughtrackSearchParams";

interface QueryParamComponentProps {
    inputPlaceholder: string;
}

const QueryParamComponent: React.FC<QueryParamComponentProps> = ({
    inputPlaceholder,
}) => {
    const params = LaughtrackSearchParams.asClientSideParams(
        new URLSearchParams(useSearchParams()),
        usePathname(),
        useRouter(),
    );

    const [value, setValue] = useState(
        params.getParamValue(URLParam.Query) as string,
    );

    const handleInputChange = (value: string) => {
        handleSearch(value);
        setValue(value);
    };

    const handleSearch = useDebouncedCallback((term) => {
        params.setParamValue(URLParam.Query, term);
        params.replaceRoute();
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
