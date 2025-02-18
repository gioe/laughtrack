"use client";

import { ChangeEvent } from "react";
import { Theater, Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import {
    DateRange,
    DistanceData,
    getDateRangeFromParams,
} from "@/util/search/util";
import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";
import ShowLocationComponent from "../../../components/area";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarContainer from "../../../components/container";

export default function ShowSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam } = useUrlParams();

    const comedian = getTypedParam(QueryProperty.Comedian);
    const club = getTypedParam(QueryProperty.Club);
    const distance = getTypedParam(QueryProperty.Distance);
    const zipCode = getTypedParam(QueryProperty.Zip);
    const from = getTypedParam(QueryProperty.FromDate);
    const to = getTypedParam(QueryProperty.ToDate);

    // Initial state setup
    const state = {
        comedian,
        club,
        distance: { distance, zipCode } as DistanceData,
        dateRange: getDateRangeFromParams({
            from,
            to,
        }),
    };

    // Simplified handler functions
    const handleComedianSearch = (value: string) =>
        setTypedParam(QueryProperty.Comedian, value);

    const handleClubSearch = (value: string) =>
        setTypedParam(QueryProperty.Club, value);

    const handleDateRangeSelection = (value?: DateRange) => {
        setTypedParam(QueryProperty.FromDate, value?.from ?? new Date());
        setTypedParam(QueryProperty.ToDate, value?.to);
    };

    const handleDistanceSelection = (distance: string) =>
        setTypedParam(QueryProperty.Distance, distance);

    const handleZipCodeInput = (event: ChangeEvent<HTMLInputElement>) =>
        setTypedParam(QueryProperty.Distance, event.target.value);

    return (
        <SearchBarContainer>
            <ShowLocationComponent
                variant={ComponentVariant.Standalone}
                value={state.distance}
                onDistanceSelection={handleDistanceSelection}
                onZipcodeInput={handleZipCodeInput}
            />
            <CalendarComponent
                variant={ComponentVariant.Standalone}
                value={state.dateRange}
                onValueChange={handleDateRangeSelection}
            />
            <TextInputComponent
                icon={
                    <Users className={`w-5 h-5 ${styleConfig.iconTextColor}`} />
                }
                placeholder="Search for comedian"
                value={state.comedian ?? ""}
                onChange={handleComedianSearch}
            />
            <TextInputComponent
                icon={
                    <Theater
                        className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                    />
                }
                placeholder="Search by club"
                value={state.club ?? ""}
                onChange={handleClubSearch}
            />
        </SearchBarContainer>
    );
}
