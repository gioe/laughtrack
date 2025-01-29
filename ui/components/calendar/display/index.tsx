import { formatDateRange } from "@/util/primatives/dateUtil";
import React from "react";
import { DateRange } from "..";
import { Popover, PopoverTrigger, PopoverContent } from "../../ui/popover";
import { Calendar } from "../../ui/calendar";

interface CalendarDisplayProps {
    selected?: DateRange;
    onSelect: (value: DateRange | undefined) => void;
    className: string;
    icon: React.ReactNode;
    chevrons: React.ReactNode;
    textSize: string;
    placeholder: string;
}

// Component that handles the calendar display logic
export const CalendarDisplay: React.FC<CalendarDisplayProps> = ({
    selected,
    onSelect,
    className,
    icon,
    chevrons,
    textSize,
    placeholder,
}) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return (
        <div className="flex items-center gap-2 w-full">
            {icon}
            <Popover>
                <PopoverTrigger asChild>
                    <div className={`${className} w-full cursor-pointer`}>
                        <div className="flex items-center justify-between w-full px-3 py-2">
                            <span className={textSize}>
                                {formatDateRange(placeholder, selected)}
                            </span>
                            <div className="ml-2">{chevrons}</div>
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
                        selected={selected}
                        defaultMonth={selected?.from}
                        onSelect={onSelect}
                        numberOfMonths={2}
                        disabled={(date) => date < today}
                    />
                </PopoverContent>
            </Popover>
        </div>
    );
};
