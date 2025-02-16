"use client";

import TextInputComponent from "../../../components/textInput";
import { useState } from "react";
import { Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { QueryProperty } from "@/objects/enum";
import { ParamKeys, useUrlParams } from "@/hooks/useUrlParams";

export default function ComedianSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam } = useUrlParams();

    const comedian = getTypedParam(QueryProperty.Comedian);

    const initialState = {
        comedian,
    };

    // Combined state management
    const [searchState, setSearchState] = useState(initialState);

    const updateSearchParams = <T extends keyof typeof initialState>(
        param: ParamKeys,
        value: any,
        stateUpdater: (prevState: typeof initialState) => typeof initialState,
    ) => {
        setTypedParam(param, value);
        setSearchState(stateUpdater);
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
                    value={searchState.comedian ?? ""}
                    onChange={handleComedianSearch}
                    className="border-gray-200 bg-ivory ring-transparent focus:ring-transparent
    shadow-none border-transparent focus:outline-none outline-none"
                />
            </div>
        </div>
    );
}
