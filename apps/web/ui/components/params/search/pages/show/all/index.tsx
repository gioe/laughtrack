"use client";

import { Theater, Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { getDateRangeFromParams } from "@/util/search/util";
import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";
import ShowLocationComponent from "../../../components/area";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarLayout, { SearchBarSection } from "../../../components/layout";
import { DateRange, DistanceData } from "@/objects/interface";

export default function ShowSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam, setMultipleTypedParams } =
        useUrlParams();

    const state = {
        comedian: getTypedParam(QueryProperty.Comedian),
        club: getTypedParam(QueryProperty.Club),
        distance: {
            distance: getTypedParam(QueryProperty.Distance),
            zipCode: getTypedParam(QueryProperty.Zip),
        } as DistanceData,
        dateRange: getDateRangeFromParams({
            from: getTypedParam(QueryProperty.FromDate),
            to: getTypedParam(QueryProperty.ToDate),
        }),
    };

    const handleComedianSearch = (value: string) =>
        setTypedParam(QueryProperty.Comedian, value);

    const handleClubSearch = (value: string) =>
        setTypedParam(QueryProperty.Club, value);

    const handleDateRangeSelection = (value?: DateRange) => {
        setMultipleTypedParams({
            fromDate: value?.from,
            toDate: value?.to,
        });
    };

    const handleDistanceSelection = (distance: string) =>
        setTypedParam(QueryProperty.Distance, distance);

    const handleZipCodeInput = (value: string) =>
        setTypedParam(QueryProperty.Zip, value);

    return (
        <SearchBarLayout>
            <SearchBarSection first>
                <ShowLocationComponent
                    variant={ComponentVariant.Standalone}
                    value={state.distance}
                    onDistanceSelection={handleDistanceSelection}
                    onZipcodeInput={handleZipCodeInput}
                />
            </SearchBarSection>

            <SearchBarSection>
                <CalendarComponent
                    variant={ComponentVariant.Standalone}
                    value={state.dateRange}
                    onValueChange={handleDateRangeSelection}
                />
            </SearchBarSection>

            <SearchBarSection>
                <TextInputComponent
                    icon={
                        <Users
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    placeholder="Search for comedian"
                    value={state.comedian ?? ""}
                    onChange={handleComedianSearch}
                    className={styleConfig.inputTextColor}
                />
            </SearchBarSection>

            <SearchBarSection last>
                <TextInputComponent
                    icon={
                        <Theater
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                    }
                    placeholder="Search by club"
                    value={state.club ?? ""}
                    onChange={handleClubSearch}
                    className={styleConfig.inputTextColor}
                />
            </SearchBarSection>
        </SearchBarLayout>
    );
}
