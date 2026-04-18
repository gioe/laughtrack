"use client";

import React from "react";
import { Minus, Plus } from "lucide-react";
import { useUrlParams } from "@/hooks/useUrlParams";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { DateRange, DistanceData } from "@/objects/interface";
import { getDateRangeFromParams } from "@/util/search/util";
import ShowLocationComponent from "../../params/search/components/area";
import CalendarComponent from "../../params/search/components/calendar";

const MIN_SHOWS_CEILING = 50;

export default function ComedianAdvancedFilters() {
    const { getTypedParam, setTypedParam, setMultipleTypedParams } =
        useUrlParams();

    const distance: DistanceData = {
        distance: getTypedParam(QueryProperty.Distance),
        zipCode: getTypedParam(QueryProperty.Zip),
    };
    const dateRange = getDateRangeFromParams({
        from: getTypedParam(QueryProperty.FromDate),
        to: getTypedParam(QueryProperty.ToDate),
    });
    const minTotalShows: number = getTypedParam("minTotalShows") ?? 0;

    const handleZip = (v: string) => setTypedParam(QueryProperty.Zip, v);
    const handleDistance = (v: string) =>
        setTypedParam(QueryProperty.Distance, v);
    const handleDateRange = (v?: DateRange) =>
        setMultipleTypedParams({ fromDate: v?.from, toDate: v?.to });
    const setMinShows = (n: number) => {
        const clamped = Math.max(0, Math.min(MIN_SHOWS_CEILING, n));
        setTypedParam("minTotalShows", clamped);
    };

    return (
        <div className="space-y-5 mb-6 animate-slideUp">
            <Section label="Where" htmlFor="comedian-filter-zip">
                <ShowLocationComponent
                    variant={ComponentVariant.Standalone}
                    value={distance}
                    onDistanceSelection={handleDistance}
                    onZipcodeInput={handleZip}
                    inputId="comedian-filter-zip"
                />
            </Section>

            <Section label="When" htmlFor="comedian-filter-dates">
                <CalendarComponent
                    variant={ComponentVariant.Standalone}
                    value={dateRange}
                    onValueChange={handleDateRange}
                    inputId="comedian-filter-dates"
                />
            </Section>

            <Section
                label="Minimum upcoming shows"
                htmlFor="comedian-filter-min-shows"
            >
                <Stepper
                    value={minTotalShows}
                    onChange={setMinShows}
                    inputId="comedian-filter-min-shows"
                />
            </Section>
        </div>
    );
}

function Section({
    label,
    htmlFor,
    children,
}: {
    label: string;
    htmlFor: string;
    children: React.ReactNode;
}) {
    return (
        <div>
            <label
                id={htmlFor}
                htmlFor={htmlFor}
                className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2 block"
            >
                {label}
            </label>
            {children}
        </div>
    );
}

function Stepper({
    value,
    onChange,
    inputId,
}: {
    value: number;
    onChange: (n: number) => void;
    inputId: string;
}) {
    return (
        <div className="flex items-center gap-3" id={inputId}>
            <button
                type="button"
                onClick={() => onChange(value - 1)}
                disabled={value <= 0}
                aria-label="Decrement minimum shows"
                className="p-2 rounded-md border border-gray-200 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
                <Minus className="w-4 h-4" />
            </button>
            <span className="font-dmSans text-[16px] min-w-[3ch] text-center tabular-nums">
                {value === 0 ? "Any" : value}
            </span>
            <button
                type="button"
                onClick={() => onChange(value + 1)}
                aria-label="Increment minimum shows"
                className="p-2 rounded-md border border-gray-200 hover:bg-gray-100 transition-colors"
            >
                <Plus className="w-4 h-4" />
            </button>
        </div>
    );
}
