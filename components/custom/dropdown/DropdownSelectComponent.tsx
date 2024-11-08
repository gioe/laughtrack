"use client";

import { Popover, PopoverTrigger, PopoverContent } from "../../ui/popover";
import { Button } from "../../ui/button";
import { useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "../../../util/tailwindUtil";
import {
    Command,
    CommandInput,
    CommandList,
    CommandGroup,
    CommandItem,
    CommandEmpty,
} from "../../../@/components/ui/command";

export interface ComboBoxItemInterface {
    value: string;
    label: string;
}

interface DropdownSelectComponentProps {
    placeholder: string;
    items: ComboBoxItemInterface[];
    handleSelection: (selection: string) => void;
}

export function DropdownSelectComponent({
    placeholder,
    items,
    handleSelection,
}: DropdownSelectComponentProps) {
    const [open, setOpen] = useState(false);
    const [value, setValue] = useState(items[0].value);

    const setLabel = (value: string) => {
        return value
            ? items.find((item) => item.value === value)?.label
            : placeholder;
    };

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={open}
                    className="w-[200px] justify-between"
                >
                    {setLabel(value)}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[200px] p-0">
                <Command>
                    <CommandInput placeholder={placeholder} />
                    <CommandList>
                        <CommandEmpty>No item found.</CommandEmpty>
                        <CommandGroup>
                            {items.map((item) => (
                                <CommandItem
                                    key={item.value}
                                    value={item.value}
                                    onSelect={(currentValue) => {
                                        const selection =
                                            currentValue === value
                                                ? ""
                                                : item.value;

                                        handleSelection(selection);
                                        setOpen(false);
                                        setValue(selection);
                                    }}
                                >
                                    <Check
                                        className={cn(
                                            "mr-2 h-4 w-4",
                                            value === item.value
                                                ? "opacity-100"
                                                : "opacity-0",
                                        )}
                                    />
                                    {item.label}
                                </CommandItem>
                            ))}
                        </CommandGroup>
                    </CommandList>
                </Command>
            </PopoverContent>
        </Popover>
    );
}
