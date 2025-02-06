"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useCityContext } from "@/contexts/CityProvider";
import { Calendar, ChevronsUpDown, MapPin, Theater, Users } from "lucide-react";
import { CityDTO } from "@/lib/data/cities/getCities";
import { useStyleContext } from "@/contexts/StyleProvider";
import {
    ParamsDictValue,
    SearchParamsHelper,
    URLParam,
} from "@/objects/class/params/SearchParamsHelper";
import { Navigator } from "@/objects/class/navigate/Navigator";
import DropdownComponent from "@/ui/components/dropdown";
import TextInputComponent from "@/ui/components/input/search/text/input";
import { CalendarVariant, DateRange } from "@/ui/components/calendar";
import { QueryProperty } from "@/objects/enum";
import CalendarComponent from "@/ui/components/calendar";

export default function ShowSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const cityList = useCityContext();

    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());
    const currentSelection = paramsHelper.getParamValue(
        QueryProperty.City,
    ) as string;

    const currentComedianQuery = paramsHelper.getParamValue(
        QueryProperty.Comedian,
    ) as string;
    const currentClubQuery = paramsHelper.getParamValue(
        QueryProperty.Club,
    ) as string;

    const getDateRange = () => {
        const fromString = paramsHelper.getParamValue(
            QueryProperty.FromDate,
        ) as string;
        const toString = paramsHelper.getParamValue(
            QueryProperty.ToDate,
        ) as string;

        const from = new Date(fromString);
        const to = new Date(toString);

        if (isNaN(from.getTime()) && isNaN(to.getTime())) {
            return undefined;
        }

        return { from, to };
    };

    const [selectedValue, setSelectedValue] = useState(currentSelection);
    const [dateRange, setSelectedDateRange] = useState(getDateRange());
    const [comedianQuery, setComedianQuery] = useState(currentComedianQuery);
    const [clubQuery, setClubQuery] = useState(currentClubQuery);

    const selectableCities = cityList.cities.map((city: CityDTO) => ({
        id: city.id,
        value: city.name,
        display: city.name,
    }));

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

    function handleSelection(value: string) {
        const map = new Map<URLParam, ParamsDictValue>();
        map.set(QueryProperty.City, value);
        setSelectedValue(value);
        paramsHelper.updateParamsFromMap(map);
        navigator.replaceRoute(paramsHelper.asParamsString());
    }

    return (
        <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col lg:flex-row gap-2 lg:gap-0 bg-ivory rounded-3xl lg:rounded-full border border-gray-200 p-2 lg:p-4 shadow-sm">
                {/* City Selection */}
                <div className="flex-1 lg:border-r lg:border-gray-200 lg:pr-4">
                    <div className="flex items-center w-full p-2 lg:p-0 rounded-full lg:rounded-none hover:bg-gray-50 lg:hover:bg-transparent transition-colors">
                        <DropdownComponent
                            icon={
                                <MapPin
                                    className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                                />
                            }
                            name="city"
                            placeholder="City"
                            items={selectableCities}
                            onChange={handleSelection}
                            value={selectedValue}
                            className="w-full text-[16px] text-cedar rounded-lg font-dmSams ring-transparent focus:ring-transparent 
                            shadow-none border-transparent focus:outline-none outline-none"
                        />
                    </div>
                </div>

                {/* Date Selection */}
                <div className="flex-1 lg:border-r lg:border-gray-200 lg:px-4">
                    <div className="flex items-center w-full p-2 lg:p-0 rounded-full lg:rounded-none hover:bg-gray-50 lg:hover:bg-transparent transition-colors">
                        <CalendarComponent
                            variant={CalendarVariant.Standalone}
                            name="dates"
                            value={dateRange}
                            placeholder="When"
                            onValueChange={(newRange) => setDateRange(newRange)}
                            className="w-full text-[16px] text-cedar rounded-lg ring-transparent 
                            focus:ring-transparent border-transparent focus:outline-none outline-none"
                            icon={
                                <Calendar
                                    className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                                />
                            }
                            chevrons={
                                <ChevronsUpDown className="w-3 h-3 ml-2 text-cedar" />
                            }
                            textSize="text-[16px]"
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
