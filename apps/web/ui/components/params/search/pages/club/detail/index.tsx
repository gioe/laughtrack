"use client";

import CalendarComponent from "../../../components/calendar";
import TextInputComponent from "../../../components/textInput";
import { Users } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { getDateRangeFromParams } from "@/util/search/util";
import { useUrlParams } from "@/hooks/useUrlParams";
import SearchBarContainer from "../../../components/container";
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
        <SearchBarContainer maxWidth="max-w-7xl">
            <div className="flex flex-col lg:flex-row items-center lg:divide-x divide-white/10">
                <div className="w-full lg:w-auto mb-4 lg:mb-0 lg:pr-6">
                    <CalendarComponent
                        variant={ComponentVariant.Standalone}
                        value={state.dateRange}
                        onValueChange={handleDateRangeSelection}
                    />
                </div>

                <div className="w-full lg:w-auto lg:pl-6">
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
                </div>
            </div>
        </SearchBarContainer>
    );
}
