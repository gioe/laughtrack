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
import { UseFormReturn } from "react-hook-form";

interface DropdownProps {
    name: string;
    placeholder: string;
    items: Selectable[];
    form: UseFormReturn<any>; // Still using 'any' but now properly typed as form return
}

export function DropdownFormComponent({
    name,
    placeholder,
    items,
    form,
}: DropdownProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const baseClasses = "text-xl rounded-lg";
    const formControlClasses = `${baseClasses}  lg:h-12 ${styleConfig.iconTextColor} ring-transparent focus:ring-transparent 
    shadow-none border-transparent focus:outline-none outline-none`;

    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => (
                <FormItem className="flex flex-col">
                    <div className="flex items-center gap-2">
                        <MapPin
                            className={`w-5 h-5 ${styleConfig.iconTextColor}`}
                        />
                        <Select
                            onValueChange={field.onChange}
                            value={field.value}
                        >
                            <FormControl className={formControlClasses}>
                                <SelectTrigger>
                                    <SelectValue
                                        className="text-left pr-2"
                                        placeholder={placeholder}
                                    />
                                </SelectTrigger>
                            </FormControl>
                            <SelectContent className="rounded-lg bg-white">
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
                    </div>
                    <FormMessage />
                </FormItem>
            )}
        />
    );
}
