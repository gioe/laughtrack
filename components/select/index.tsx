"use client";

import { FormSelectable } from "../../objects/interfaces";
import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectValue,
    SelectItem,
} from "../ui/select";

interface DropdownProps {
    placeholder: string;
    handleValueChange: (value: string) => void;
    items: FormSelectable[];
}

export function SelectComponent({
    placeholder,
    items,
    handleValueChange,
}: DropdownProps) {
    return (
        <Select onValueChange={handleValueChange} defaultValue={items[0].value}>
            <SelectTrigger>
                <SelectValue
                    className="text-blue-500"
                    placeholder={placeholder}
                />
            </SelectTrigger>
            <SelectContent className="rounded-lg">
                {items.map((item) => (
                    <SelectItem
                        className="bg-white rounded-lg"
                        key={item.label}
                        value={item.value}
                    >
                        {item.label}
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}
