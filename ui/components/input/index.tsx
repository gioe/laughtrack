"use client";

import {
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../ui/form";
import PasswordInput from "./password";
import EmailInput from "./email";
import ZipCodeInput from "./zipcode";

interface FormInputProps {
    isLoading: boolean;
    name: string;
    placeholder: string;
    form: any;
    label: string;
    className?: string;
    type: "password" | "email" | "zipCode"; // Add type prop
}

export function FormInput({
    isLoading,
    form,
    name,
    placeholder,
    label,
    type,
}: FormInputProps) {
    // Helper function to render the appropriate input component
    const renderInput = (field: any) => {
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
                        <FormLabel
                            className="text-black font-dmSans
                         placeholder:text-black placeholder:font-dmSans"
                        >
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
