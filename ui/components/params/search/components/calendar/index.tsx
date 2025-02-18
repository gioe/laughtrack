import React from "react";
import { UseFormReturn } from "react-hook-form";
import { CalendarDisplay } from "./display";
import { DateRange } from "@/util/search/util";
import { ComponentVariant } from "@/objects/enum";
import { FormControl, FormField, FormItem } from "@/ui/components/ui/form";

type CalendarFormProps = {
    variant: ComponentVariant.Form;
    form: UseFormReturn<any>;
    name: string;
};

type CalendarStandaloneProps = {
    variant: ComponentVariant.Standalone;
    value: any;
    onValueChange: (value: DateRange | undefined) => void;
};

type CalendarComponentProps = CalendarFormProps | CalendarStandaloneProps;

// Main component with form/standalone logic
const CalendarComponent = (props: CalendarComponentProps) => {
    const getDateErrors = (formState: any) => {
        const fromError = formState.errors.dates?.from?.message;
        const toError = formState.errors.dates?.to?.message;

        if (fromError && toError) {
            return `Date selection is required`;
        }
        return fromError || toError || "";
    };

    if (props.variant === ComponentVariant.Form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field, formState }) => {
                    const errorMessage = getDateErrors(formState);
                    return (
                        <FormItem className="flex flex-col w-full">
                            <FormControl>
                                <CalendarDisplay
                                    selectedRange={field.value}
                                    onSelect={field.onChange}
                                />
                            </FormControl>
                            {errorMessage && (
                                <p className="text-sm font-medium text-destructive">
                                    {errorMessage}
                                </p>
                            )}
                        </FormItem>
                    );
                }}
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
