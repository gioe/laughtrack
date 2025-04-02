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
import { useMediaQuery } from "@/hooks/useMediaQuery"; // You'll need to create this hook

const PLACEHOLDER = "When";

interface CalendarDisplayProps {
    selectedRange: DateRange;
    onSelect: (value: DateRange | undefined) => void;
}

// Component that handles the calendar display logic
export const CalendarDisplay: React.FC<CalendarDisplayProps> = ({
    selectedRange,
    onSelect,
}) => {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const isMobile = useMediaQuery("(max-width: 768px)");

    return (
        <div className="flex items-center">
            <CalendarIcon
                className={`w-5 h-5 mr-2 ${styleConfig.iconTextColor}`}
            />
            <Popover>
                <PopoverTrigger asChild>
                    <button
                        type="button"
                        className="flex items-center focus:outline-none"
                    >
                        <div
                            className={`text-base ${styleConfig.inputTextColor} font-dmSans`}
                        >
                            {formatDateRange(PLACEHOLDER, selectedRange)}
                        </div>
                        <ChevronsUpDown
                            className={`w-4 h-4 ml-1 opacity-50 ${styleConfig.iconTextColor}`}
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
                        numberOfMonths={isMobile ? 1 : 2}
                        disabled={(date) => date < today}
                    />
                </PopoverContent>
            </Popover>
        </div>
    );
};
