"use client";

import { ControllerRenderProps, FieldValues } from "react-hook-form";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../../ui/form";
import { Checkbox } from "../../../@/components/ui/checkbox";
import { FormSelectable } from "../../../objects/interfaces";

type TypedFieldValues = ControllerRenderProps<FieldValues, "items">;

interface CheckboxFormComponentProps {
    inputs: FormSelectable[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function CheckboxFormComponent({
    inputs,
    form,
}: CheckboxFormComponentProps) {
    const handleCheckChange = (
        checked: string | boolean,
        item: FormSelectable,
        field: TypedFieldValues,
    ) => {
        const values = checked
            ? [...field.value, item.value.toString()]
            : field.value?.filter((value: string) => value !== item.value);
        field.onChange(values);
    };

    const handleCheckbox = (item: FormSelectable, field: TypedFieldValues) => {
        return field.value?.includes(item.value);
    };

    return (
        <Form {...form}>
            <FormField
                control={form.control}
                name="items"
                render={() => (
                    <FormItem>
                        {inputs.map((item) => (
                            <FormField
                                key={item.value}
                                control={form.control}
                                name="items"
                                render={({ field }) => {
                                    return (
                                        <FormItem
                                            key={item.value}
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
                                                {item.label}
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
