"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ChangeEvent, useState } from "react";
import { MapPin, Theater } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import {
    ParamsDictValue,
    SearchParamsHelper,
    URLParam,
} from "@/objects/class/params/SearchParamsHelper";
import { Navigator } from "@/objects/class/navigate/Navigator";
import TextInputComponent from "@/ui/components/input/search/text/input";
import ShowDistanceSelectionComponent from "@/ui/components/area";
import { DistanceData, getDistanceDataFromParams } from "@/util/search/util";

export default function ClubSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());

    const currentClubQuery = paramsHelper.getParamValue(
        QueryProperty.Club,
    ) as string;

    const [clubQuery, setClubQuery] = useState(currentClubQuery);
    const [distanceData, setDistanceQuery] = useState(
        getDistanceDataFromParams(paramsHelper),
    );

    function handleClubSearch(value: string) {
        const map = new Map<URLParam, ParamsDictValue>();
        map.set(QueryProperty.Club, value);
        setClubQuery(value);
        paramsHelper.updateParamsFromMap(map);
        navigator.replaceRoute(paramsHelper.asParamsString());
    }

    const handleDistanceSelection = (distance: string) => {
        // onSelect({
        //     ...selectedValues,
        //     distance,
        // });
    };

    const handleZipCodeInput = (event: ChangeEvent<HTMLInputElement>) => {
        // onSelect({
        //     distance: selectedValues?.distance,
        //     zipCode: event.target.value,
        // });
    };

    return (
        <div className="flex items-center bg-ivory rounded-full border border-gray-200 px-4 py-2 shadow-sm max-w-3xl w-full">
            <div className="flex items-center flex-1 border-r border-gray-200 pr-4">
                <ShowDistanceSelectionComponent
                    variant={ComponentVariant.Standalone}
                    value={distanceData}
                    onDistanceSelection={handleDistanceSelection}
                    onZipcodeInput={handleZipCodeInput}
                />
            </div>

            {/* Date input */}
            <div className="flex items-center px-4">
                <TextInputComponent
                    icon={
                        <Theater
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    placeholder="Search for club"
                    value={clubQuery}
                    onChange={handleClubSearch}
                    className="border-gray-200 pr-4 bg-ivory ring-transparent focus:ring-transparent shadow-none border-transparent"
                />
            </div>
        </div>
    );
}
