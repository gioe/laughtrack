"use client";

import ShowLocationComponent from "../../../components/area";
import TextInputComponent from "../../../components/textInput";
import { ChangeEvent, useState } from "react";
import { Theater } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { DistanceData } from "@/util/search/util";
import { ParamKeys, useUrlParams } from "@/hooks/useUrlParams";

export default function ClubSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam } = useUrlParams();

    const club = getTypedParam(QueryProperty.Club);
    const distance = getTypedParam(QueryProperty.Distance);
    const zipCode = getTypedParam(QueryProperty.Zip);

    // Initial state setup
    const initialState = {
        club,
        distance: { distance, zipCode } as DistanceData,
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

    const handleClubSearch = (value: string) =>
        updateSearchParams(QueryProperty.Club, value, (prev) => ({
            ...prev,
            club: value,
        }));

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
        <div className="flex items-center bg-ivory rounded-full border border-gray-200 px-4 py-2 shadow-sm max-w-3xl w-full">
            <div className="flex items-center flex-1 border-r border-gray-200 pr-4">
                <ShowLocationComponent
                    variant={ComponentVariant.Standalone}
                    value={searchState.distance}
                    onDistanceSelection={handleDistanceSelection}
                    onZipcodeInput={handleZipCodeInput}
                />
            </div>

            <div className="flex items-center px-4">
                <TextInputComponent
                    icon={
                        <Theater
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    placeholder="Search for club"
                    value={searchState.club ?? ""}
                    onChange={handleClubSearch}
                    className="border-gray-200 pr-4 bg-ivory ring-transparent focus:ring-transparent shadow-none border-transparent"
                />
            </div>
        </div>
    );
}
