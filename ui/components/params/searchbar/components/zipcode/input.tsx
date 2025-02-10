import React, { ChangeEvent } from "react";
import { ComponentVariant } from "@/objects/enum";
import {
    FormControl,
    FormField,
    FormItem,
    FormMessage,
} from "@/ui/components/ui/form";
import { Input } from "@/ui/components/ui/input";

interface ZipCodeInputBaseProps {
    disabled: boolean;
    placeholder: string;
    className: string;
}

interface ZipCodeInputFormProps extends ZipCodeInputBaseProps {
    variant: ComponentVariant.Form;
    name: string;
    form: any;
}

interface ZipCodeInputStandaloneProps extends ZipCodeInputBaseProps {
    variant: ComponentVariant.Standalone;
    onChange: (event: ChangeEvent<HTMLInputElement>) => void;
    value?: string;
}

type ZipCodeInputComponentProps =
    | ZipCodeInputFormProps
    | ZipCodeInputStandaloneProps;

const ZipCodeInput = (props: ZipCodeInputComponentProps) => {
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

export default ZipCodeInput;
