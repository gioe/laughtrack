"use client";

import { Input } from "../../ui/input";
import {
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../../ui/form";

interface FormTextInputProps {
    isLoading: boolean;
    name: string;
    placeholder: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function FormTextInput({
    isLoading,
    form,
    name,
    placeholder,
}: FormTextInputProps) {
    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => {
                return (
                    <FormItem>
                        <FormLabel className="text-white">
                            {placeholder}
                        </FormLabel>
                        <FormControl className="bg-white rounded-lg">
                            <Input
                                disabled={isLoading}
                                type={"text"}
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
