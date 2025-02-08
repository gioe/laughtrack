import React from "react";
import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { UseFormReturn } from "react-hook-form";
import { CalendarDisplay } from "./display";
import { DateRange } from "@/util/search/util";
import { ComponentVariant } from "@/objects/enum";

type CalendarFormProps = {
    variant: ComponentVariant.Form;
    form: UseFormReturn<any>;
    name: string;
};

type CalendarStandaloneProps = {
    variant: ComponentVariant.Standalone;
    value?: DateRange;
    onValueChange: (value: DateRange | undefined) => void;
};

type CalendarComponentProps = CalendarFormProps | CalendarStandaloneProps;

// Main component with form/standalone logic
const CalendarComponent = (props: CalendarComponentProps) => {
    if (props.variant === ComponentVariant.Form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field }) => (
                    <FormItem className="flex flex-col w-full">
                        <FormControl>
                            <CalendarDisplay
                                selectedRange={field.value}
                                onSelect={field.onChange}
                            />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />
        );
    }

    return (
        <CalendarDisplay
            selectedRange={props.value}
            onSelect={props.onValueChange}
        />
    );
};

export default CalendarComponent;
