"use client";

import React from "react";
import { Minus, Plus } from "lucide-react";
import { useUrlParams } from "@/hooks/useUrlParams";
import { ComponentVariant, QueryProperty } from "@/objects/enum";
import { DateRange, DistanceData } from "@/objects/interface";
import { getDateRangeFromParams } from "@/util/search/util";
import { MIN_UPCOMING_SHOWS_CEILING } from "@/util/filter/util";
import ShowLocationComponent from "../../params/search/components/area";
import CalendarComponent from "../../params/search/components/calendar";

const ZIP_INPUT_ID = "comedian-filter-zip";
const DATES_LABEL_ID = "comedian-filter-dates-label";
const MIN_SHOWS_LABEL_ID = "comedian-filter-min-shows-label";

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
    const minUpcomingShows: number = getTypedParam(
        QueryProperty.MinUpcomingShows,
    );

    const handleZip = (v: string) => setTypedParam(QueryProperty.Zip, v);
    const handleDistance = (v: string) =>
        setTypedParam(QueryProperty.Distance, v);
    const handleDateRange = (v?: DateRange) =>
        setMultipleTypedParams({ fromDate: v?.from, toDate: v?.to });
    const setMinShows = (n: number) => {
        const clamped = Math.max(0, Math.min(MIN_UPCOMING_SHOWS_CEILING, n));
        setTypedParam(QueryProperty.MinUpcomingShows, clamped);
    };

    return (
        <div className="space-y-5 mb-6 animate-slideUp">
            <Section label="Where" htmlFor={ZIP_INPUT_ID}>
                <ShowLocationComponent
                    variant={ComponentVariant.Standalone}
                    value={distance}
                    onDistanceSelection={handleDistance}
                    onZipcodeInput={handleZip}
                    inputId={ZIP_INPUT_ID}
                />
            </Section>

            <Section label="When" labelId={DATES_LABEL_ID}>
                <CalendarComponent
                    variant={ComponentVariant.Standalone}
                    value={dateRange}
                    onValueChange={handleDateRange}
                    inputId={DATES_LABEL_ID}
                />
            </Section>

            <Section
                label="Minimum upcoming shows"
                labelId={MIN_SHOWS_LABEL_ID}
            >
                <Stepper
                    value={minUpcomingShows}
                    onChange={setMinShows}
                    labelledBy={MIN_SHOWS_LABEL_ID}
                />
            </Section>
        </div>
    );
}

function Section({
    label,
    htmlFor,
    labelId,
    children,
}: {
    label: string;
    htmlFor?: string;
    labelId?: string;
    children: React.ReactNode;
}) {
    return (
        <div>
            <label
                {...(htmlFor ? { htmlFor } : {})}
                {...(labelId ? { id: labelId } : {})}
                className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-2 block"
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
    labelledBy,
}: {
    value: number;
    onChange: (n: number) => void;
    labelledBy: string;
}) {
    const atMin = value <= 0;
    const atMax = value >= MIN_UPCOMING_SHOWS_CEILING;
    return (
        <div className="flex items-center gap-3">
            <button
                type="button"
                onClick={() => onChange(value - 1)}
                disabled={atMin}
                aria-label="Decrement minimum shows"
                className="p-2 rounded-md border border-gray-200 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
                <Minus className="w-4 h-4" />
            </button>
            <span
                role="spinbutton"
                aria-labelledby={labelledBy}
                aria-valuenow={value}
                aria-valuemin={0}
                aria-valuemax={MIN_UPCOMING_SHOWS_CEILING}
                aria-valuetext={value === 0 ? "Any" : String(value)}
                tabIndex={0}
                className="font-dmSans text-body min-w-[3ch] text-center tabular-nums"
            >
                {value === 0 ? "Any" : value}
            </span>
            <button
                type="button"
                onClick={() => onChange(value + 1)}
                disabled={atMax}
                aria-label="Increment minimum shows"
                className="p-2 rounded-md border border-gray-200 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
                <Plus className="w-4 h-4" />
            </button>
        </div>
    );
}
