"use client";

import { Theater } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarLayout, { SearchChipRow } from "../../../components/layout";
import ShowLocationComponent from "../../../components/area";
import TextInputComponent from "../../../components/textInput";
import { DistanceData } from "@/objects/interface";

// Per-entity composers remain separate: each has a distinct filter set
// (show: location + calendar + comedian + club; club: location + club; comedian: name only).
// The structural wrapper is already extracted as SearchBarLayout/SearchChipRow.
// A shared HOC would add indirection without reducing the per-entity JSX sections.
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
            <TextInputComponent
                icon={
                    <Theater
                        className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                    />
                }
                placeholder="Search clubs"
                value={state.club ?? ""}
                onChange={handleClubSearch}
                className={styleConfig.inputTextColor}
            />
            <SearchChipRow ariaLabel="Club search filters">
                <ShowLocationComponent
                    variant={ComponentVariant.Standalone}
                    value={state.distance}
                    onDistanceSelection={handleDistanceSelection}
                    onZipcodeInput={handleZipCodeInput}
                    inputId="club-all-zip"
                    dropdownId="club-all-distance-listbox"
                />
            </SearchChipRow>
        </SearchBarLayout>
    );
}
