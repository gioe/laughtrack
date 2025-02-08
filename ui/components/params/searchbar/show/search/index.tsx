"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Theater, Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import {
    ParamsDictValue,
    SearchParamsHelper,
    URLParam,
} from "@/objects/class/params/SearchParamsHelper";
import { Navigator } from "@/objects/class/navigate/Navigator";
import TextInputComponent from "@/ui/components/input/search/text/input";
import { CalendarVariant } from "@/ui/components/calendar";
import { QueryProperty } from "@/objects/enum";
import CalendarComponent from "@/ui/components/calendar";
import ShowDistanceSelectionComponent, {
    DistanceComponentVariant,
} from "@/ui/components/area";
import {
    DateRange,
    DistanceData,
    getDateRangeFromParams,
    getDistanceDataFromParams,
} from "@/util/search/util";

export default function ShowSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());
    const currentComedianQuery = paramsHelper.getParamValue(
        QueryProperty.Comedian,
    ) as string;
    const currentClubQuery = paramsHelper.getParamValue(
        QueryProperty.Club,
    ) as string;

    const [distanceData, setDistanceQuery] = useState(
        getDistanceDataFromParams(paramsHelper),
    );
    const [dateRange, setSelectedDateRange] = useState(
        getDateRangeFromParams(paramsHelper),
    );
    const [comedianQuery, setComedianQuery] = useState(currentComedianQuery);
    const [clubQuery, setClubQuery] = useState(currentClubQuery);

    function handleComedianSearch(value: string) {
        const map = new Map<URLParam, ParamsDictValue>();
        map.set(QueryProperty.Comedian, value);
        setComedianQuery(value);
        paramsHelper.updateParamsFromMap(map);
        navigator.replaceRoute(paramsHelper.asParamsString());
    }

    function handleClubSearch(value: string) {
        const map = new Map<URLParam, ParamsDictValue>();
        map.set(QueryProperty.Club, value);
        setClubQuery(value);
        paramsHelper.updateParamsFromMap(map);
        navigator.replaceRoute(paramsHelper.asParamsString());
    }

    function setDateRange(value?: DateRange) {
        const map = new Map<URLParam, ParamsDictValue>();
        map.set(QueryProperty.FromDate, value?.from ?? "");
        map.set(QueryProperty.ToDate, value?.to ?? "");
        setSelectedDateRange({
            from: value?.from ?? new Date(),
            to: value?.to ?? new Date(),
        });
        paramsHelper.updateParamsFromMap(map);
        navigator.replaceRoute(paramsHelper.asParamsString());
    }

    function handleDistanceUpdate(data: DistanceData) {
        const map = new Map<URLParam, ParamsDictValue>();
        map.set(QueryProperty.Distance, data.distance ?? "");
        map.set(QueryProperty.Zip, data.zipCode ?? "");
        setDistanceQuery(data);
        paramsHelper.updateParamsFromMap(map);
        navigator.replaceRoute(paramsHelper.asParamsString());
    }

    return (
        <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div
                className="flex flex-col lg:flex-row gap-2 lg:gap-0 
            bg-ivory rounded-3xl lg:rounded-full border
             border-gray-200 p-2 lg:p-4 shadow-sm"
            >
                {/* City Selection */}
                <div className="flex-1 lg:border-r lg:border-gray-200 lg:pr-4">
                    <div
                        className="flex items-center p-2 lg:p-0 rounded-full lg:rounded-none
                     hover:bg-gray-50 lg:hover:bg-transparent transition-colors"
                    >
                        <ShowDistanceSelectionComponent
                            variant={DistanceComponentVariant.Standalone}
                            value={distanceData}
                            onValueChange={handleDistanceUpdate}
                        />
                    </div>
                </div>

                {/* Date Selection */}
                <div className="flex-1 lg:border-r lg:border-gray-200 lg:px-4">
                    <div className="flex items-center w-full p-2 lg:p-0 rounded-full lg:rounded-none hover:bg-gray-50 lg:hover:bg-transparent transition-colors">
                        <CalendarComponent
                            variant={CalendarVariant.Standalone}
                            value={dateRange}
                            onValueChange={(newRange) => setDateRange(newRange)}
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
                            value={comedianQuery}
                            onChange={handleComedianSearch}
                            className="w-full border-gray-200 bg-ivory ring-transparent focus:ring-transparent 
                            shadow-none border-transparent focus:outline-none outline-none"
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
                            value={clubQuery}
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
