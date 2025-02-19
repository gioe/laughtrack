"use client";

import ShowLocationComponent from "../../../components/area";
import TextInputComponent from "../../../components/textInput";
import { Theater } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarContainer from "../../../components/container";
import { DistanceData } from "@/objects/interface";

export default function ClubSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam } = useUrlParams();

    // Initial state setup
    const state = {
        club: getTypedParam(QueryProperty.Club),
        distance: {
            distance: getTypedParam(QueryProperty.Distance),
            zipCode: getTypedParam(QueryProperty.Zip),
        } as DistanceData,
    };

    const handleClubSearch = (value: string) =>
        setTypedParam(QueryProperty.Club, value);

    const handleZipCodeInput = (value: string) =>
        setTypedParam(QueryProperty.Zip, value);

    const handleDistanceSelection = (distance: string) =>
        setTypedParam(QueryProperty.Distance, distance);

    return (
        <SearchBarContainer maxWidth="max-w-4xl">
            <div className={"lg:pr-4 lg:border-r lg:border-black"}>
                <ShowLocationComponent
                    variant={ComponentVariant.Standalone}
                    value={state.distance}
                    onDistanceSelection={handleDistanceSelection}
                    onZipcodeInput={handleZipCodeInput}
                />
            </div>

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
