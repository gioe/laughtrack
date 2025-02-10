import React, { ChangeEvent } from "react";
import { Input } from "../../ui/input";
import { FormControl, FormField, FormItem, FormMessage } from "../../ui/form";
import { ComponentVariant } from "@/objects/enum";

interface EmailInputBaseProps {
    disabled: boolean;
    placeholder: string;
    className: string;
}

interface EmailInputFormProps extends EmailInputBaseProps {
    variant: ComponentVariant.Form;
    name: string;
    form: any;
}

interface EmailInputStandaloneProps extends EmailInputBaseProps {
    variant: ComponentVariant.Standalone;
    onChange: (event: ChangeEvent<HTMLInputElement>) => void;
    value?: string;
}

type EmailInputComponentProps = EmailInputFormProps | EmailInputStandaloneProps;

const EmailInput = (props: EmailInputComponentProps) => {
    if (props.variant == ComponentVariant.Form) {
        return (
            <FormField
                control={props.form.control}
                name={props.name}
                render={({ field }) => {
                    return (
                        <FormItem>
                            <FormControl className="rounded-lg">
                                <Input {...field} {...props} />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    );
                }}
            />
        );
    }

    return (
        <div className="space-y-2">
            <Input type="text" maxLength={5} pattern="[0-9]{5}" {...props} />
        </div>
    );
};

export default EmailInput;
