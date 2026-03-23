"use client";

import { useEffect, useRef } from "react";
import { Theater, Users } from "lucide-react";
import { useSession } from "next-auth/react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { getDateRangeFromParams } from "@/util/search/util";
import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";
import ShowLocationComponent from "../../../components/area";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarLayout, { SearchBarSection } from "../../../components/layout";
import { DateRange, DistanceData } from "@/objects/interface";

// Per-entity composers remain separate: each has a distinct filter set
// (show: location + calendar + comedian + club; club: location + club; comedian: name only).
// The structural wrapper is already extracted as SearchBarLayout/SearchBarSection.
// A shared HOC would add indirection without reducing the per-entity JSX sections.
export default function ShowSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam, setMultipleTypedParams } =
        useUrlParams();
    const session = useSession();
    const hasSeeded = useRef(false);

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

    useEffect(() => {
        if (hasSeeded.current || session.status === "loading") return;
        hasSeeded.current = true;
        if (state.distance.zipCode) return;
        const zip =
            session.data?.profile?.zipCode ??
            (typeof window !== "undefined"
                ? localStorage.getItem("laughtrack_zip")
                : null);
        if (zip) setMultipleTypedParams({ zip, distance: "10" });
    }, [
        session.status,
        session.data,
        state.distance.zipCode,
        setMultipleTypedParams,
    ]);

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
                <div>
                    <label
                        htmlFor="show-all-zip"
                        className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1 block"
                    >
                        Where
                    </label>
                    <ShowLocationComponent
                        variant={ComponentVariant.Standalone}
                        value={state.distance}
                        onDistanceSelection={handleDistanceSelection}
                        onZipcodeInput={handleZipCodeInput}
                        inputId="show-all-zip"
                    />
                </div>
            </SearchBarSection>

            <SearchBarSection>
                <div>
                    <p
                        id="show-all-dates-label"
                        className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1"
                    >
                        When
                    </p>
                    <CalendarComponent
                        variant={ComponentVariant.Standalone}
                        value={state.dateRange}
                        onValueChange={handleDateRangeSelection}
                        inputId="show-all-dates-label"
                    />
                </div>
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
