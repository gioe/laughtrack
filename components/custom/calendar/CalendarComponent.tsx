"use client";

import { Popover, PopoverContent, PopoverTrigger } from "../../ui/popover";
import { format } from "date-fns";
import { Calendar } from "../../ui/calendar";
import {
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../../ui/form";
import { Button } from "../../ui/button";
import { cn } from "../../../util/tailwindUtil";

interface CalendarComponentProps {
    name: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

const CalendarComponent: React.FC<CalendarComponentProps> = ({
    name,
    form,
}: CalendarComponentProps) => {
    return (
        <div className="grid w-full lg:max-w-sm flex-1 items-center gap-1.5">
            <FormField
                control={form.control}
                name={name}
                render={({ field }) => {
                    return (
                        <FormItem className="flex flex-col">
                            <FormLabel className="text-white">Dates</FormLabel>
                            <FormMessage />
                            <Popover>
                                <PopoverTrigger asChild>
                                    <FormControl className="rounded-lg">
                                        <Button
                                            id="date"
                                            name="dates"
                                            variant={"outline"}
                                            className={cn(
                                                "w-full lg:w-[300px] justify-start text-left font-normal",
                                                !field.value.from &&
                                                    "placeholder:text-muted-foreground",
                                            )}
                                        >
                                            {field.value?.from ? (
                                                field.value?.to ? (
                                                    <>
                                                        {format(
                                                            field.value?.from,
                                                            "LLL dd, yyyy",
                                                        )}{" "}
                                                        -{" "}
                                                        {format(
                                                            field.value?.to,
                                                            "LLL dd, yyyy",
                                                        )}
                                                    </>
                                                ) : (
                                                    format(
                                                        field.value?.from,
                                                        "LLL dd, yyyy",
                                                    )
                                                )
                                            ) : (
                                                <span>Select your dates</span>
                                            )}
                                        </Button>
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
                        </FormItem>
                    );
                }}
            ></FormField>
        </div>
    );
};

export default CalendarComponent;
