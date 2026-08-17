"use client";

import { useEffect, useRef } from "react";
import { Users } from "lucide-react";
import { useSession } from "next-auth/react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { getDateRangeFromParams } from "@/util/search/util";
import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";
import ShowLocationComponent from "../../../components/area";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarLayout, { SearchChipRow } from "../../../components/layout";
import { DateRange, DistanceData } from "@/objects/interface";

// Per-entity composers remain separate: each has a distinct filter set
// (show: location + calendar + comedian; club: location + club; comedian: name only).
// The structural wrapper is already extracted as SearchBarLayout/SearchChipRow.
// A shared HOC would add indirection without reducing the per-entity JSX sections.
//
// Shows intentionally exposes ONLY a comedian search input, not a club input.
// This matches iOS's single-axis model on the Shows tab — two simultaneous
// text inputs is not a common consumer-search convention (Spotify, Apple
// Music, Netflix, etc. all use a single field). Filtering shows by club
// happens through location + filter chips instead.
export default function ShowSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam, setMultipleTypedParams } =
        useUrlParams();
    const session = useSession();
    const hasSeeded = useRef(false);

    const state = {
        comedian: getTypedParam(QueryProperty.Comedian),
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

    // Drop any stale `club` URL param on mount — the input was removed when we
    // converged on iOS's single-axis search model, and without a visible
    // surface the filter becomes a hidden, unclearable state. Older shared
    // links land here and get the filter cleared rather than being stuck.
    const staleClub = getTypedParam(QueryProperty.Club);
    useEffect(() => {
        if (staleClub) {
            setTypedParam(QueryProperty.Club, "");
        }
    }, [staleClub, setTypedParam]);

    const handleComedianSearch = (value: string) =>
        setTypedParam(QueryProperty.Comedian, value);

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
            <TextInputComponent
                icon={
                    <Users className={`w-5 h-5 ${styleConfig.iconTextColor}`} />
                }
                placeholder="Search comedians"
                value={state.comedian ?? ""}
                onChange={handleComedianSearch}
                className={styleConfig.inputTextColor}
            />
            <SearchChipRow ariaLabel="Show search filters">
                <ShowLocationComponent
                    variant={ComponentVariant.Standalone}
                    value={state.distance}
                    onDistanceSelection={handleDistanceSelection}
                    onZipcodeInput={handleZipCodeInput}
                    inputId="show-all-zip"
                />
                <CalendarComponent
                    variant={ComponentVariant.Standalone}
                    value={state.dateRange}
                    onValueChange={handleDateRangeSelection}
                />
            </SearchChipRow>
        </SearchBarLayout>
    );
}
