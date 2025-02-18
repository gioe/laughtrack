"use client";

import ShowLocationComponent from "../../../components/area";
import TextInputComponent from "../../../components/textInput";
import { ChangeEvent } from "react";
import { Theater } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { DistanceData } from "@/util/search/util";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarContainer from "../../../components/container";

export default function ClubSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam } = useUrlParams();

    const club = getTypedParam(QueryProperty.Club);
    const distance = getTypedParam(QueryProperty.Distance);
    const zipCode = getTypedParam(QueryProperty.Zip);

    // Initial state setup
    const state = {
        club,
        distance: { distance, zipCode } as DistanceData,
    };

    const handleClubSearch = (queryString: string) =>
        setTypedParam(QueryProperty.Club, queryString);

    const handleDistanceSelection = (distance: string) =>
        setTypedParam(QueryProperty.Distance, distance);

    const handleZipCodeInput = (event: ChangeEvent<HTMLInputElement>) =>
        setTypedParam(QueryProperty.Zip, event.target.value);

    return (
        <SearchBarContainer>
            <ShowLocationComponent
                variant={ComponentVariant.Standalone}
                value={state.distance}
                onDistanceSelection={handleDistanceSelection}
                onZipcodeInput={handleZipCodeInput}
            />

            <TextInputComponent
                icon={
                    <Theater
                        className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                    />
                }
                placeholder="Search for club"
                value={state.club ?? ""}
                onChange={handleClubSearch}
            />
        </SearchBarContainer>
    );
}
