"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { QueryProperty } from "@/objects/enum";
import {
    ParamsDictValue,
    SearchParamsHelper,
    URLParam,
} from "@/objects/class/params/SearchParamsHelper";
import { Navigator } from "@/objects/class/navigate/Navigator";
import TextInputComponent from "../../../components/textInput";

export default function ComedianSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());

    const initialState = {
        comedian: paramsHelper.getParamValue(QueryProperty.Comedian) as string,
    };

    // Combined state management
    const [searchState, setSearchState] = useState(initialState);

    const updateSearchParams = <T extends keyof typeof initialState>(
        param: QueryProperty,
        value: any,
        stateUpdater: (prevState: typeof initialState) => typeof initialState,
    ) => {
        const map = new Map<URLParam, ParamsDictValue>();
        map.set(param, value);
        setSearchState(stateUpdater);
        paramsHelper.updateParamsFromMap(map);
        navigator.replaceRoute(paramsHelper.asParamsString());
    };

    const handleComedianSearch = (value: string) =>
        updateSearchParams(QueryProperty.Comedian, value, (prev) => ({
            ...prev,
            comedian: value,
        }));

    return (
        <div className="flex items-center bg-ivory rounded-full border border-gray-200 px-4 py-2 shadow-sm max-w-xl w-full">
            {/* Date input */}
            <div className="flex items-center flex-1 px-4">
                <TextInputComponent
                    icon={
                        <Users
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    placeholder="Search for comedian"
                    value={searchState.comedian}
                    onChange={handleComedianSearch}
                    className="border-gray-200 bg-ivory ring-transparent focus:ring-transparent
    shadow-none border-transparent focus:outline-none outline-none"
                />
            </div>
        </div>
    );
}
