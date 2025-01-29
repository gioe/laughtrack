"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useCityContext } from "@/contexts/CityProvider";
import { Calendar, ChevronsUpDownIcon, MapPin, Users } from "lucide-react";
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
import CalendarFormComponent, { DateRange } from "@/ui/components/calendar";
import { QueryProperty } from "@/objects/enum";

export default function ShowSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const cityList = useCityContext();

    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());
    const currentSelection = paramsHelper.getParamValue(
        QueryProperty.City,
    ) as string;
    const currentQuery = paramsHelper.getParamValue(
        QueryProperty.Query,
    ) as string;

    const currentDateRange = {
        from: new Date(
            paramsHelper.getParamValue(QueryProperty.FromDate) as string,
        ),
        to: new Date(
            paramsHelper.getParamValue(QueryProperty.ToDate) as string,
        ),
    };

    const [selectedValue, setSelectedValue] = useState(currentSelection);
    const [dateRange, setSelectedDateRange] = useState(currentDateRange);
    const [comedianQuery, setComedianQuery] = useState(currentQuery);

    const selectableCities = cityList.cities.map((city: CityDTO) => ({
        id: city.id,
        value: city.name,
        display: city.name,
    }));

    function handleSearch(value: string) {
        const map = new Map<URLParam, ParamsDictValue>();
        map.set(QueryProperty.Query, value);
        setComedianQuery(value);
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
        <div className="flex items-center bg-ivory rounded-full border border-gray-200 px-4 py-2 shadow-sm max-w-4xl w-full">
            {/* Location input */}
            <div className="flex items-center flex-1 border-r border-gray-200 pr-4">
                <DropdownComponent
                    icon={
                        <MapPin
                            className={`size-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    name="city"
                    placeholder="City"
                    items={selectableCities}
                    onChange={handleSelection}
                    value={selectedValue}
                    className={`text-[16px] text-cedar rounded-lg font-dmSams ring-transparent focus:ring-transparent 
                        shadow-none border-transparent focus:outline-none outline-none`}
                />
            </div>

            <div className="w-5/12 pl-6 py-4">
                <CalendarFormComponent
                    name="dates"
                    value={dateRange}
                    placeholder="When"
                    onValueChange={(newRange) => setDateRange(newRange)}
                    className={`text-[16px] text-cedar rounded-lg px-3 ring-transparent 
                        focus:ring-transparent border-transparent focus:outline-none outline-none`}
                    icon={
                        <Calendar
                            className={`size-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    chevrons={
                        <ChevronsUpDownIcon
                            className={"w-3 h-3 pl-3"}
                            style={{ opacity: 0.5 }}
                        />
                    }
                    textSize="text-[16px]"
                />
            </div>

            {/* Date input */}
            <div className="flex items-center flex-1 px-4">
                <TextInputComponent
                    icon={
                        <Users
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    placeholder="Search by comedian"
                    value={comedianQuery}
                    onChange={handleSearch}
                    className="border-gray-200 pr-4 bg-ivory ring-transparent focus:ring-transparent 
    shadow-none border-transparent focus:outline-none outline-none"
                />
            </div>
        </div>
    );
}
