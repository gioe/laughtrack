"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ControllerRenderProps, useForm } from "react-hook-form";
import { z } from "zod";

import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "../../ui/form";
import { Checkbox } from "../../../@/components/ui/checkbox";

const FormSchema = z.object({
    items: z.array(z.string()).refine((value) => value.some((item) => item), {
        message: "You have to select at least one item.",
    }),
});

export interface CheckboxComponentItem {
    id: number;
    name: string;
}

interface CheckboxComponentProps {
    inputs: CheckboxComponentItem[];
    handleValueChange: (ids: string[]) => void;
}

export function CheckboxComponent({
    inputs,
    handleValueChange,
}: CheckboxComponentProps) {
    const form = useForm<z.infer<typeof FormSchema>>({
        resolver: zodResolver(FormSchema),
        defaultValues: {
            items: [],
        },
    });

    const handleCheckChange = (
        checked: string | boolean,
        item: CheckboxComponentItem,
        field: ControllerRenderProps<
            {
                items: string[];
            },
            "items"
        >,
    ) => {
        const values = checked
            ? [...field.value, item.id.toString()]
            : field.value?.filter((value) => value !== item.id.toString());
        handleValueChange(values);
        return field.onChange(values);
    };

    const handleCheckbox = (
        item: CheckboxComponentItem,
        field: ControllerRenderProps<
            {
                items: string[];
            },
            "items"
        >,
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
