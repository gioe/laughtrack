"use client";

import { FormDirection } from "../../../objects/enum";
import { ButtonData } from "../../../objects/interface";
import ButtonComponent from "../../button/form";
import { Form } from "../../ui/form";
import { DefaultFormButton } from "../components/button";

export interface BaseFormProps {
    isLoading: boolean;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onSubmit: (data: any) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
    body: React.ReactNode;
    primaryButton?: React.ReactNode;
    secondaryButtonData?: ButtonData;
    direction?: FormDirection;
}

export default function BaseForm({
    direction = FormDirection.Vertical,
    form,
    body,
    primaryButton,
    secondaryButtonData,
    onSubmit,
}: BaseFormProps) {
    return (
        <div className="flex justify-center">
            <Form {...form}>
                <form
                    onSubmit={form.handleSubmit(onSubmit)}
                    className={`flex ${direction == FormDirection.Vertical ? "flex-col" : "flex-row"}`}
                >
                    {body}
                    {secondaryButtonData && (
                        <ButtonComponent
                            data={secondaryButtonData}
                            disabled={false}
                            onClick={() => {
                                console.log("FOOOOO");
                            }}
                        />
                    )}
                    <div className="flex justify-center">
                        {primaryButton ? (
                            primaryButton
                        ) : (
                            <DefaultFormButton label="OK" />
                        )}
                    </div>
                </form>
            </Form>
        </div>
    );
}
