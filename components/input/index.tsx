"use client";

import { Input } from "../ui/input";
import {
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../ui/form";

interface FormInputProps {
    isLoading: boolean;
    name: string;
    placeholder: string;
    type?: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
    label: string;
}

export function FormInput({
    isLoading,
    form,
    name,
    placeholder,
    label,
    type,
}: FormInputProps) {
    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => {
                return (
                    <FormItem>
                        <FormLabel className="text-shark">{label}</FormLabel>
                        <FormControl className="bg-white rounded-lg">
                            <Input
                                disabled={isLoading}
                                type={type}
                                placeholder={placeholder}
                                {...field}
                            />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                );
            }}
        />
    );
}
