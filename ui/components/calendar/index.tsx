import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { UseFormReturn } from "react-hook-form";
import React from "react";
import { CalendarDisplay } from "./display";

export enum CalendarVariant {
    Form = "form",
    Standalone = "standalone",
}

export interface DateRange {
    from: Date;
    to?: Date;
}

interface CalendarBaseProps {
    name: string;
    className: string;
    icon: React.ReactNode;
    chevrons: React.ReactNode;
    textSize: string;
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
                                selected={field.value}
                                onSelect={field.onChange}
                                className={props.className}
                                icon={props.icon}
                                chevrons={props.chevrons}
                                textSize={props.textSize}
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
            selected={props.value}
            onSelect={props.onValueChange}
            className={props.className}
            icon={props.icon}
            chevrons={props.chevrons}
            textSize={props.textSize}
            placeholder={props.placeholder}
        />
    );
};

export default CalendarComponent;
