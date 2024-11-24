"use client";

import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectValue,
    SelectItem,
} from "../../../ui/select";
import {
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../../../ui/form";
import { cn } from "../../../../util/tailwindUtil";
import { SelectableItem } from "../../../../objects/interface";

interface DropdownProps {
    name: string;
    title: string;
    placeholder: string;
    items: SelectableItem[];
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
                                            className="bg-white rounded-lg"
                                            key={item.id.toString()}
                                            value={item.name}
                                        >
                                            {item.name}
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
