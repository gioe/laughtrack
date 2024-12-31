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
}: FormInputProps) {
    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => {
                return (
                    <FormItem>
                        <FormLabel
                            className="text-copper font-fjalla
                         placeholder:text-copper placeholder:font-fjalla"
                        >
                            {label}
                        </FormLabel>
                        <FormControl className="rounded-lg">
                            <Input
                                disabled={isLoading}
                                type={name}
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
