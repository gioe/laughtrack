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
import { MapPin, Theater } from "lucide-react";
import { CityDTO } from "@/lib/data/cities/getCities";
import { DropdownComponent } from "../../dropdown";
import TextInputComponent from "../../input/search/text/input";
import { useStyleContext } from "@/contexts/StyleProvider";
import { QueryProperty } from "@/objects/enum";

export default function ClubSearchBar() {
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
    const [clubQuery, setClubQuery] = useState(currentClubQuery);

    const selectableCities = cityList.cities.map((city: CityDTO) => ({
        id: city.id,
        value: city.name,
        display: city.name,
    }));

    function handleSearch(value: string) {
        const map = new Map<URLParam, ParamsDictValue>();
        map.set(QueryProperty.Query, value);
        setClubQuery(value);
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
        <div className="flex items-center bg-ivory rounded-full border border-gray-200 px-4 py-2 shadow-sm max-w-xl w-full">
            {/* Location input */}
            <div className="flex items-center flex-1 border-r border-gray-200 pr-4">
                <DropdownComponent
                    icon={
                        <MapPin
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    name="city"
                    placeholder="Where"
                    items={selectableCities}
                    onChange={handleSelection}
                    value={selectedValue}
                    className={`text-[16px] text-cedar rounded-lg font-dmSams ring-transparent focus:ring-transparent 
                        shadow-none border-transparent focus:outline-none outline-none`}
                />
            </div>

            {/* Date input */}
            <div className="flex items-center flex-1 px-4">
                <TextInputComponent
                    icon={
                        <Theater
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    placeholder="Search for club"
                    value={clubQuery}
                    onChange={handleSearch}
                    className="border-gray-200 pr-4 bg-ivory ring-transparent focus:ring-transparent shadow-none border-transparent"
                />
            </div>
        </div>
    );
}
