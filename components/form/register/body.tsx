/* eslint-disable @typescript-eslint/no-explicit-any */
import { FormInput } from "../../input/index";
import Heading from "../../modals/heading";

interface RegisterFormBodyProps {
    isLoading: boolean;
    form: any;
}
export default function RegisterFormBody({
    isLoading,
    form,
}: RegisterFormBodyProps) {
    return (
        <div className="flex flex-col gap-4">
            <Heading title="Register" />
            <FormInput
                isLoading={isLoading}
                name={"email"}
                label={"Email"}
                type={"email"}
                placeholder={"Enter email"}
                form={form}
            />
            <FormInput
                isLoading={isLoading}
                name={"password"}
                label={"Password"}
                type={"password"}
                placeholder={"Enter password"}
                form={form}
            />
        </div>
    );
}
