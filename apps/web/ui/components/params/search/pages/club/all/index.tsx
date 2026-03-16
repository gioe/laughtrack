"use client";

import { Theater } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarLayout, { SearchBarSection } from "../../../components/layout";
import ShowLocationComponent from "../../../components/area";
import TextInputComponent from "../../../components/textInput";
import { DistanceData } from "@/objects/interface";

export default function ClubSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam } = useUrlParams();

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
        <SearchBarLayout>
            <SearchBarSection first>
                <div>
                    <label
                        htmlFor="club-all-zip"
                        className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1 block"
                    >
                        Where
                    </label>
                    <ShowLocationComponent
                        variant={ComponentVariant.Standalone}
                        value={state.distance}
                        onDistanceSelection={handleDistanceSelection}
                        onZipcodeInput={handleZipCodeInput}
                        inputId="club-all-zip"
                    />
                </div>
            </SearchBarSection>

            <SearchBarSection last>
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
            </SearchBarSection>
        </SearchBarLayout>
    );
}
