"use client";

import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";
import { useState } from "react";
import { Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { DateRange, getDateRangeFromParams } from "@/util/search/util";
import { ParamKeys, useUrlParams } from "@/hooks/useUrlParams";

export default function ClubDetailSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam } = useUrlParams();

    const comedian = getTypedParam(QueryProperty.Comedian);
    const from = getTypedParam(QueryProperty.FromDate);
    const to = getTypedParam(QueryProperty.ToDate);

    // Initial state setup
    const initialState = {
        comedian,
        dateRange: getDateRangeFromParams({
            from,
            to,
        }),
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
    const handleDateRangeSelection = (value?: DateRange) =>
        updateSearchParams(
            QueryProperty.FromDate,
            value?.from ?? "",
            (prev) => ({
                ...prev,
                dateRange: {
                    from: value?.from ?? new Date(),
                    to: value?.to,
                },
            }),
        );

    return (
        <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col lg:flex-row gap-2 lg:gap-0 bg-ivory rounded-3xl lg:rounded-full border border-gray-200 p-2 lg:p-4 shadow-sm">
                {/* Date Selection */}
                <div className="flex-1 lg:border-r lg:border-gray-200 lg:px-4">
                    <div className="flex items-center w-full p-2 lg:p-0 rounded-full lg:rounded-none hover:bg-gray-50 lg:hover:bg-transparent transition-colors">
                        <CalendarComponent
                            variant={ComponentVariant.Standalone}
                            value={searchState.dateRange}
                            onValueChange={handleDateRangeSelection}
                        />
                    </div>
                </div>

                {/* Comedian Search */}
                <div className="flex-1 lg:border-r lg:border-gray-200 lg:px-4">
                    <div className="flex items-center w-full p-2 lg:p-0 rounded-full lg:rounded-none hover:bg-gray-50 lg:hover:bg-transparent transition-colors">
                        <TextInputComponent
                            icon={
                                <Users
                                    className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                                />
                            }
                            placeholder="Search for comedian"
                            value={searchState.comedian ?? ""}
                            onChange={handleComedianSearch}
                            className="w-full border-gray-200 bg-ivory ring-transparent focus:ring-transparent
                            shadow-none border-transparent focus:outline-none outline-none"
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
