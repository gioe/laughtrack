"use client";

import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { Calendar } from "../ui/calendar";
import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { Calendar as CalIcon, ChevronsUpDown } from "lucide-react";
import { useStyleContext } from "@/contexts/StyleProvider";
import { UseFormReturn } from "react-hook-form";
import { cn } from "@/util/tailwindUtil";
import { formatDateRange } from "@/util/primatives/dateUtil";

export interface DateRange {
    from: Date;
    to?: Date;
}

interface CalendarFormComponentProps {
    name: string;
    form: UseFormReturn<any>;
}

const CalendarFormComponent = ({ name, form }: CalendarFormComponentProps) => {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const baseClasses = "text-xl rounded-lg";
    const formControlClasses = `${baseClasses} px-3 lg:w-80 lg:h-12 ${styleConfig.iconTextColor} ring-transparent focus:ring-transparent border-transparent focus:outline-none outline-none`;

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => (
                <FormItem className="flex flex-col">
                    <div className="flex items-center gap-2">
                        <CalIcon
                            className={cn("w-7 h-7", styleConfig.iconTextColor)}
                        />
                        <Popover>
                            <PopoverTrigger asChild>
                                <FormControl className={formControlClasses}>
                                    <div className="flex items-center justify-between w-full">
                                        <span
                                            className={cn(
                                                "text-xl",
                                                styleConfig.iconTextColor,
                                            )}
                                        >
                                            {formatDateRange(field.value)}
                                        </span>
                                        <ChevronsUpDown
                                            className={cn(
                                                "w-3 h-3",
                                                styleConfig.iconTextColor,
                                            )}
                                            style={{ opacity: 0.5 }}
                                        />
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
                                    defaultMonth={field.value?.from}
                                    onSelect={field.onChange}
                                    numberOfMonths={2}
                                    disabled={(date) => date < today}
                                />
                            </PopoverContent>
                        </Popover>
                    </div>
                    <FormMessage />
                </FormItem>
            )}
        />
    );
};

export default CalendarFormComponent;
