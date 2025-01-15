"use client";

import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectValue,
    SelectItem,
} from "../ui/select";
import { FormControl, FormField, FormItem, FormMessage } from "../ui/form";
import { MapPin } from "lucide-react";
import { Selectable } from "@/objects/interface";
import { useStyleContext } from "@/contexts/StyleProvider";

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
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => {
                return (
                    <FormItem className="flex flex-col">
                        <Select onValueChange={field.onChange}>
                            <FormControl
                                className={`text-xl rounded-lg lg:w-40 lg:h-12 ${styleConfig.iconTextColor} ring-transparent focus:ring-transparent
                             border-transparent focus:outline-none outline-none`}
                            >
                                <MapPin
                                    className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                                />
                                <SelectTrigger>
                                    <SelectValue
                                        className="text-left pr-2"
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
                                        {item.display}
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
