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
        <SearchBarContainer maxWidth="max-w-7xl">
            <div className="flex flex-col lg:flex-row items-center lg:divide-x divide-white/10">
                <div className="w-full lg:w-auto mb-4 lg:mb-0 lg:pr-6">
                    <ShowLocationComponent
                        variant={ComponentVariant.Standalone}
                        value={state.distance}
                        onDistanceSelection={handleDistanceSelection}
                        onZipcodeInput={handleZipCodeInput}
                    />
                </div>

                <div className="w-full lg:w-auto lg:pl-6">
                    <TextInputComponent
                        icon={
                            <Theater
                                className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                            />
                        }
                        placeholder="Search for club"
                        value={state.club ?? ""}
                        onChange={handleClubSearch}
                        className={styleConfig.inputTextColor}
                    />
                </div>
            </div>
        </SearchBarContainer>
    );
}
