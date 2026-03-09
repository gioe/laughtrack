"use client";

import { FieldValues, UseFormReturn, SubmitHandler } from "react-hook-form";
import { Form } from "../ui/form";
import { FullRoundedButton } from "../button/rounded/full";

export interface BaseFormProps {
    isLoading: boolean;
    onSubmit: SubmitHandler<FieldValues>;
    form: UseFormReturn<FieldValues>;
    body: React.ReactNode;
}

export default function BaseForm({ form, body, onSubmit }: BaseFormProps) {
    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)}>
                <div className="flex flex-col justify-center w-full gap-3">
                    {body}
                    <FullRoundedButton label="OK" />
                </div>
            </form>
        </Form>
    );
}
