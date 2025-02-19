"use client";

import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";
import { Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { DateRange, getDateRangeFromParams } from "@/util/search/util";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarContainer from "../../../components/container";

export default function ClubDetailSearchBar() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const { getTypedParam, setTypedParam, setMultipleTypedParams } =
        useUrlParams();

    // Initial state setup
    const state = {
        comedian: getTypedParam(QueryProperty.Comedian),
        dateRange: getDateRangeFromParams({
            from: getTypedParam(QueryProperty.FromDate),
            to: getTypedParam(QueryProperty.ToDate),
        }),
    };

    // Combined state management

    const handleComedianSearch = (value: string) =>
        setTypedParam(QueryProperty.Comedian, value);

    const handleDateRangeSelection = (value?: DateRange) => {
        setMultipleTypedParams({
            fromDate: value?.from,
            toDate: value?.to,
        });
    };

    return (
        <SearchBarContainer maxWidth="max-w-2xl">
            <div className={"lg:pr-4 lg:border-r lg:border-black"}>
                <CalendarComponent
                    variant={ComponentVariant.Standalone}
                    value={state.dateRange}
                    onValueChange={handleDateRangeSelection}
                />
            </div>
            <TextInputComponent
                icon={
                    <Users className={`w-5 h-5 ${styleConfig.iconTextColor}`} />
                }
                placeholder="Search for comedian"
                value={state.comedian ?? ""}
                onChange={handleComedianSearch}
            />
        </SearchBarContainer>
    );
}
