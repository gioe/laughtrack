"use client";

import { Theater } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { getDateRangeFromParams } from "@/util/search/util";
import ShowLocationComponent from "../../../components/area";
import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarLayout, { SearchBarSection } from "../../../components/layout";
import { DateRange, DistanceData } from "@/objects/interface";

export default function ComedianDetailSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam, setMultipleTypedParams } =
        useUrlParams();
    // Initial state setup
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

    // Generic update function for all search parameters
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
                <div>
                    <label
                        htmlFor="comedian-detail-zip"
                        className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1 block"
                    >
                        Where
                    </label>
                    <ShowLocationComponent
                        variant={ComponentVariant.Standalone}
                        value={state.distance}
                        onDistanceSelection={handleDistanceSelection}
                        onZipcodeInput={handleZipCodeInput}
                        inputId="comedian-detail-zip"
                    />
                </div>
            </SearchBarSection>

            <SearchBarSection>
                <div>
                    <p
                        id="comedian-detail-dates-label"
                        className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1"
                    >
                        When
                    </p>
                    <CalendarComponent
                        variant={ComponentVariant.Standalone}
                        value={state.dateRange}
                        onValueChange={handleDateRangeSelection}
                        inputId="comedian-detail-dates-label"
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
                    placeholder="Search by club"
                    value={state.club ?? ""}
                    onChange={handleClubSearch}
                    className={styleConfig.inputTextColor}
                />
            </SearchBarSection>
        </SearchBarLayout>
    );
}
