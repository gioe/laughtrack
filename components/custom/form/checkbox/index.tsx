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

type TypedFieldValues = ControllerRenderProps<FieldValues, "items">;
export interface CheckboxComponentItem {
    id: number;
    name: string;
}

interface CheckboxFormComponentProps {
    inputs: CheckboxComponentItem[];
    handleValueChange: (ids: string[]) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function CheckboxFormComponent({
    inputs,
    handleValueChange,
    form,
}: CheckboxFormComponentProps) {
    const handleCheckChange = (
        checked: string | boolean,
        item: CheckboxComponentItem,
        field: TypedFieldValues,
    ) => {
        const values = checked
            ? [...field.value, item.id.toString()]
            : field.value?.filter((value) => value !== item.id.toString());
        handleValueChange(values);
        field.onChange(values);
    };

    const handleCheckbox = (
        item: CheckboxComponentItem,
        field: TypedFieldValues,
    ) => {
        return field.value?.includes(item.id.toString());
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
                                key={item.id}
                                control={form.control}
                                name="items"
                                render={({ field }) => {
                                    return (
                                        <FormItem
                                            key={item.id}
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
