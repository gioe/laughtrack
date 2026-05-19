"use client";

import { useMemo } from "react";
import { useUrlParams } from "@/hooks/useUrlParams";
import { QueryProperty } from "@/objects/enum";

// Mirrors iOS Search's "Tonight / This Week / Near Me" affordance row — quick
// presets that the user can apply without opening the WHEN calendar dropdown.
// The calendar still owns the precise date-range UI; this row is for the
// common cases (today, this weekend, next 7 days).

function toDateKey(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
}

function dateAtOffset(today: Date, offsetDays: number): Date {
    const next = new Date(today);
    next.setDate(next.getDate() + offsetDays);
    return next;
}

function buildShortcuts(
    today: Date,
): { label: string; from: Date; to: Date }[] {
    const dayOfWeek = today.getDay(); // 0 = Sunday, 6 = Saturday
    // "This Weekend" — upcoming Saturday + Sunday. If we're already on Saturday
    // or Sunday, we use today + tomorrow (collapsing if Sunday).
    let weekendStart: Date;
    let weekendEnd: Date;
    if (dayOfWeek === 0) {
        weekendStart = today;
        weekendEnd = today;
    } else if (dayOfWeek === 6) {
        weekendStart = today;
        weekendEnd = dateAtOffset(today, 1);
    } else {
        const daysUntilSaturday = 6 - dayOfWeek;
        weekendStart = dateAtOffset(today, daysUntilSaturday);
        weekendEnd = dateAtOffset(today, daysUntilSaturday + 1);
    }

    return [
        { label: "Tonight", from: today, to: today },
        { label: "This Weekend", from: weekendStart, to: weekendEnd },
        { label: "This Week", from: today, to: dateAtOffset(today, 6) },
    ];
}

export default function DateShortcutChips() {
    const { getTypedParam, setMultipleTypedParams } = useUrlParams();

    const shortcuts = useMemo(() => {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return buildShortcuts(today);
    }, []);

    const activeFromKey = useMemo(() => {
        const raw = getTypedParam(QueryProperty.FromDate);
        return raw instanceof Date ? toDateKey(raw) : null;
    }, [getTypedParam]);
    const activeToKey = useMemo(() => {
        const raw = getTypedParam(QueryProperty.ToDate);
        return raw instanceof Date ? toDateKey(raw) : null;
    }, [getTypedParam]);

    const matchesActiveRange = (from: Date, to: Date) =>
        toDateKey(from) === activeFromKey && toDateKey(to) === activeToKey;

    const apply = (from: Date, to: Date, isActive: boolean) => {
        if (isActive) {
            // Tapping the active chip clears the range.
            setMultipleTypedParams({
                fromDate: undefined,
                toDate: undefined,
            });
            return;
        }
        setMultipleTypedParams({ fromDate: from, toDate: to });
    };

    return (
        <div
            className="flex flex-wrap items-center gap-2"
            role="group"
            aria-label="Date quick filters"
        >
            {shortcuts.map((s) => {
                const isActive = matchesActiveRange(s.from, s.to);
                return (
                    <button
                        key={s.label}
                        type="button"
                        onClick={() => apply(s.from, s.to, isActive)}
                        aria-pressed={isActive}
                        className={`rounded-full px-3 py-1.5 font-dmSans text-xs font-semibold transition ${
                            isActive
                                ? "bg-copper text-white"
                                : "bg-white/5 text-copper border border-copper/20 hover:bg-copper/10"
                        }`}
                    >
                        {s.label}
                    </button>
                );
            })}
        </div>
    );
}
