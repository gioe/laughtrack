// CalendarDisplay.tsx
import React from "react";
import { formatDateRange } from "@/util/primatives/dateUtil";
import { ChevronsUpDown } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { Calendar as CalendarIcon } from "lucide-react";
import { Calendar } from "@/ui/components/ui/calendar";
import {
    Popover,
    PopoverTrigger,
    PopoverContent,
} from "@/ui/components/ui/popover";
import { DateRange } from "@/objects/interface";

const PLACEHOLDER = "When";

interface CalendarDisplayProps {
    selectedRange: DateRange;
    onSelect: (value: DateRange | undefined) => void;
    ariaLabelledBy?: string;
}

// Component that handles the calendar display logic
export const CalendarDisplay: React.FC<CalendarDisplayProps> = ({
    selectedRange,
    onSelect,
    ariaLabelledBy,
}) => {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return (
        <div className="flex items-center gap-3">
            <div className="flex items-center">
                <CalendarIcon
                    className={`w-5 h-5 mr-2 flex-shrink-0 ${styleConfig.iconTextColor}`}
                />
                <Popover>
                    <PopoverTrigger asChild>
                        <button
                            type="button"
                            aria-labelledby={ariaLabelledBy}
                            className="flex items-center focus:outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 rounded"
                        >
                            <div
                                className={`text-sm sm:text-base ${styleConfig.inputTextColor} font-dmSans`}
                            >
                                {formatDateRange(PLACEHOLDER, selectedRange)}
                            </div>
                            <ChevronsUpDown
                                className={`w-4 h-4 ml-2 opacity-50 ${styleConfig.iconTextColor}`}
                            />
                        </button>
                    </PopoverTrigger>
                    <PopoverContent
                        className="p-0 rounded-lg border shadow-lg"
                        align="center"
                        sideOffset={16}
                        avoidCollisions={true}
                    >
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
                    </PopoverContent>
                </Popover>
            </div>
        </div>
    );
};
