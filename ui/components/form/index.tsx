"use client";

import { Form } from "../ui/form";
import { FullRoundedButton } from "../button/rounded/full";

export interface BaseFormProps {
    isLoading: boolean;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onSubmit: (data: any) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
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
