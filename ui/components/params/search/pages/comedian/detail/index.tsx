"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ChangeEvent, useState } from "react";
import { Theater } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import {
    ParamsDictValue,
    SearchParamsHelper,
    URLParam,
} from "@/objects/class/params/SearchParamsHelper";
import { Navigator } from "@/objects/class/navigate/Navigator";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import {
    DateRange,
    getDateRangeFromParams,
    getDistanceDataFromParams,
} from "@/util/search/util";
import ShowLocationComponent from "../../../components/area";
import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";

export default function ComedianDetailSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());

    // Initial state setup
    const initialState = {
        comedian: paramsHelper.getParamValue(QueryProperty.Comedian) as string,
        club: paramsHelper.getParamValue(QueryProperty.Club) as string,
        distance: getDistanceDataFromParams(paramsHelper),
        dateRange: getDateRangeFromParams(paramsHelper),
    };

    // Combined state management
    const [searchState, setSearchState] = useState(initialState);

    // Generic update function for all search parameters
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

    const handleClubSearch = (value: string) =>
        updateSearchParams(QueryProperty.Club, value, (prev) => ({
            ...prev,
            club: value,
        }));

    const handleDateRangeSelection = (value?: DateRange) => {
        updateSearchParams(
            QueryProperty.FromDate,
            value?.from ?? "",
            (prev) => ({
                ...prev,
                dateRange: {
                    from: value?.from ?? new Date(),
                    to: value?.to ?? new Date(),
                },
            }),
        );
        updateSearchParams(QueryProperty.ToDate, value?.to ?? "", (prev) => ({
            ...prev,
            dateRange: {
                from: value?.from ?? new Date(),
                to: value?.to ?? new Date(),
            },
        }));
    };

    const handleDistanceSelection = (distance: string) =>
        updateSearchParams(QueryProperty.Distance, distance, (prev) => ({
            ...prev,
            distance: { ...prev.distance, distance },
        }));

    const handleZipCodeInput = (event: ChangeEvent<HTMLInputElement>) =>
        updateSearchParams(QueryProperty.Zip, event.target.value, (prev) => ({
            ...prev,
            distance: { ...prev.distance, zipCode: event.target.value },
        }));
    return (
        <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col lg:flex-row gap-2 lg:gap-0 bg-ivory rounded-3xl lg:rounded-full border border-gray-200 p-2 lg:p-4 shadow-sm">
                {/* City Selection */}
                <div className="flex-1 lg:border-r lg:border-gray-200 lg:pr-4">
                    <div className="flex items-center p-2 lg:p-0 rounded-full lg:rounded-none hover:bg-gray-50 lg:hover:bg-transparent transition-colors">
                        <ShowLocationComponent
                            variant={ComponentVariant.Standalone}
                            value={searchState.distance}
                            onDistanceSelection={handleDistanceSelection}
                            onZipcodeInput={handleZipCodeInput}
                        />
                    </div>
                </div>

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

                {/* Club Search */}
                <div className="flex-1 lg:px-4">
                    <div className="flex items-center w-full p-2 lg:p-0 rounded-full lg:rounded-none hover:bg-gray-50 lg:hover:bg-transparent transition-colors">
                        <TextInputComponent
                            icon={
                                <Theater
                                    className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                                />
                            }
                            placeholder="Search by club"
                            value={searchState.club}
                            onChange={handleClubSearch}
                            className="w-full border-gray-200 bg-ivory ring-transparent focus:ring-transparent
                            shadow-none border-transparent focus:outline-none outline-none"
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
