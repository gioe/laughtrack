"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ChangeEvent, useState } from "react";
import { Theater } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { Navigator } from "@/objects/class/navigate/Navigator";
import { getDistanceDataFromParams } from "@/util/search/util";
import ShowLocationComponent from "../../../components/area";
import TextInputComponent from "../../../components/textInput";

export default function ClubSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const searchParams = useSearchParams();
    const navigator = new Navigator(usePathname(), useRouter());

    // Initial state setup
    const initialState = {
        club: searchParams.get(QueryProperty.Club) as string,
        distance: getDistanceDataFromParams(searchParams),
    };

    // Combined state management
    const [searchState, setSearchState] = useState(initialState);

    const updateSearchParams = <T extends keyof typeof initialState>(
        param: QueryProperty,
        value: any,
        stateUpdater: (prevState: typeof initialState) => typeof initialState,
    ) => {
        setSearchState(stateUpdater);
        // navigator.replaceRoute(paramsHelper.asParamsString());
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
                    value={searchState.club}
                    onChange={handleClubSearch}
                    className="border-gray-200 pr-4 bg-ivory ring-transparent focus:ring-transparent shadow-none border-transparent"
                />
            </div>
        </div>
    );
}
