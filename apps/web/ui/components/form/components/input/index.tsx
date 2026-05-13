"use client";

import {
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../../../ui/form";
import PasswordInput from "./password";
import EmailInput from "./email";
import ZipCodeInput from "./zipcode";
import {
    ControllerRenderProps,
    FieldPath,
    FieldValues,
    UseFormReturn,
} from "react-hook-form";

interface FormInputProps<TFieldValues extends FieldValues> {
    isLoading: boolean;
    name: FieldPath<TFieldValues>;
    placeholder: string;
    form: UseFormReturn<TFieldValues>;
    label: string;
    className?: string;
    type: "password" | "email" | "zipCode"; // Add type prop
}

export function FormInput<TFieldValues extends FieldValues>({
    isLoading,
    form,
    name,
    placeholder,
    label,
    type,
}: FormInputProps<TFieldValues>) {
    // Helper function to render the appropriate input component
    const renderInput = (
        field: ControllerRenderProps<TFieldValues, FieldPath<TFieldValues>>,
    ) => {
        const commonProps = {
            ...field,
            id: name,
            placeholder,
            disabled: isLoading,
        };
        switch (type) {
            case "password":
                return <PasswordInput {...commonProps} />;
            case "email":
                return <EmailInput {...commonProps} />;
            case "zipCode":
                return <ZipCodeInput {...commonProps} />;
            default:
                return null;
        }
    };

    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => {
                return (
                    <FormItem>
                        <FormLabel className="text-foreground font-gilroy-bold font-bold">
                            {label}
                        </FormLabel>
                        <FormControl className="rounded-lg">
                            {renderInput(field)}
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                );
            }}
        />
    );
}
