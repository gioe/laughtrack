"use client";

import { ButtonData } from "../../../objects/interface";
import ButtonComponent from "../../button";
import { Form } from "../../ui/form";

export interface BaseFormProps {
    isLoading: boolean;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onSubmit: (data: any) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
    body: React.ReactNode;
    primaryButtonData: ButtonData;
    secondaryButtonData?: ButtonData;
}

export default function BaseForm({
    form,
    body,
    primaryButtonData,
    secondaryButtonData,
    onSubmit,
}: BaseFormProps) {
    return (
        <Form {...form}>
            <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="flex flex-row items-center gap-4 w-full"
            >
                <div className="relative p-6 flex-auto">{body}</div>
                {secondaryButtonData && (
                    <ButtonComponent
                        data={secondaryButtonData}
                        disabled={false}
                        onClick={() => {
                            console.log("FOOOOO");
                        }}
                    />
                )}
                <ButtonComponent data={primaryButtonData} disabled={false} />
            </form>
        </Form>
    );
}
