"use client";

import { ControllerRenderProps } from "react-hook-form";
import {
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../../../ui/form";
import { Checkbox } from "../../../../@/components/ui/checkbox";
import { FormSelectable } from "../../../../objects/interface";

type TypedFieldValues = ControllerRenderProps<
    {
        ids: number[];
    },
    "ids"
>;

interface CheckboxFormComponentProps {
    items: FormSelectable[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function CheckboxFormComponent({
    items,
    form,
}: CheckboxFormComponentProps) {
    const handleSelection = (
        checked: string | boolean,
        item: FormSelectable,
        field: TypedFieldValues,
    ) => {
        const values = checked
            ? [...field.value, item.id]
            : field.value.filter((value) => value !== item.id);
        field.onChange(values);
    };

    const isChecked = (item: FormSelectable, field: TypedFieldValues) => {
        return field.value.includes(Number(item.id));
    };

    return (
        <FormField
            control={form.control}
            name={"ids"}
            render={() => (
                <FormItem>
                    {items.map((item) => (
                        <FormField
                            defaultValue={[]}
                            key={item.id}
                            control={form.control}
                            name={"ids"}
                            render={({ field }) => {
                                return (
                                    <FormItem
                                        key={item.id}
                                        className="flex flex-row items-start space-x-3 space-y-0  bg-white"
                                    >
                                        <FormControl>
                                            <Checkbox
                                                checked={isChecked(item, field)}
                                                onCheckedChange={(checked) => {
                                                    handleSelection(
                                                        checked,
                                                        item,
                                                        field,
                                                    );
                                                }}
                                            />
                                        </FormControl>
                                        <FormLabel className="font-normal">
                                            {item.name}
                                        </FormLabel>
                                    </FormItem>
                                );
                            }}
                        />
                    ))}
                    <FormMessage />
                </FormItem>
            )}
        />
    );
}
