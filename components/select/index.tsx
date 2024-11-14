"use client";

import { FormSelectable } from "../../objects/interface";
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
        <Select
            onValueChange={handleValueChange}
            defaultValue={items[0].id.toString()}
        >
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
                        key={item.id.toString()}
                        value={item.id.toString()}
                    >
                        {item.name}
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}
