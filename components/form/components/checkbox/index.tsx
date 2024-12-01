"use client";

import { ControllerRenderProps, FieldValues } from "react-hook-form";
import {
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../../../ui/form";
import { Checkbox } from "../../../../@/components/ui/checkbox";
import { Selectable } from "../../../../objects/interface";

type TypedFieldValues = ControllerRenderProps<FieldValues, string>;

interface CheckboxFormComponentProps {
    selectables: Selectable[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function CheckboxFormComponent({
    selectables,
    form,
}: CheckboxFormComponentProps) {
    const handleSelection = (
        checked: string | boolean,
        item: Selectable,
        field: TypedFieldValues,
    ) => {
        const values = checked
            ? [...field.value, item.id]
            : field.value.filter((value) => value !== item.id);
        field.onChange(values);
    };

    const isChecked = (item: Selectable, field: TypedFieldValues) => {
        return field.value.includes(item.id) || item.selected == true;
    };

    return (
        <FormField
            control={form.control}
            name={"ids"}
            render={(parentField) => {
                return (
                    <FormItem>
                        {selectables.map((item) => (
                            <FormField
                                key={item.id}
                                control={form.control}
                                name={item.value}
                                render={() => {
                                    return (
                                        <FormItem
                                            defaultChecked={item.selected}
                                            key={item.id}
                                            className="flex flex-row items-start space-x-3 space-y-0 bg-shark text-white"
                                        >
                                            <FormControl>
                                                <Checkbox
                                                    className="border-white"
                                                    checked={isChecked(
                                                        item,
                                                        parentField.field,
                                                    )}
                                                    onCheckedChange={(
                                                        checked,
                                                    ) => {
                                                        handleSelection(
                                                            checked,
                                                            item,
                                                            parentField.field,
                                                        );
                                                    }}
                                                />
                                            </FormControl>
                                            <FormLabel className="font-normal ">
                                                {item.displayName}
                                            </FormLabel>
                                        </FormItem>
                                    );
                                }}
                            />
                        ))}
                        <FormMessage />
                    </FormItem>
                );
            }}
        />
    );
}
