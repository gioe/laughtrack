"use client";

import { Selectable } from "../../objects/interface";
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
    items: Selectable[];
}

export function SelectComponent({
    placeholder,
    items,
    handleValueChange,
}: DropdownProps) {
    return (
        <Select
            onValueChange={handleValueChange}
            defaultValue={items[0].id.toString()}
        >
            <SelectTrigger className="bg-white">
                <SelectValue
                    className="text-blue-500 bg-white"
                    placeholder={placeholder}
                />
            </SelectTrigger>
            <SelectContent className="rounded-lg">
                {items.map((item) => (
                    <SelectItem
                        className="bg-white rounded-lg"
                        key={item.id.toString()}
                        value={item.id.toString()}
                    >
                        {item.displayName}
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}
