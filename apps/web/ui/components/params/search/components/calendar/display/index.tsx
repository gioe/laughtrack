"use client";

import React, {
    useEffect,
    useRef,
    useState,
    useSyncExternalStore,
} from "react";
import { createPortal } from "react-dom";
import { formatDateRange } from "@/util/primatives/dateUtil";
import { Calendar as CalendarIcon, ChevronsUpDown, X } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { Calendar } from "@/ui/components/ui/calendar";
import {
    Popover,
    PopoverTrigger,
    PopoverContent,
} from "@/ui/components/ui/popover";
import { DateRange } from "@/objects/interface";
import { getChipPresets } from "./presets";

const PLACEHOLDER = "When";
const MOBILE_QUERY = "(max-width: 639px)";

function subscribeToMobileQuery(callback: () => void): () => void {
    const mql = window.matchMedia(MOBILE_QUERY);
    mql.addEventListener("change", callback);
    return () => mql.removeEventListener("change", callback);
}

function getMobileSnapshot(): boolean {
    return window.matchMedia(MOBILE_QUERY).matches;
}

function getMobileServerSnapshot(): boolean {
    return false;
}

function useIsMobileViewport(): boolean {
    return useSyncExternalStore(
        subscribeToMobileQuery,
        getMobileSnapshot,
        getMobileServerSnapshot,
    );
}

interface CalendarDisplayProps {
    selectedRange: DateRange;
    onSelect: (value: DateRange | undefined) => void;
    ariaLabelledBy?: string;
}

export const CalendarDisplay: React.FC<CalendarDisplayProps> = ({
    selectedRange,
    onSelect,
    ariaLabelledBy,
}) => {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const isMobile = useIsMobileViewport();
    const [sheetOpen, setSheetOpen] = useState(false);
    const [popoverOpen, setPopoverOpen] = useState(false);

    const handleChipSelect = (range: DateRange) => {
        onSelect(range);
        setSheetOpen(false);
        setPopoverOpen(false);
    };

    const chipPresets = getChipPresets();
    const chipRow = (
        <div
            className="flex flex-wrap gap-2 px-2 pt-2 pb-3 justify-center"
            role="group"
            aria-label="Quick date presets"
        >
            {chipPresets.map((preset) => (
                <button
                    key={preset.label}
                    type="button"
                    onClick={() => handleChipSelect(preset.range)}
                    className="px-3 py-1.5 text-xs font-dmSans font-medium rounded-full border border-gray-300 text-gray-700 bg-white hover:bg-gray-100 hover:border-gray-400 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                    {preset.label}
                </button>
            ))}
        </div>
    );

    const savedScrollY = useRef(0);
    useEffect(() => {
        if (!isMobile || !sheetOpen) return;
        savedScrollY.current = window.scrollY;
        document.body.style.position = "fixed";
        document.body.style.top = `-${savedScrollY.current}px`;
        document.body.style.width = "100%";
        return () => {
            document.body.style.position = "";
            document.body.style.top = "";
            document.body.style.width = "";
            window.scrollTo(0, savedScrollY.current);
        };
    }, [isMobile, sheetOpen]);

    const triggerClassName =
        "flex items-center focus:outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 rounded";

    const triggerContent = (
        <>
            <div
                className={`text-sm sm:text-base ${styleConfig.inputTextColor} font-dmSans`}
            >
                {formatDateRange(PLACEHOLDER, selectedRange)}
            </div>
            <ChevronsUpDown
                className={`w-4 h-4 ml-2 opacity-50 ${styleConfig.iconTextColor}`}
            />
        </>
    );

    const calendar = (
        <Calendar
            className="rounded-lg"
            initialFocus
            mode="range"
            selected={selectedRange}
            defaultMonth={selectedRange?.from || new Date()}
            onSelect={onSelect}
            numberOfMonths={1}
            disabled={(date) => date < today}
        />
    );

    return (
        <div className="flex items-center gap-3">
            <div className="flex items-center">
                <CalendarIcon
                    className={`w-5 h-5 mr-2 flex-shrink-0 ${styleConfig.iconTextColor}`}
                />
                {isMobile ? (
                    <>
                        <button
                            type="button"
                            aria-labelledby={ariaLabelledBy}
                            aria-haspopup="dialog"
                            aria-expanded={sheetOpen}
                            onClick={() => setSheetOpen(true)}
                            className={triggerClassName}
                        >
                            {triggerContent}
                        </button>
                        {sheetOpen &&
                            typeof document !== "undefined" &&
                            createPortal(
                                <div
                                    className="fixed inset-0 z-[60] bg-black/50"
                                    onClick={() => setSheetOpen(false)}
                                    role="presentation"
                                >
                                    <div
                                        role="dialog"
                                        aria-modal="true"
                                        aria-label="Select dates"
                                        className="fixed inset-x-0 bottom-0 rounded-t-2xl bg-white shadow-2xl pt-2 pb-6 px-4 animate-in slide-in-from-bottom duration-300"
                                        onClick={(e) => e.stopPropagation()}
                                    >
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="text-base font-medium text-gray-900 font-dmSans">
                                                Select dates
                                            </span>
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    setSheetOpen(false)
                                                }
                                                aria-label="Close date picker"
                                                className="p-2 rounded-full hover:bg-gray-100 transition"
                                            >
                                                <X
                                                    size={20}
                                                    className="text-gray-600"
                                                />
                                            </button>
                                        </div>
                                        {chipRow}
                                        <div className="flex justify-center">
                                            {calendar}
                                        </div>
                                    </div>
                                </div>,
                                document.body,
                            )}
                    </>
                ) : (
                    <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
                        <PopoverTrigger asChild>
                            <button
                                type="button"
                                aria-labelledby={ariaLabelledBy}
                                className={triggerClassName}
                            >
                                {triggerContent}
                            </button>
                        </PopoverTrigger>
                        <PopoverContent
                            className="p-0 rounded-lg border shadow-lg"
                            align="center"
                            sideOffset={16}
                            avoidCollisions={true}
                        >
                            {chipRow}
                            {calendar}
                        </PopoverContent>
                    </Popover>
                )}
            </div>
        </div>
    );
};
