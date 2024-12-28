"use client";

import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectValue,
    SelectItem,
} from "../ui/select";
import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { Selectable } from "../../objects/interface";
import { MapIcon } from "@heroicons/react/24/outline";

interface DropdownProps {
    name: string;
    placeholder: string;
    items: Selectable[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function DropdownFormComponent({
    name,
    placeholder,
    items,
    form,
}: DropdownProps) {
    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => {
                return (
                    <FormItem className="flex flex-col">
                        <Select onValueChange={field.onChange}>
                            <FormControl className="rounded-lg lg:w-40 lg:h-12">
                                <SelectTrigger>
                                    <MapIcon className="h-5 w-5" />
                                    <SelectValue
                                        className="text-left"
                                        placeholder={placeholder}
                                    />
                                </SelectTrigger>
                            </FormControl>
                            <SelectContent
                                key={name}
                                className="rounded-lg bg-white"
                            >
                                {items.map((item) => (
                                    <SelectItem
                                        className="rounded-lg"
                                        key={item.id.toString()}
                                        value={item.value}
                                    >
                                        {item.displayName}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <FormMessage />
                    </FormItem>
                );
            }}
        />
    );
}
