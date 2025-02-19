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

    return (
        <div className="flex items-center gap-2 w-full">
            <CalendarIcon className={`w-5 h-5 ${styleConfig.iconTextColor}`} />
            <Popover>
                <PopoverTrigger asChild>
                    <div>
                        <div className="flex items-center justify-between w-full h-9 gap-2 pl-2">
                            <div
                                className={`text-[18px] ${styleConfig.searchBarTextColor} font-dmSans`}
                            >
                                {formatDateRange(PLACEHOLDER, selectedRange)}
                            </div>
                            <ChevronsUpDown
                                className={`w-4 h-4 opacity-50 ${styleConfig.iconTextColor}`}
                            />
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
                        onSelect={(
                            range: DateRange | undefined,
                            selectedDay: Date,
                        ) => {
                            console.log("Selected range: ", range);
                            console.log("Selected day: ", selectedDay);

                            onSelect(range);
                        }}
                        numberOfMonths={2}
                        disabled={(date) => date < today}
                    />
                </PopoverContent>
            </Popover>
        </div>
    );
};
