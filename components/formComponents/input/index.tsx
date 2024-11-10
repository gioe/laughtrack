"use client";

import { Input } from "../../ui/input";
import { FormControl, FormField, FormItem, FormMessage } from "../../ui/form";

interface FormInputProps {
    isLoading: boolean;
    name: string;
    placeholder: string;
    type?: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function FormInput({
    isLoading,
    form,
    name,
    type,
    placeholder,
}: FormInputProps) {
    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => {
                return (
                    <FormItem>
                        <FormControl>
                            <Input
                                disabled={isLoading}
                                type={type ?? "text"}
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
