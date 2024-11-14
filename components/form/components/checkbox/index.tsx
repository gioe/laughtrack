"use client";

import { ControllerRenderProps, FieldValues } from "react-hook-form";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../../../ui/form";
import { Checkbox } from "../../../../@/components/ui/checkbox";
import { FormSelectable } from "../../../../objects/interface";

type TypedFieldValues = ControllerRenderProps<FieldValues, string>;

interface CheckboxFormComponentProps {
    items: FormSelectable[];
    name: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function CheckboxFormComponent({
    items,
    form,
    name,
}: CheckboxFormComponentProps) {
    const handleCheckChange = (
        checked: string | boolean,
        item: FormSelectable,
        field: TypedFieldValues,
    ) => {
        const values = checked
            ? [...field.value, item.name.toString()]
            : field.value?.filter((value: string) => value !== item.name);
        field.onChange(values);
    };

    const handleCheckbox = (item: FormSelectable, field: TypedFieldValues) => {
        return field.value?.includes(item.name);
    };

    return (
        <Form {...form}>
            <FormField
                control={form.control}
                name={name}
                render={() => (
                    <FormItem>
                        {items.map((item) => (
                            <FormField
                                key={item.name}
                                control={form.control}
                                name={name}
                                render={({ field }) => {
                                    return (
                                        <FormItem
                                            key={item.name}
                                            className="flex flex-row items-start space-x-3 space-y-0"
                                        >
                                            <FormControl>
                                                <Checkbox
                                                    checked={handleCheckbox(
                                                        item,
                                                        field,
                                                    )}
                                                    onCheckedChange={(
                                                        checked,
                                                    ) => {
                                                        handleCheckChange(
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
        </Form>
    );
}
