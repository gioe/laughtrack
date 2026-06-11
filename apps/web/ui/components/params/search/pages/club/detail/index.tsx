"use client";

import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";
import { Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { getDateRangeFromParams } from "@/util/search/util";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarLayout, { SearchChipRow } from "../../../components/layout";
import { DateRange } from "@/objects/interface";

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

    const handleComedianSearch = (value: string) =>
        setTypedParam(QueryProperty.Comedian, value);

    const handleDateRangeSelection = (value?: DateRange) => {
        setMultipleTypedParams({
            fromDate: value?.from,
            toDate: value?.to,
        });
    };

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
                <CalendarComponent
                    variant={ComponentVariant.Standalone}
                    value={state.dateRange}
                    onValueChange={handleDateRangeSelection}
                />
            </SearchChipRow>
        </SearchBarLayout>
    );
}
