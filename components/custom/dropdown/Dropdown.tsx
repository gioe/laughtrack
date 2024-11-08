"use client";

import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectValue,
    SelectItem,
} from "../../../components/ui/select";
import {
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../../../components/ui/form";
import { cn } from "../../../util/tailwindUtil";

interface DropdownProps {
    name: string;
    title: string;
    placeholder: string;
    items: string[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function Dropdown({
    name,
    title,
    placeholder,
    items,
    form,
}: DropdownProps) {
    return (
        <div className="grid w-full lg:max-w-sm flex-1 items-center gap-1.5">
            <FormField
                control={form.control}
                name={name}
                render={({ field }) => {
                    return (
                        <FormItem className="flex flex-col">
                            <FormLabel className="text-white">
                                {title}
                            </FormLabel>
                            <Select
                                onValueChange={field.onChange}
                                defaultValue={field.value}
                            >
                                <FormControl className="bg-white rounded-lg">
                                    <SelectTrigger>
                                        <SelectValue
                                            className={cn(
                                                "w-full lg:w-[300px] justify-start text-left font-normal",
                                                field.value == "" &&
                                                    "text-blue-500",
                                            )}
                                            placeholder={placeholder}
                                        />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent className="rounded-lg">
                                    {items.map((item) => (
                                        <SelectItem
                                            className="bg-white rounded-lg"
                                            key={item}
                                            value={item}
                                        >
                                            {item}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <FormMessage />
                        </FormItem>
                    );
                }}
            />
        </div>
    );
}
