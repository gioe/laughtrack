"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Navigator } from "../../../../objects/class/navigate/Navigator";
import {
    ParamsDictValue,
    SearchParamsHelper,
    URLParam,
} from "../../../../objects/class/params/SearchParamsHelper";
import { useCityContext } from "@/contexts/CityProvider";
import { Theater } from "lucide-react";
import TextInputComponent from "../../input/search/text/input";
import { useStyleContext } from "@/contexts/StyleProvider";
import { QueryProperty } from "@/objects/enum";

export default function ComedianSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const cityList = useCityContext();

    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());
    const currentSelection = paramsHelper.getParamValue(
        QueryProperty.City,
    ) as string;
    const currentClubQuery = paramsHelper.getParamValue(
        QueryProperty.Query,
    ) as string;

    const [selectedValue, setSelectedValue] = useState(currentSelection);
    const [comedianQuery, setComedianQuery] = useState(currentClubQuery);

    function handleSearch(value: string) {
        const map = new Map<URLParam, ParamsDictValue>();
        map.set(QueryProperty.Comedian, value);
        setComedianQuery(value);
        paramsHelper.updateParamsFromMap(map);
        navigator.replaceRoute(paramsHelper.asParamsString());
    }

    return (
        <div className="flex items-center bg-ivory rounded-full border border-gray-200 px-4 py-2 shadow-sm max-w-xl w-full">
            {/* Date input */}
            <div className="flex items-center flex-1 px-4">
                <TextInputComponent
                    icon={
                        <Theater
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    placeholder="Search for comedian"
                    value={comedianQuery}
                    onChange={handleSearch}
                    className="border-gray-200 bg-ivory ring-transparent focus:ring-transparent 
    shadow-none border-transparent focus:outline-none outline-none"
                />
            </div>
        </div>
    );
}
