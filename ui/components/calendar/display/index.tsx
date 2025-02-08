import { formatDateRange } from "@/util/primatives/dateUtil";
import React from "react";
import { Popover, PopoverTrigger, PopoverContent } from "../../ui/popover";
import { Calendar } from "../../ui/calendar";
import { DateRange } from "@/util/search/util";
import { ChevronsUpDown } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";

interface CalendarDisplayProps {
    selectedRange?: DateRange;
    onSelect: (value: DateRange | undefined) => void;
    icon: React.ReactNode;
    placeholder: string;
}

// Component that handles the calendar display logic
export const CalendarDisplay: React.FC<CalendarDisplayProps> = ({
    selectedRange,
    onSelect,
    icon,
    placeholder,
}) => {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return (
        <div className="flex items-center gap-2 w-full">
            {icon}
            <Popover>
                <PopoverTrigger asChild>
                    <div
                        className={`rounded-lg ring-transparent 
                            focus:ring-transparent border-transparent focus:outline-none outline-none w-full cursor-pointer`}
                    >
                        <div className="flex items-center justify-between w-full px-3 py-2">
                            <span
                                className={`${styleConfig.searchBarFontSize} ${styleConfig.searchBarTextColor}`}
                            >
                                {formatDateRange(placeholder, selectedRange)}
                            </span>
                            <div className="ml-2">
                                <ChevronsUpDown
                                    className={`w-3 h-3 ml-2 ${styleConfig.iconTextColor}`}
                                />
                            </div>
                        </div>
                    </div>
                </PopoverTrigger>
                <PopoverContent
                    className="w-auto p-0 rounded-lg"
                    align="start"
                    sideOffset={8}
                >
                    <Calendar
                        className="rounded-lg"
                        initialFocus
                        mode="range"
                        selected={selectedRange}
                        defaultMonth={selectedRange?.from}
                        onSelect={onSelect}
                        numberOfMonths={2}
                        disabled={(date) => date < today}
                    />
                </PopoverContent>
            </Popover>
        </div>
    );
};
