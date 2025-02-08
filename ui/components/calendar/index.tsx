import React from "react";
import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { UseFormReturn } from "react-hook-form";
import { CalendarDisplay } from "./display";
import { DateRange } from "@/util/search/util";

export enum CalendarVariant {
    Form = "form",
    Standalone = "standalone",
}

interface CalendarBaseProps {
    name: string;
    icon: React.ReactNode;
    placeholder: string;
}

type CalendarFormProps = CalendarBaseProps & {
    variant: CalendarVariant.Form;
    form: UseFormReturn<any>;
};

type CalendarStandaloneProps = CalendarBaseProps & {
    variant: CalendarVariant.Standalone;
    value?: DateRange;
    onValueChange: (value: DateRange | undefined) => void;
};

type CalendarComponentProps = CalendarFormProps | CalendarStandaloneProps;

// Main component with form/standalone logic
const CalendarComponent = (props: CalendarComponentProps) => {
    if (props.variant === CalendarVariant.Form) {
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
                                icon={props.icon}
                                placeholder={props.placeholder}
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
            icon={props.icon}
            placeholder={props.placeholder}
        />
    );
};

export default CalendarComponent;
