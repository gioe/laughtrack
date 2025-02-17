"use client";

import { ChangeEvent, useState } from "react";
import { Theater } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import {
    DateRange,
    DistanceData,
    getDateRangeFromParams,
} from "@/util/search/util";
import ShowLocationComponent from "../../../components/area";
import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";
import { ParamKeys, useUrlParams } from "@/hooks/useUrlParams";

export default function ComedianDetailSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam } = useUrlParams();

    const comedian = getTypedParam(QueryProperty.Comedian);
    const club = getTypedParam(QueryProperty.Club);
    const distance = getTypedParam(QueryProperty.Distance);
    const zipCode = getTypedParam(QueryProperty.Zip);
    const from = getTypedParam(QueryProperty.FromDate);
    const to = getTypedParam(QueryProperty.ToDate);

    // Initial state setup
    const initialState = {
        comedian,
        club,
        distance: { distance, zipCode } as DistanceData,
        dateRange: getDateRangeFromParams({
            from,
            to,
        }),
    };

    // Combined state management
    const [searchState, setSearchState] = useState(initialState);

    // Generic update function for all search parameters
    const updateSearchParams = <T extends keyof typeof initialState>(
        param: ParamKeys,
        value: any,
        stateUpdater: (prevState: typeof initialState) => typeof initialState,
    ) => {
        setSearchState(stateUpdater);
        setTypedParam(param, value);
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
                    to: value?.to,
                },
            }),
        );
        updateSearchParams(QueryProperty.ToDate, value?.to ?? "", (prev) => ({
            ...prev,
            dateRange: {
                from: value?.from ?? new Date(),
                to: value?.to,
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
            <div className="flex flex-col lg:flex-row gap-2 lg:gap-0 bg-coconut-cream rounded-3xl lg:rounded-full border border-gray-200 p-2 lg:p-4 shadow-sm">
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

                <div className="flex-1 lg:border-r lg:border-gray-200 lg:px-4">
                    <div className="flex items-center w-full p-2 lg:p-0 rounded-full lg:rounded-none hover:bg-gray-50 lg:hover:bg-transparent transition-colors">
                        <CalendarComponent
                            variant={ComponentVariant.Standalone}
                            value={searchState.dateRange}
                            onValueChange={handleDateRangeSelection}
                        />
                    </div>
                </div>

                <div className="flex-1 lg:px-4">
                    <div className="flex items-center w-full p-2 lg:p-0 rounded-full lg:rounded-none hover:bg-gray-50 lg:hover:bg-transparent transition-colors">
                        <TextInputComponent
                            icon={
                                <Theater
                                    className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                                />
                            }
                            placeholder="Search by club"
                            value={searchState.club ?? ""}
                            onChange={handleClubSearch}
                            className="w-full border-gray-200 bg-coconut-cream ring-transparent focus:ring-transparent
                            shadow-none border-transparent focus:outline-none outline-none"
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
