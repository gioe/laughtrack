import React from "react";
import { FieldPath, FieldValues, FormState, UseFormReturn } from "react-hook-form";
import { CalendarDisplay } from "./display";
import { ComponentVariant } from "@/objects/enum";
import { FormControl, FormField, FormItem } from "@/ui/components/ui/form";
import { DateRange } from "@/objects/interface";

type CalendarFormProps<TFieldValues extends FieldValues> = {
    variant: ComponentVariant.Form;
    form: UseFormReturn<TFieldValues>;
    name: FieldPath<TFieldValues>;
    inputId?: string;
};

type CalendarStandaloneProps = {
    variant: ComponentVariant.Standalone;
    value: DateRange | undefined;
    onValueChange: (value: DateRange | undefined) => void;
    inputId?: string;
};

type CalendarComponentProps<TFieldValues extends FieldValues> =
    | CalendarFormProps<TFieldValues>
    | CalendarStandaloneProps;

// Main component with form/standalone logic
const CalendarComponent = <TFieldValues extends FieldValues>(
    props: CalendarComponentProps<TFieldValues>,
) => {
    const getDateErrors = (formState: FormState<TFieldValues>) => {
        const errors = formState.errors as {
            dates?: {
                from?: { message?: string };
                to?: { message?: string };
            };
        };
        const fromError = errors.dates?.from?.message;
        const toError = errors.dates?.to?.message;

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
                                    ariaLabelledBy={props.inputId}
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
            selectedRange={props.value ?? { from: undefined, to: undefined }}
            onSelect={props.onValueChange}
            ariaLabelledBy={props.inputId}
        />
    );
};

export default CalendarComponent;
