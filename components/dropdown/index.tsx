"use client";

import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectValue,
    SelectItem,
} from "../ui/select";
import {
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../ui/form";
import { cn } from "../../util/tailwindUtil";
import { Selectable } from "../../objects/interface";

interface DropdownProps {
    name: string;
    title: string;
    placeholder: string;
    items: Selectable[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function DropdownFormComponent({
    name,
    title,
    placeholder,
    items,
    form,
}: DropdownProps) {
    return (
        <div className="bg-green-700 w-full flex-1 items-center lg:max-w-sm gap-1.5">
            <FormField
                control={form.control}
                name={name}
                render={({ field }) => {
                    return (
                        <FormItem className="flex flex-col">
                            <FormLabel className="text-white h-9 font-medium">
                                {title}
                            </FormLabel>
                            <Select onValueChange={field.onChange}>
                                <FormControl className="rounded-lg">
                                    <SelectTrigger>
                                        <SelectValue
                                            className={cn(
                                                "w-full lg:w-[300px] justify-start text-left font-normal",
                                                field.value == "" &&
                                                    "placeholder:text-muted-foreground",
                                            )}
                                            placeholder={placeholder}
                                        />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent
                                    key={title}
                                    className="rounded-lg"
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
        </div>
    );
}
