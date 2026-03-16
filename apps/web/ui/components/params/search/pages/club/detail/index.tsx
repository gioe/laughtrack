"use client";

import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";
import { Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { getDateRangeFromParams } from "@/util/search/util";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarLayout, { SearchBarSection } from "../../../components/layout";
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
        <SearchBarLayout>
            <SearchBarSection first>
                <div>
                    <p
                        id="club-detail-dates-label"
                        className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1"
                    >
                        When
                    </p>
                    <CalendarComponent
                        variant={ComponentVariant.Standalone}
                        value={state.dateRange}
                        onValueChange={handleDateRangeSelection}
                        inputId="club-detail-dates-label"
                    />
                </div>
            </SearchBarSection>

            <SearchBarSection last>
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
        </SearchBarLayout>
    );
}
