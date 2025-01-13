"use client";

import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { format, isToday, isTomorrow } from "date-fns";
import { Calendar } from "../ui/calendar";
import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { ChevronUpDownIcon } from "@heroicons/react/24/solid";
import { ControllerRenderProps, FieldValues } from "react-hook-form";
import { Calendar as CalIcon } from "lucide-react";
import { datesAreToday, datesAreTomorrow } from "@/util/dateUtil";

type TypedFieldValues = ControllerRenderProps<FieldValues, string>;

interface CalendarFormComponentProps {
    name: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

const determineDateString = (field: TypedFieldValues) => {
    const fromDate = field.value?.from;
    const toDate = field.value?.to;

    if (fromDate && toDate == undefined) {
        return format(fromDate, "LLL dd, yyyy");
    } else if (datesAreToday(fromDate, toDate)) {
        return "Today";
    } else if (datesAreTomorrow(fromDate, toDate)) {
        return "Tomorrow";
    } else {
        let startDate = fromDate;

        if (isToday(fromDate)) {
            startDate = "Today";
        } else if (isTomorrow(fromDate)) {
            startDate = "Tomorrow";
        } else {
            startDate = format(fromDate, "LLL d, yyyy");
        }
        return startDate + " - " + format(toDate, "LLL d, yyyy");
    }
};

const CalendarFormComponent: React.FC<CalendarFormComponentProps> = ({
    name,
    form,
}: CalendarFormComponentProps) => {
    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => {
                return (
                    <FormItem className="flex flex-col">
                        <Popover>
                            <PopoverTrigger asChild>
                                <FormControl className="rounded-lg lg:w-80 lg:h-12 text-gray-400">
                                    <div
                                        className="flex h-9 w-full items-center justify-between whitespace-nowrap 
                                    bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none 
                                    focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1"
                                    >
                                        <CalIcon className="w-5 h-5 text-gray-400 mr-3" />
                                        <span className="text-xl">
                                            {determineDateString(field)}
                                        </span>
                                        <ChevronUpDownIcon className="h-4 w-4 opacity-50" />
                                    </div>
                                </FormControl>
                            </PopoverTrigger>
                            <PopoverContent
                                className="w-auto p-0 rounded-lg"
                                align="start"
                            >
                                <Calendar
                                    className="rounded-lg"
                                    initialFocus
                                    mode="range"
                                    selected={field.value}
                                    defaultMonth={field.value.from}
                                    onSelect={(e) => {
                                        field.onChange(e);
                                    }}
                                    numberOfMonths={2}
                                    disabled={(date) =>
                                        date <
                                        new Date(
                                            new Date().setHours(0, 0, 0, 0),
                                        )
                                    }
                                ></Calendar>
                            </PopoverContent>
                        </Popover>
                        <FormMessage />
                    </FormItem>
                );
            }}
        />
    );
};

export default CalendarFormComponent;
