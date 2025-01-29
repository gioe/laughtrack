import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { Calendar } from "../ui/calendar";
import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { UseFormReturn } from "react-hook-form";
import { formatDateRange } from "@/util/primatives/dateUtil";
import React from "react";

export interface DateRange {
    from: Date;
    to?: Date;
}

// Base props that both variants share
interface BaseCalendarProps {
    name: string;
    className: string;
    icon: React.ReactNode;
    chevrons: React.ReactNode;
    textSize: string;
    placeholder: string;
}

// Props for the form variant
interface FormCalendarProps extends BaseCalendarProps {
    form: UseFormReturn<any>;
    onValueChange?: never; // Ensure onValueChange is not provided with form
    value?: never;
}

// Props for the standalone variant
interface StandaloneCalendarProps extends BaseCalendarProps {
    form?: never; // Ensure form is not provided with onValueChange
    onValueChange: (value: DateRange | undefined) => void;
    value?: DateRange;
}

// Combined type using discriminated union
type CalendarComponentProps = FormCalendarProps | StandaloneCalendarProps;

const CalendarComponent = (props: CalendarComponentProps) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Common calendar content
    const CalendarContent = ({
        selected,
        onSelect,
    }: {
        selected?: DateRange;
        onSelect: (value: DateRange | undefined) => void;
    }) => (
        <div className="flex items-center gap-2">
            {props.icon}
            <Popover>
                <PopoverTrigger asChild>
                    <div className={props.className}>
                        <div className="flex items-center justify-between w-full">
                            <span className={props.textSize}>
                                {formatDateRange(props.placeholder, selected)}
                            </span>
                            {props.chevrons}
                        </div>
                    </div>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0 rounded-lg" align="start">
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

    // Render for form-controlled calendar
    if (props.form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field }) => (
                    <FormItem className="flex flex-col">
                        <FormControl className={props.className}>
                            <CalendarContent
                                selected={field.value}
                                onSelect={field.onChange}
                            />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />
        );
    }

    // Render for standalone calendar
    return (
        <CalendarContent
            selected={props.value}
            onSelect={props.onValueChange}
        />
    );
};

export default CalendarComponent;
