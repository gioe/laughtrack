"use client";

import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { format } from "date-fns";
import { Calendar } from "../ui/calendar";
import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { ChevronUpDownIcon } from "@heroicons/react/24/solid";
import { CalendarDateRangeIcon } from "@heroicons/react/24/outline";
import { ControllerRenderProps, FieldValues } from "react-hook-form";

type TypedFieldValues = ControllerRenderProps<FieldValues, string>;

interface CalendarFormComponentProps {
    name: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

const CalendarFormComponent: React.FC<CalendarFormComponentProps> = ({
    name,
    form,
}: CalendarFormComponentProps) => {
    const determineDateString = (field: TypedFieldValues) => {
        return field.value?.from
            ? field.value?.to
                ? format(field.value?.from, "LLL dd, yyyy") +
                  " - " +
                  format(field.value?.to, "LLL dd, yyyy")
                : format(field.value?.from, "LLL dd, yyyy")
            : "Date(s)";
    };

    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => {
                return (
                    <FormItem className="flex flex-col">
                        <Popover>
                            <PopoverTrigger asChild>
                                <FormControl className="rounded-lg lg:w-80 lg:h-12">
                                    <div
                                        className="flex h-9 w-full items-center justify-between whitespace-nowrap border border-input 
                                    bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none 
                                    focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1"
                                    >
                                        <CalendarDateRangeIcon className="h-5 w-5" />
                                        <span>
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
                                    selected={{
                                        // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
                                        from: field.value.from!,
                                        to: field.value.to,
                                    }}
                                    defaultMonth={field.value.from}
                                    onSelect={field.onChange}
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
