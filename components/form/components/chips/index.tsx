"use client";

import { FormField, FormItem, FormControl } from "../../../ui/form";
import { Chip } from "@nextui-org/react";
import { ControllerRenderProps, FieldValues } from "react-hook-form";

type TypedFieldValues = ControllerRenderProps<FieldValues, string>;

export interface ChipInterface {
    id: number;
    name: string;
}
interface FormInputProps {
    name: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function ChipFormComponent({ form, name }: FormInputProps) {
    const handleRemoveChip = (item: ChipInterface, field: TypedFieldValues) => {
        const values = field.value?.filter(
            (value: ChipInterface) => value.id !== item.id,
        );
        field.onChange(values);
    };

    const generateChipLabel = (
        item: ChipInterface,
        field: TypedFieldValues,
    ) => {
        return field.value.find((data: ChipInterface) => data.id == item.id)
            ?.name;
    };
    return (
        <FormField
            control={form.control}
            name={name}
            render={(field) => {
                return (
                    <FormItem className="grid grid-cols-4 gap-4">
                        {field.field.value.map((item: ChipInterface) => (
                            <FormField
                                key={item.id}
                                control={form.control}
                                name={name}
                                render={({ field }) => {
                                    return (
                                        <FormItem key={item.id}>
                                            <FormControl>
                                                <Chip
                                                    size="md"
                                                    key={item.id}
                                                    onClose={() => {
                                                        handleRemoveChip(
                                                            item,
                                                            field,
                                                        );
                                                    }}
                                                >
                                                    {generateChipLabel(
                                                        item,
                                                        field,
                                                    )}
                                                </Chip>
                                            </FormControl>
                                        </FormItem>
                                    );
                                }}
                            />
                        ))}
                    </FormItem>
                );
            }}
        />
    );
}
